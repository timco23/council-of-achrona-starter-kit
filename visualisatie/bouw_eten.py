"""Zet de voedselmodellen van KayKit Restaurant Bits (CC0) om naar visualisatie/web/eten.glb voor de 3D-viewer.
Elk stuk eten is een eigen node (eten_ham_cooked, eten_steak, ...), gecentreerd en ~0,24 m groot.

blender -b --factory-startup --python visualisatie/bouw_eten.py --     visualisatie/assets/KayKit-Restaurant-Bits-1.0/addons/kaykit_restaurant_bits/Assets/gltf visualisatie/web/eten.glb
"""
import bpy, sys, os
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
bron, doel = args[0], args[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
for i, naam in enumerate(["food_ingredient_ham_cooked", "food_ingredient_steak", "food_ingredient_cheese",
                          "food_ingredient_tomato", "food_ingredient_carrot", "food_ingredient_bun"]):
    voor = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(bron, naam + ".gltf"))
    nieuw = [o for o in bpy.data.objects if o not in voor]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in nieuw if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    maat = max(hi - lo); midden = (lo + hi) / 2
    leeg = bpy.data.objects.new(naam.replace("food_ingredient_", "eten_"), None)
    bpy.context.scene.collection.objects.link(leeg)
    for o in nieuw:
        if o.parent is None:
            o.parent = leeg
            o.location -= midden
    s = 0.24 / maat
    leeg.scale = (s, s, s)
    leeg.location = (i * 2.0, 0, 0)
    print("ETEN", leeg.name, round(maat, 3))
bpy.ops.export_scene.gltf(filepath=doel, export_format="GLB", export_animations=False)
