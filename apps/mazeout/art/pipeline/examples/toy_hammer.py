"""Toy hammer (level 1 goal item).

Reference: research/items/toy-hammer-a.png, -b.png, -upright-tray.png, goal card.
Cylindrical head: cream middle band, blue end caps (flat faces, soft rounded
rims), a red star printed on both faces, a short red nub opposite the handle,
an orange-red wood-grain handle ending in a chunky blue cap.
Proportions measured on the board capture: head length / diameter = 1.5,
handle-direction extent / head length = 1.2, handle diameter = 0.34 head diameter,
each blue cap ~0.23 of the head length.

The head is ONE rounded cylinder; cream band, blue caps, grain and the two stars
are painted into a cylindrical-UV texture (no seams, no sliver geometry).

Frame: head axis = X, handle = -Y, nub = +Y, star faces = +/-Z (front = +Z).

Colour variant (same meshes, built once): star_mallet (L13 goal) - white head, red star,
royal-blue caps, red handle with a blue end cap (research/items/toy-hammer-mallet-star-a|b.png).
"""
import math
from dataclasses import replace

import numpy as np

from sdf import cylinder, star2, union
from mesher import Item, Material, Part, hex_to_rgb, recolor
from palette import HAMMER_BLUE, HAMMER_CREAM, HAMMER_HANDLE, HAMMER_RED, HAMMER_STAR, streaks

VARIANTS = ["toy_hammer", "star_mallet"]  # ids build() returns (lets build.py/preview.py select one cheaply)

R = 0.20  # head radius
L = 0.60  # head length (cap to cap)
CAP = 0.138  # each blue cap
XB = L / 2 - CAP  # cream/blue boundary
V_SCALE = 1 / (L + 0.1)  # cylindrical UV: v = x * V_SCALE + 0.5
STAR = star2(5, 0.104, 0.05, rotation=90, round=0.0045, round_valley=0.004)


def make_head_texture(band_hex, blue_hex, blue_dark, blue_light, star_hex):
    return lambda u, v: head_texture(u, v, band_hex, blue_hex, blue_dark, blue_light, star_hex)


def head_texture(u, v, band_hex=HAMMER_CREAM.color, blue_hex=HAMMER_BLUE.color, blue_dark="#15609F",
                 blue_light="#3A9BE0", star_hex=HAMMER_STAR.color):
    """u = angle around X (0 = +Y top, 0.25 = +Z front, 0.5 = -Y, 0.75 = -Z back); v -> x."""
    x = (v - 0.5) / V_SCALE
    cream = np.array(hex_to_rgb(band_hex))
    blue = streaks(blue_hex, blue_dark, blue_light, n_lines=40, strength=0.14, seed=3)(u, v)
    col = np.where((np.abs(x) > XB)[..., None], blue, cream[None, None, :])
    # thin darker seam line where the blue meets the cream
    seam = np.clip(1 - np.abs(np.abs(x) - XB) / 0.004, 0, 1)
    col = col * (1 - 0.18 * seam[..., None])
    # stars wrapped on the barrel: star-space = (arc length from the face centre, x)
    star_rgb = np.array(hex_to_rgb(star_hex))
    texel = 2 * math.pi * R / u.shape[1]
    for uc in (0.25, 0.75):
        du = ((u - uc + 0.5) % 1.0) - 0.5
        s = du * 2 * math.pi * R
        # star "up" = +Y: from the front face (u=.25) +Y is toward u=0 (arc -s); from the back (u=.75) toward u=1
        up = -s if uc == 0.25 else s
        d = np.asarray(STAR(np.stack([x.reshape(-1), up.reshape(-1)], 1).astype(np.float32)), float).reshape(u.shape)
        a = np.clip(0.5 - d / texel, 0, 1)
        edge = np.clip(1 - np.abs(d + 0.003) / 0.003, 0, 1) * (d < 0)
        sc = star_rgb[None, None, :] * (1 - 0.10 * edge[..., None])
        col = col * (1 - a[..., None]) + sc * a[..., None]
    return col


def build():
    # head: one cylinder along Y with soft rims, laid along X
    # caps a hair proud of the cream band (as in the capture), blended so it stays one clean mesh
    band = cylinder(R, XB + 0.01, round=0.0)
    caps = cylinder(R + 0.01, L / 2, round=0.048).subtract(cylinder(R + 0.05, XB, round=0.0))
    head = union(band, caps, k=0.014).rotate_z(90)
    head_mat = replace(HAMMER_CREAM, name="hammer_head", texture=head_texture, texture_size=(768, 512))

    nub = cylinder(0.072, 0.05, round=0.022).translate(0, R + 0.018, 0)

    hl = 0.175  # exposed handle length
    handle = cylinder(0.068, (R + hl) / 2 + 0.01, round=0.01).translate(0, -(R + hl) / 2, 0)
    hc = 0.058
    handle_cap = cylinder(0.094, hc, round=0.03).translate(0, -(R + hl + hc - 0.012), 0)

    parts = [
        Part("head", head, head_mat, detail=1.0, uv=("cyl", (0, 0, 0), (1, 0, 0), V_SCALE, 0.5)),
        Part("nub", nub, HAMMER_RED, detail=1.4),
        Part("handle", handle, HAMMER_HANDLE, detail=0.9, uv=("cyl", (0, 0, 0), (0, 1, 0), 1.5)),
        Part("handle_cap", handle_cap, HAMMER_BLUE, detail=1.4, uv=("cyl", (0, 0, 0), (0, 1, 0), 1.5)),
    ]
    # ---- AD pass 2026-09-24: ONE colourway for L1 and L13 (requests-music-sports.md R2). The L1 goal card measures
    #      white-lilac head (242,232,248), blue (4,112,246), red (239,50,55) = the L13 mallet colours; the cream band and
    #      orange handle came from the L1 board crops, which carry the yellow tutorial-hint glow.
    white, blue, red = "#EEE3DF", "#0A6FEA", "#E22120"
    one = {
        "head": replace(head_mat, name="hammer_head", texture=make_head_texture(white, blue, "#0650BE", "#3C95FA", red)),
        "nub": Material("hammer_nub_red", red, roughness=0.5),
        "handle": Material("hammer_handle_red", red, roughness=0.5,
                           texture=streaks(red, "#A8161A", "#F0514A", n_lines=40, strength=0.35, seed=7), texture_size=256),
        "handle_cap": Material("hammer_cap_blue", blue, roughness=0.5,
                               texture=streaks(blue, "#0650BE", "#3C95FA", n_lines=34, strength=0.2, seed=3), texture_size=256),
    }
    parts = [replace(p, material=one[p.name]) for p in parts]
    hammer = Item("toy_hammer", parts, length=1.0,  # 1.15 on the L1 capture / L1 itemScale 1.15 (L13 head ~0.88x the L1 one)
                  budget=2200, voxel=0.004,
                  display_name="Toy Hammer", icon_view=(0.0, 4.0), tray_view=(0.0, 0.0, 0.0),
                  ref_poses=[("research/items/toy-hammer-a.png", ("up", (0, 0, 1)), 90.0),
                             ("research/items/toy-hammer-b.png", ("up", (0, 0, 1)), 45.0)],
                  icon_ref=("research/items/goalcard-hammer-complete-check.png", (380, 30, 555, 215)),
                  tray_ref="research/items/toy-hammer-upright-tray.png")

    # ---- star mallet colourway (measured on toy-hammer-mallet-star-a: white #E9D9D5 lit, blue #0C7EF7 lit /
    #      #0653C6 mid, red #E22120)
    mallet = recolor(hammer, "star_mallet", {
        "head": replace(head_mat, name="mallet_head",
                        texture=make_head_texture(white, blue, "#0650BE", "#3C95FA", red)),
        "nub": Material("mallet_red", red, roughness=0.5),
        "handle": Material("mallet_handle", red, roughness=0.5,
                           texture=streaks(red, "#A8161A", "#F0514A", n_lines=40, strength=0.35, seed=7), texture_size=256),
        "handle_cap": Material("mallet_blue", blue, roughness=0.5,
                               texture=streaks(blue, "#0650BE", "#3C95FA", n_lines=34, strength=0.2, seed=3), texture_size=256),
    }, display_name="Star Mallet",
        ref_poses=[("research/items/toy-hammer-mallet-star-a.png", ("up", (0.0, 0.0, 1.0)), 50.0),
                   ("research/items/toy-hammer-mallet-star-b.png", ("up", (0.0, 0.0, 1.0)), 150.0)])
    return [hammer, mallet]
