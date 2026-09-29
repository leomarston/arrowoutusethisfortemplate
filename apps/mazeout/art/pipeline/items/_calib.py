"""Lighting calibration: one sphere per palette material + an 18% grey sphere (not a game item)."""
from dataclasses import replace

from mesher import Item, Material, Part
from palette import DUCK_YELLOW
from sdf import sphere


def build():
    Y = replace(DUCK_YELLOW, texture=None)
    mats = [replace(Y, name="y_ior15"), replace(Y, name="y_ior11", ior=1.1), replace(Y, name="y_ior125", ior=1.25),
            replace(Y, name="y_specblack", specular_color="#000000"), replace(Y, name="y_rough9", roughness=0.9)]
    parts = [Part(f"s{i}", sphere(0.2).translate(-0.9 + 0.45 * i, 0, 0), m, occluder=False, cut=False) for i, m in enumerate(mats)]
    return Item("_calib", parts, length=2.2, budget=4000, voxel=0.006)
