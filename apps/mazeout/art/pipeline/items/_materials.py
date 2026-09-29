"""Material-family swatches (not a game item): one sphere per palette.FAMILIES preset + textured examples.
    build.py _materials && preview.py --materials   -> art/previews/material_presets.png
"""
from mesher import Item, Part
from palette import (chrome, fabric, frost, glass_ice, glossy_plastic, glaze, knit, leather, marble, matte_food,
                     metal_gold, paper, preset, satin_plastic, satin_rubber, speckle, stripes, tiled_motif, fruit_skin, bread, wood, streaks)
from sdf import sphere, star2

SWATCHES = [
    ("glossy_plastic", glossy_plastic("s_glossy", "#1F66D8")),
    ("satin_plastic", satin_plastic("s_satin", "#E2290C")),
    ("satin_rubber", satin_rubber("s_rubber", "#FFAE00")),
    ("fruit_skin", fruit_skin("s_fruit", "#E3161B")),
    ("matte_food", matte_food("s_matte", "#F3D03A")),
    ("glaze", glaze("s_glaze", "#6B3A1E")),
    ("bread", bread("s_bread", "#D98A3A")),
    ("fabric", fabric("s_fabric", "#E0A800")),
    ("paper", paper("s_paper")),
    ("leather", leather("s_leather", "#8A2A1C")),
    ("wood", wood("s_wood", "#8B5A2B")),
    ("metal_gold", metal_gold("s_gold")),
    ("chrome", chrome("s_chrome")),
    ("glass_ice", glass_ice("s_ice", texture=frost("#A9E3F2"), texture_size=256)),
    ("marble()", glossy_plastic("s_marble", "#1F4FC8", texture=marble("#1F4FC8", "#7FA6F5", seed=2), texture_size=512)),
    ("speckle()", bread("s_speckle", texture=speckle("#D98A3A", "#6B3310", "#F5C27A", density=0.02, size=3), texture_size=256)),
    ("tiled_motif()", satin_plastic("s_motif", "#F2B124", texture=tiled_motif("#F2B124", star2(5, 0.45, 0.2), "#FFE08A", cells=(6, 4)), texture_size=512)),
    ("stripes()", paper("s_stripes", "#E0262C", texture=stripes(["#E0262C", "#FFFFFF"], n=5, slant=0.6), texture_size=256)),
]
COLS = 6
R = 0.3
STEP = 0.8


def build():
    parts = []
    for i, (label, m) in enumerate(SWATCHES):
        x = (i % COLS - (COLS - 1) / 2) * STEP
        z = (i // COLS - 1) * STEP
        uv = ("sphere", (x, 0, z)) if m.texture else None
        parts.append(Part(f"s{i:02d}", sphere(R).translate(x, 0, z), m, occluder=False, voxel=0.008, uv=uv, min_tris=300))
    return Item("_materials", parts, length=(COLS - 1) * STEP + 2 * R, budget=9000, voxel=0.008)
