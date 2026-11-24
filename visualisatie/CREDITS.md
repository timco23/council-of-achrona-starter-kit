# Credits voor de visualisatie

Alle 3D-modellen, texturen en animaties komen van **KayKit, gemaakt door Kay Lousberg** ([kaylousberg.com](https://www.kaylousberg.com)).
Ze staan onder **CC0 1.0** (publiek domein): vrij te gebruiken, ook commercieel. Credit is niet verplicht, maar wel verdiend.

| Pack | Gebruikt voor |
|---|---|
| [KayKit Character Pack: Adventurers 1.0](https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0) | De 7 figuren (Barbarian, Mage, Knight, Rogue, Rogue Hooded), hun attributen en poses |
| [KayKit Dungeon Remastered 1.0](https://github.com/KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0) | De raadszaal en het feest: vloer, muren, pilaren, banieren, fakkels, kaarsen, kaarsenplanken, tafels, stoelen, eten, flessen, vaatjes, tonnen, goud |
| [KayKit Restaurant Bits 1.0](https://github.com/KayKit-Game-Assets/KayKit-Restaurant-Bits-1.0) | Het eten op de borden in de 3D-viewer: ham, steak, kaas, tomaat, wortel, brood |

Zelf gemaakt in `bouw_raadszaal.py`: alleen de kroon van ijskristallen van de Vorstkoning, de gloeiende bol van de Oracle, de lichten, de nevel en het oplichten van de vlammen (de gele vlakken van de KayKit-textuur worden lichtgevend).

| Rol | Figuur | Attribuut | Pose |
|---|---|---|---|
| Vorstkoning | Barbarian (zonder hoed), 1,4× groter | ijskroon | Cheer |
| Archmage | Mage | staf | Spellcasting |
| Engineer | Rogue | kruisboog | 1H_Ranged_Aiming |
| Guardian Keeper | Knight | rond schild en zwaard | Blocking |
| Historian | Mage (zonder hoed) | open boek | Idle |
| Oracle | Rogue Hooded | gloeiende zienersbol | Spellcast_Raise |
| Beast Master | Barbarian | tweehandige bijl | 2H_Melee_Idle |

- `raadszaal.png`: het debat. De zes Raadsleden zitten aan tafel (Sit_Chair_Pose), de Vorstkoning staat aan het hoofd; kaarsen en fakkels branden.
- `feest.png`: na het Verdict. Gedekte tafels, vaatjes, goud en rood-gouden banieren; iedereen juicht (Cheer), de Beast Master heft zijn beker.
- `avatar_<rol>.png`: portretten met transparante achtergrond voor de viewer.

## De 3D-zaal in de viewer

`uv run viewer` toont de zitting in echte 3D met [three.js](https://threejs.org) (MIT, geladen van jsDelivr):

- `web/zaal.glb`: de zaal uit Blender (KayKit Dungeon Remastered), met de groepen `hal`, `debat`, `feest`, `troon` en `attributen`.
- `web/figuren/*.glb`: de KayKit-figuren met hun 76 eigen animaties; three.js speelt ze af (zitten, opstaan, gebaren, eten en drinken van tafel, juichen, schrikken, vonken, ronddraaien).
- `web/scene.json`: stoelen en staplaatsen, vlammen en fakkels, en de camera, omgezet naar three.js-coördinaten.
- `web/eten.glb`: het eten (KayKit Restaurant Bits), gemaakt met `bouw_eten.py`.

Wie spreekt, staat op van zijn stoel, knikt en praat met gebaren. Hij krijgt een gele gloedrand (three.js `OutlinePass`), een zachte gloed en een gele spot, zoals een geselecteerd personage in een game. De camera neemt een close-up vanaf de overkant van de tafel: de spreker staat links in beeld, zijn perkament ernaast. Overgangen zijn kritisch gedempt, zoals `smoothDamp` in [yomotsu/camera-controls](https://github.com/yomotsu/camera-controls). Het overvloeien tussen animaties volgt het three.js-voorbeeld `webgl_animation_skinning_blending`. Zittend zijn wapens verborgen, zodat ze niet door de tafel steken. Tussendoor pakken Raadsleden eten van hun eigen bord, nemen twee happen (het stuk wordt kleiner, met kruimels) en leggen het aangebeten terug; na een paar happen komt er een nieuwe gang. Of ze doen iets grappigs. Na het Verdict wordt het feest: gedekte tafels, iedereen staat en viert, en het Verdict rolt uit als perkament.

## Opnieuw maken

```
python visualisatie/haal_assets.py
blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- zaal
blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- feest
blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- web     # zaal.glb, scene.json en figuren voor de 3D-viewer
blender -b --factory-startup --python visualisatie/bouw_eten.py -- visualisatie/assets/KayKit-Restaurant-Bits-1.0/addons/kaykit_restaurant_bits/Assets/gltf visualisatie/web/eten.glb
blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- avatar koning
```
Rollen voor `avatar`: `koning archmage engineer guardian_keeper historian oracle beast_master`. Voeg `--test` toe voor een snelle, kleine render.
