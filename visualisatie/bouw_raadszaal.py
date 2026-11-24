"""De raadszaal van Achrona in Blender: avatars voor de viewer en een beeld van de zaal voor de pitch.

Alle 3D-modellen zijn CC0 van KayKit (Kay Lousberg, www.kaylousberg.com):
  - KayKit Character Pack: Adventurers 1.0  (figuren, attributen en animaties)
  - KayKit Dungeon Remastered 1.0          (muren, pilaren, banieren, fakkels, tafels, stoelen, kisten)
Haal ze op met `python visualisatie/haal_assets.py`. Alleen de ijskroon en wat lichteffecten maakt dit script zelf.

Gebruik (vanuit de root van de repo):
  blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- zaal            [--test]
  blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- avatar koning   [--test]
Uitvoer in visualisatie/renders/.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

HIER = os.path.dirname(os.path.abspath(__file__))
FIGUREN = os.path.join(HIER, "assets", "KayKit-Character-Pack-Adventures-1.0", "addons",
                       "kaykit_character_pack_adventures", "Characters", "gltf")
KERKER = os.path.join(HIER, "assets", "KayKit-Dungeon-Remastered-1.0", "addons", "kaykit_dungeon_remastered",
                      "Assets", "gltf")
RENDERS = os.path.join(HIER, "renders")
TAFELHOOGTE = 1.0  # bovenkant van KayKit's lange tafel (zie de meting in de commit)

ALLE_ATTRIBUTEN = {"1H_Sword", "1H_Sword_Offhand", "2H_Sword", "Badge_Shield", "Rectangle_Shield", "Round_Shield",
                   "Spike_Shield", "1H_Axe", "1H_Axe_Offhand", "2H_Axe", "Barbarian_Round_Shield", "Mug", "1H_Wand",
                   "2H_Staff", "Spellbook", "Spellbook_open", "1H_Crossbow", "2H_Crossbow", "Knife", "Knife_Offhand",
                   "Throwable", "Icosphere"}

# rol: (naam, model, attributen die zichtbaar blijven, ook verbergen, pose staand, kleur)
ROLLEN = {
    "koning":          ("Vorstkoning",     "Barbarian",    [],                     ["Barbarian_Hat"], ("Cheer", 0.55),        (0.45, 0.80, 1.00)),
    "archmage":        ("Archmage",        "Mage",         ["2H_Staff"],           [],                ("Spellcasting", 0.3),  (0.60, 0.40, 1.00)),
    "engineer":        ("Engineer",        "Rogue",        ["1H_Crossbow"],        [],                ("1H_Ranged_Aiming", 0.5), (1.00, 0.55, 0.20)),
    "guardian_keeper": ("Guardian Keeper", "Knight",       ["Round_Shield", "1H_Sword"], [],          ("Blocking", 0.5),      (0.95, 0.80, 0.30)),
    "historian":       ("Historian",       "Mage",         ["Spellbook_open"],     ["Mage_Hat"],      ("Idle", 0.3),          (0.80, 0.60, 0.35)),
    "oracle":          ("Oracle",          "Rogue_Hooded", [],                     [],                ("Spellcast_Raise", 0.6), (0.85, 0.35, 0.90)),
    "beast_master":    ("Beast Master",    "Barbarian",    ["2H_Axe"],             [],                ("2H_Melee_Idle", 0.3), (0.35, 0.85, 0.40)),
}


# ------------------------------------------------------------------ hulpmiddelen

def importeer(pad):
    voor = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=pad)
    return [o for o in bpy.data.objects if o not in voor]


def kerker(naam, plek=(0, 0, 0), draai=0.0, schaal=1.0):
    pad = next(os.path.join(KERKER, naam + e) for e in (".gltf.glb", ".glb") if os.path.exists(os.path.join(KERKER, naam + e)))
    nieuw = importeer(pad)
    for o in nieuw:
        if o.parent is None:
            o.location = Vector(plek) + o.location
            draai_z(o, draai)
            o.scale = (schaal, schaal, schaal)
    return nieuw


def draai_z(o, graden):
    """De glTF-import zet objecten op quaternion-rotatie; dan negeert Blender rotation_euler."""
    o.rotation_mode = "XYZ"
    o.rotation_euler[2] += math.radians(graden)


def laat_vlam_branden(objecten, sterkte=25.0):
    """KayKit-kaarsen en -fakkels hebben hun vlam in de gedeelde textuur. Maak alleen de fel geel-oranje
    vlakken lichtgevend (masker op de kleur), zodat de vlam echt gloeit en de rest niet."""
    for o in objecten:
        if o.type != "MESH":
            continue
        for slot in o.material_slots:
            m = slot.material
            if m is None or m.get("vlam"):
                continue
            m = m.copy()
            slot.material = m
            m["vlam"] = True
            nt = m.node_tree
            bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
            tex = next(n for n in nt.nodes if n.type == "TEX_IMAGE")
            sep = nt.nodes.new("ShaderNodeSeparateColor")
            nt.links.new(tex.outputs["Color"], sep.inputs["Color"])
            rood = nt.nodes.new("ShaderNodeMath"); rood.operation = "GREATER_THAN"; rood.inputs[1].default_value = 0.85
            blauw = nt.nodes.new("ShaderNodeMath"); blauw.operation = "LESS_THAN"; blauw.inputs[1].default_value = 0.45
            nt.links.new(sep.outputs[0], rood.inputs[0])
            nt.links.new(sep.outputs[2], blauw.inputs[0])
            masker = nt.nodes.new("ShaderNodeMath"); masker.operation = "MULTIPLY"
            nt.links.new(rood.outputs[0], masker.inputs[0])
            nt.links.new(blauw.outputs[0], masker.inputs[1])
            kracht = nt.nodes.new("ShaderNodeMath"); kracht.operation = "MULTIPLY"; kracht.inputs[1].default_value = sterkte
            nt.links.new(masker.outputs[0], kracht.inputs[0])
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            nt.links.new(kracht.outputs[0], bsdf.inputs["Emission Strength"])


def kaars(naam, plek, draai=0.0, licht_hoogte=None, energie=35, schaal=1.0):
    """Een brandende KayKit-kaars of -fakkel: gloeiende vlam plus een warm puntlicht boven de vlam."""
    delen = kerker(naam, plek, draai, schaal)
    laat_vlam_branden(delen)
    if energie <= 0:  # alleen de gloeiende vlam; het licht zet de beller zelf
        return delen
    bpy.context.view_layer.update()
    if licht_hoogte is None:
        pts = [o.matrix_world @ Vector(c) for o in delen if o.type == "MESH" for c in o.bound_box]
        midden = sum(pts, Vector()) / len(pts)
        top = Vector((midden.x, midden.y, max(p.z for p in pts)))
    else:
        top = Vector(plek) + Vector((0, 0, licht_hoogte))
    vlam = licht("POINT", (top.x, top.y, top.z + 0.12), (1.0, 0.58, 0.24), energie, 0.08, naam="vlam")
    vlam.data.use_shadow = False  # tientallen kaarsjes: zonder schaduw past alles in de schaduwbuffer
    return delen


def basisnaam(naam):
    return naam.rsplit(".", 1)[0] if naam.rsplit(".", 1)[-1].isdigit() else naam


def zet_pose(rig, actie_naam, fractie):
    actie = bpy.data.actions.get(actie_naam) or next(a for a in bpy.data.actions if basisnaam(a.name) == actie_naam)
    ad = rig.animation_data or rig.animation_data_create()
    ad.action = actie
    if getattr(actie, "slots", None) and hasattr(ad, "action_slot"):
        ad.action_slot = actie.slots[0]
    start, eind = actie.frame_range
    bpy.context.scene.frame_set(int(start + (eind - start) * fractie))


def figuur(rol, plek=(0, 0, 0), draai=0.0, schaal=1.0, pose=None):
    naam, model, tonen, verbergen, staand, kleur = ROLLEN[rol]
    nieuw = importeer(os.path.join(FIGUREN, model + ".glb"))
    rig = next(o for o in nieuw if o.type == "ARMATURE")
    for o in nieuw:
        b = basisnaam(o.name)
        if o.type == "MESH" and ((b in ALLE_ATTRIBUTEN and b not in tonen) or b in verbergen):
            o.hide_render = o.hide_viewport = True
    rig.location = plek
    draai_z(rig, draai)
    rig.scale = (schaal, schaal, schaal)
    zet_pose(rig, *(pose or staand))
    bpy.context.view_layer.update()
    if rol == "oracle":  # de Oracle ziet het patroon in wat komt: een gloeiende bol in de hand
        hand = rig.matrix_world @ rig.pose.bones["handslot.r"].head
        r = 0.16 * schaal
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=(hand.x, hand.y, hand.z + r * 0.9))
        bol = bpy.context.object
        bpy.ops.object.shade_smooth()
        bol.data.materials.append(materiaal("zienersbol", (0.78, 0.38, 1.0), emissie=6.0, ruwheid=0.1, transmissie=0.3))
        licht("POINT", bol.location, (0.78, 0.4, 1.0), 60 * schaal, r, naam="bolgloed")
    return rig, [o for o in nieuw if o.type == "MESH" and not o.hide_render]


def bovenkant_hoofd(meshes):
    """Hoogste punt en middelpunt van het hoofd in de huidige pose (geëvalueerd, dus na de armature)."""
    dg = bpy.context.evaluated_depsgraph_get()
    hoofd = [o for o in meshes if "_Head" in o.name]
    pts = []
    for o in hoofd:
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        pts += [ev.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
    top = max(p.z for p in pts)
    midden = sum((p for p in pts), Vector()) / len(pts)
    breedte = max(p.x for p in pts) - min(p.x for p in pts)
    return Vector((midden.x, midden.y, top)), breedte


def materiaal(naam, kleur, emissie=0.0, ruwheid=0.3, transmissie=0.0):
    m = bpy.data.materials.new(naam)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*kleur, 1)
    b.inputs["Roughness"].default_value = ruwheid
    if "Transmission Weight" in b.inputs:
        b.inputs["Transmission Weight"].default_value = transmissie
    if emissie:
        b.inputs["Emission Color"].default_value = (*kleur, 1)
        b.inputs["Emission Strength"].default_value = emissie
    return m


def ijskroon(meshes):
    """De enige zelfgemaakte vorm: een kroon van ijskristallen op het hoofd van de Vorstkoning."""
    top, breedte = bovenkant_hoofd(meshes)
    r = breedte * 0.36
    ijs = materiaal("ijs", (0.18, 0.55, 1.0), emissie=1.2, ruwheid=0.08, transmissie=0.2)
    goud = materiaal("kroongoud", (1.0, 0.72, 0.25), ruwheid=0.25)
    goud.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    basis_z = top.z - r * 0.35
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=r * 0.13, location=(top.x, top.y, basis_z))
    ring = bpy.context.object
    ring.data.materials.append(goud)
    delen = [ring]
    for i in range(7):
        a = 2 * math.pi * i / 7
        hoog = r * (1.5 if i == 0 else 1.0 if i % 2 else 1.25)
        bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=r * 0.22, radius2=0, depth=hoog,
                                        location=(top.x + r * math.sin(a), top.y - r * math.cos(a), basis_z + hoog / 2))
        k = bpy.context.object
        k.rotation_euler = (math.radians(-8) * math.cos(a), math.radians(8) * math.sin(a), 0)
        k.data.materials.append(ijs)
        delen.append(k)
    bpy.ops.object.light_add(type="POINT", location=(top.x, top.y - r, basis_z + r))
    gloed = bpy.context.object
    gloed.data.color = (0.55, 0.85, 1.0)
    gloed.data.energy = 60
    gloed.data.shadow_soft_size = 0.3
    return delen


def licht(soort, plek, kleur, energie, grootte=0.5, richt_op=None, naam="licht"):
    data = bpy.data.lights.new(naam, soort)
    data.color = kleur
    data.energy = energie
    if soort == "AREA":
        data.size = grootte
    else:
        data.shadow_soft_size = grootte
    obj = bpy.data.objects.new(naam, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = plek
    if richt_op is not None:
        richting = Vector(richt_op) - Vector(plek)
        obj.rotation_euler = richting.to_track_quat("-Z", "Y").to_euler()
    return obj


def camera(plek, kijk_naar, lens=35):
    data = bpy.data.cameras.new("camera")
    data.lens = lens
    obj = bpy.data.objects.new("camera", data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = plek
    obj.rotation_euler = (Vector(kijk_naar) - Vector(plek)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = obj
    return obj


def render_instellingen(breedte, hoogte, test, transparant=False):
    s = bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    s.render.resolution_x, s.render.resolution_y = breedte, hoogte
    s.render.resolution_percentage = 40 if test else 100
    s.render.film_transparent = transparant
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA" if transparant else "RGB"
    ee = s.eevee
    for attr, waarde in (("taa_render_samples", 16 if test else 96), ("use_raytracing", True),
                         ("use_shadows", True), ("shadow_ray_count", 2), ("use_volumetric_shadows", True),
                         ("shadow_pool_size", "1024")):  # veel kaarsen = veel schaduwen: grotere buffer
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, waarde)
            except (TypeError, ValueError):
                pass
    try:
        s.view_settings.view_transform = "AgX"
        s.view_settings.look = "AgX - Punchy"
    except TypeError:
        pass


def wereld(kleur, sterkte, nevel=0.0):
    w = bpy.data.worlds.new("lucht")
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    bg.inputs["Color"].default_value = (*kleur, 1)
    bg.inputs["Strength"].default_value = sterkte
    if nevel:  # lichte blauwe nevel: het maanlicht door de ramen wordt zichtbaar als lichtbundels
        vs = nt.nodes.new("ShaderNodeVolumeScatter")
        vs.inputs["Color"].default_value = (0.75, 0.85, 1.0, 1)
        vs.inputs["Density"].default_value = nevel
        nt.links.new(vs.outputs["Volume"], nt.nodes["World Output"].inputs["Volume"])
    bpy.context.scene.world = w


# ------------------------------------------------------------------ de zaal

RAAD = ["archmage", "engineer", "guardian_keeper", "historian", "oracle", "beast_master"]


def bouw_hal(feest=False):
    """De lege kasteelzaal: vloer, hoge muren met ramen, pilaren, banieren, brandende fakkels en kaarsen."""
    wereld((0.02, 0.04, 0.10), 0.5, nevel=0.006)
    for ix in range(-2, 3):  # vloer: 5 x 5 vakken van 4 m
        for iy in range(-1, 4):
            kerker("floor_tile_large", (ix * 4, iy * 4, 0))
    for ix in range(-2, 3):  # achtermuur met boogramen, en een tweede verdieping
        kerker("wall_archedwindow_open" if ix % 2 else "wall", (ix * 4, 14, 0))
        kerker("wall_window_open" if ix % 2 == 0 else "wall", (ix * 4, 14, 4))
    for iy in range(-1, 4):
        for z in (0, 4):
            soort = "wall_archedwindow_open" if (z == 4 and iy % 2) else "wall"
            kerker(soort, (-10, iy * 4, z), draai=90)
            kerker(soort, (10, iy * 4, z), draai=90)
    for x in (-7, 7):  # pilaren, met aan de voet een brandende kaars
        for y in (0, 6, 12):
            kerker("pillar_decorated", (x, y, 0))
            kaars("candle_lit", (x - 0.9 * (1 if x > 0 else -1), y - 0.9, 0), energie=40)
    banieren = ("banner_patternA_yellow", "banner_patternA_red") if feest else ("banner_patternA_blue", "banner_patternA_white")
    for x in (-6, -2, 2, 6):
        kerker(banieren[0] if x in (-6, 6) else banieren[1], (x, 13.4, 0.3))
    for x, y in ((-9.4, 2), (-9.4, 8), (9.4, 2), (9.4, 8)):  # wandfakkels met gloeiende vlam
        kaars("torch_mounted", (x, y, 2.0), draai=-90 if x < 0 else 90, energie=0)
        licht("POINT", (x * 0.93, y, 2.85), (1.0, 0.52, 0.2), 450, 0.3, naam="fakkel")
    for x, y in ((-9.5, 5), (9.5, 5), (-9.5, 11), (9.5, 11)):  # kaarsenplanken aan de zijmuren
        kaars("shelf_small_candles", (x, y, 1.6), draai=-90 if x < 0 else 90, energie=30)
    # licht: koel maanlicht door de ramen, warme vulling vanuit de camera
    licht("AREA", (0, 17, 6), (0.45, 0.65, 1.0), 1800 if feest else 2500, 10, richt_op=(0, 6, 0), naam="maan")
    licht("AREA", (0, -6, 6), (1.0, 0.82, 0.65), 650 if feest else 400, 8, richt_op=(0, 5, 1), naam="vul")


def kaarsen_op_tafel(ys, extra=False):
    for y in ys:
        kaars("candle_lit", (-0.12, y, TAFELHOOGTE), energie=38)
        kaars("candle_thin_lit", (0.15, y + 0.12, TAFELHOOGTE), energie=25)
        if extra:
            kaars("candle_thin_lit", (0.05, y - 0.22, TAFELHOOGTE), energie=25)


def koning_aan_het_hoofd():
    kerker("chair", (0, 11.0, 0), draai=0, schaal=1.9)  # troon: een vergrote KayKit-stoel
    rig, meshes = figuur("koning", (0, 9.6, 0), draai=0, schaal=1.4)
    ijskroon(meshes)
    licht("SPOT", (0, 2, 9), (0.75, 0.88, 1.0), 2500, 0.6, richt_op=(0, 9.6, 1.5), naam="koningsspot")
    return rig


def bouw_zaal(test):
    """Het debat: de zes Raadsleden zitten aan tafel, de Vorstkoning leidt het vanaf het hoofd."""
    bouw_hal()
    for y in (2, 6):
        kerker("table_long_tablecloth", (0, y, 0))
    kaarsen_op_tafel((0.8, 4.0, 7.2))
    for x, y in ((-0.55, 1.3), (0.55, 1.3), (-0.55, 4.0), (0.55, 4.0), (-0.55, 6.7), (0.55, 6.7)):
        kerker("plate", (x, y, TAFELHOOGTE))
    for i, rol in enumerate(RAAD):
        kant = -1 if i % 2 == 0 else 1
        y = 1.3 + (i // 2) * 2.7
        kerker("chair", (kant * 1.75, y, 0), draai=-90 * kant)
        figuur(rol, (kant * 1.75, y, 0), draai=-90 * kant, pose=("Sit_Chair_Pose", 0.0))
    koning_aan_het_hoofd()
    kerker("chest_gold", (-2.6, 10.2, 0), draai=20)
    kaars("candle_lit", (2.4, 10.4, 0), energie=40)
    kerker("sword_shield_gold", (2.8, 12.8, 0))
    camera((0, -7.2, 5.0), (0, 6.0, 1.7), lens=26)
    render_instellingen(1920, 1080, test)
    bpy.context.scene.render.filepath = os.path.join(RENDERS, "raadszaal_test.png" if test else "raadszaal.png")


def bouw_feest(test):
    """Na het Verdict: feest. Gedekte tafels vol eten, vaatjes, goud, overal kaarsen; iedereen juicht."""
    bouw_hal(feest=True)
    for y in (2, 6):
        kerker("table_long_tablecloth_decorated_A", (0, y, 0))
    kaarsen_op_tafel((0.3, 4.0, 7.7), extra=True)
    for x, y, n in ((-0.5, 3.0, "plate_food_A"), (0.5, 5.0, "plate_food_B"), (-0.45, 7.0, "plate_food_B"),
                    (0.55, 1.0, "bottle_A_green"), (-0.6, 5.4, "bottle_A_labeled_brown")):
        kerker(n, (x, y, TAFELHOOGTE))
    for x, y, n, d in ((-5.2, 10.5, "keg_decorated", 30), (5.2, 10.5, "keg_decorated", -30),
                       (-5.8, 8.6, "barrel_small_stack", 10), (5.8, 8.4, "barrel_small", 0),
                       (-2.8, 10.4, "chest_gold", 20), (2.7, 10.6, "coin_stack_large", 0),
                       (3.3, 9.9, "coin_stack_medium", 0), (-3.4, 9.7, "coin_stack_small", 0),
                       (2.8, 12.8, "sword_shield_gold", 0)):
        kerker(n, (x, y, 0), draai=d)
    # de Raadsleden staan rond de tafel en juichen, elk net op een ander moment van de animatie
    for i, rol in enumerate(RAAD):
        kant = -1 if i % 2 == 0 else 1
        y = 0.9 + (i // 2) * 3.0
        pose = ("Cheer", 0.25 + 0.17 * i)
        if rol == "beast_master":  # heft zijn beker
            ROLLEN[rol] = (*ROLLEN[rol][:2], ["Mug"], *ROLLEN[rol][3:])
            pose = ("Cheer", 0.45)
        figuur(rol, (kant * 2.0, y, 0), draai=-90 * kant + 15 * kant, pose=pose)
    koning_aan_het_hoofd()
    licht("POINT", (0, 4, 4.2), (1.0, 0.72, 0.4), 900, 2.5, naam="feestgloed")
    camera((0, -7.2, 5.0), (0, 6.0, 1.7), lens=26)
    render_instellingen(1920, 1080, test)
    bpy.context.scene.render.filepath = os.path.join(RENDERS, "feest_test.png" if test else "feest.png")


# ------------------------------------------------------------------ een avatar

def bouw_avatar(rol, test):
    naam, *_, kleur = ROLLEN[rol]
    wereld((0.02, 0.03, 0.06), 0.3)
    kerker("floor_tile_small_decorated", (0, 0, 0)) if os.path.exists(os.path.join(KERKER, "floor_tile_small_decorated.gltf.glb")) else None
    schaal = 1.0
    rig, meshes = figuur(rol, (0, 0, 0), draai=0, schaal=schaal)
    if rol == "koning":
        ijskroon(meshes)
    top, _ = bovenkant_hoofd(meshes)
    midden_z = top.z * 0.72  # portret: van borst tot kruin
    licht("AREA", (-2.2, -3.0, top.z + 1.2), (1.0, 0.95, 0.9), 220, 3, richt_op=(0, 0, midden_z), naam="key")
    licht("AREA", (2.6, -2.2, midden_z), (0.8, 0.85, 1.0), 55, 3, richt_op=(0, 0, midden_z), naam="fill")
    licht("AREA", (0, 2.5, top.z + 0.8), kleur, 700, 2.0, richt_op=(0, 0, midden_z), naam="rand")
    camera((0, -4.4, midden_z + 0.45), (0, 0, midden_z + 0.05), lens=55)
    render_instellingen(1024, 1024, test, transparant=True)
    bpy.context.scene.render.filepath = os.path.join(RENDERS, f"avatar_{rol}{'_test' if test else ''}.png")


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["zaal"]
    test = "--test" in args
    args = [a for a in args if a != "--test"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(RENDERS, exist_ok=True)
    if args[0] == "zaal":
        bouw_zaal(test)
    elif args[0] == "feest":
        bouw_feest(test)
    elif args[0] == "avatar":
        bouw_avatar(args[1], test)
    bpy.ops.render.render(write_still=True)
    print("KLAAR:", bpy.context.scene.render.filepath)


main()
