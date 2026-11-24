# Credits voor de visualisatie

Alle 3D-modellen, texturen en animaties komen van **KayKit, gemaakt door Kay Lousberg** ([kaylousberg.com](https://www.kaylousberg.com)).
Ze staan onder **CC0 1.0** (publiek domein): vrij te gebruiken, ook commercieel. Credit is niet verplicht, maar wel verdiend.

| Pack | Gebruikt voor |
|---|---|
| [KayKit Character Pack: Adventurers 1.0](https://github.com/KayKit-Game-Assets/KayKit-Character-Pack-Adventures-1.0) | De 7 figuren (Barbarian, Mage, Knight, Rogue, Rogue Hooded), hun attributen en poses |
| [KayKit Dungeon Remastered 1.0](https://github.com/KayKit-Game-Assets/KayKit-Dungeon-Remastered-1.0) | De raadszaal en het feest: vloer, muren, pilaren, banieren, fakkels, kaarsen, kaarsenplanken, tafels, stoelen, eten, flessen, vaatjes, tonnen, goud |

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

De debatviewer (`uv run viewer`) toont bovenaan de raadszaal met de avatars: wie aan het woord is, licht op in zijn kleur. Na het Verdict wordt de achtergrond het feest.

## Opnieuw maken

```
python visualisatie/haal_assets.py
blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- zaal
blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- feest
blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- avatar koning
```
Rollen voor `avatar`: `koning archmage engineer guardian_keeper historian oracle beast_master`. Voeg `--test` toe voor een snelle, kleine render.
