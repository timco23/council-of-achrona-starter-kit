"""Haalt de CC0-modellen van KayKit op (alleen de modellen en texturen, ~45 MB) naar visualisatie/assets/.

Start vanuit de root van de repo:  python visualisatie/haal_assets.py
Daarna:  blender -b --factory-startup --python visualisatie/bouw_raadszaal.py -- zaal
"""
import os
import subprocess

HIER = os.path.dirname(os.path.abspath(__file__))
PACKS = {
    "KayKit-Character-Pack-Adventures-1.0": ["/LICENSE.txt",
                                             "/addons/kaykit_character_pack_adventures/Characters/gltf/",
                                             "/addons/kaykit_character_pack_adventures/Assets/gltf/"],
    "KayKit-Dungeon-Remastered-1.0": ["/LICENSE.txt",
                                      "/addons/kaykit_dungeon_remastered/Assets/gltf/",
                                      "/addons/kaykit_dungeon_remastered/Assets/texture/"],
    # Echt eten voor de 3D-viewer (bouw_eten.py): ham, steak, kaas, tomaat, wortel, brood.
    "KayKit-Restaurant-Bits-1.0": ["/LICENSE.txt", "/addons/kaykit_restaurant_bits/Assets/gltf/restaurantbits_texture.png",
                                   *(f"/addons/kaykit_restaurant_bits/Assets/gltf/food_ingredient_{n}.{x}"
                                     for n in ("ham_cooked", "steak", "cheese", "tomato", "carrot", "bun") for x in ("gltf", "bin"))],
}


def main():
    doel = os.path.join(HIER, "assets")
    os.makedirs(doel, exist_ok=True)
    for pack, paden in PACKS.items():
        map_ = os.path.join(doel, pack)
        if not os.path.isdir(map_):
            subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                            f"https://github.com/KayKit-Game-Assets/{pack}.git", map_], check=True)
        subprocess.run(["git", "-C", map_, "sparse-checkout", "set", "--no-cone", *paden], check=True)
        print("ok:", pack)


if __name__ == "__main__":
    main()
