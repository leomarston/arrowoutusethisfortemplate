"""Rubber duck (level 1 goal item).

Reference: art/ref/duck_left|mid|right.png (board, 007 capture), goal-card icon.
Plump golden-yellow body (profile ~0.74 x 0.62 of total length) with a soft
upturned tail bump, a big round head (diameter ~0.47 of length), a large flat
open orange bill (wide upper + smaller lower bill), black oval eyes, and on each
side a large raised teardrop wing "pillow" high on the back, outlined by a thin
groove, with two feather grooves at its rear tip.

Frame: beak -> -X, up +Y, wings on +/-Z. Icon view turns it 3/4 toward the camera.
"""
import numpy as np

from sdf import capsule, ellipsoid, plane, project_to_surface, round_cone, sphere, union
from mesher import Item, Part
from palette import DUCK_BEAK, DUCK_EYE, DUCK_MOUTH, DUCK_YELLOW


def mirror_z(s):
    return s.union(s.transform(np.diag([1.0, 1.0, -1.0])))


def on_surface(base, x, y, side=1.0):
    """Point on `base` straight out from the body axis at (x, y), on the +Z (side=1) or -Z side."""
    return project_to_surface(base, np.array([[x, y, 0.33 * side]])).astype(float)[0]


def build():
    big = ((-2, -2, -2), (2, 2, 2))
    # ---------------- body + head
    body = ellipsoid(0.38, 0.33, 0.37).translate(0.07, 0.0, 0.0)
    tail = ellipsoid(0.13, 0.085, 0.11).rotate_z(40).translate(0.38, 0.14, 0.0)
    body = union(body, tail, k=0.1)
    body = body.intersect(plane((0, -1, 0), 0.28).bounded(*big), k=0.12)  # soft, barely-flat base
    hc = np.array([-0.2, 0.35, 0.0])
    head = sphere(0.26).translate(*hc)
    torso = union(body, head, k=0.08)

    # ---------------- wing pillows: offset body surface cut by a 3D teardrop blob sitting on the side
    rise = 0.034
    a = on_surface(torso, -0.02, 0.1)
    b = on_surface(torso, 0.37, 0.19)
    blob = round_cone(a, b, 0.185, 0.11)
    wing = torso.offset(rise).intersect(blob, k=0.03)
    # feather grooves near the rear tip, following the pillow surface
    f1a = on_surface(torso.offset(rise), 0.21, 0.225); f1b = on_surface(torso.offset(rise), 0.41, 0.235)
    f2a = on_surface(torso.offset(rise), 0.21, 0.15); f2b = on_surface(torso.offset(rise), 0.4, 0.165)
    wing = wing.subtract(union(capsule(f1a, f1b, 0.0075), capsule(f2a, f2b, 0.0075)), k=0.004)
    wings = mirror_z(wing)
    # thin groove in the body right around each pillow
    ring = blob.offset(0.012).subtract(blob.offset(0.0))
    groove = ring.subtract(torso.offset(-0.016))
    torso = torso.subtract(mirror_z(groove), k=0.004)

    # ---------------- bill: wide flat upper + smaller lower, mouth slightly open
    upper = ellipsoid(0.175, 0.055, 0.215).rotate_z(-10).translate(-0.49, 0.305, 0.0)
    lower = ellipsoid(0.145, 0.046, 0.18).rotate_z(13).translate(-0.465, 0.222, 0.0)
    root = ellipsoid(0.1, 0.11, 0.18).translate(-0.39, 0.265, 0.0)
    beak = union(upper, lower, root, k=0.025)
    # dark mouth interior between the open bills
    mouth = ellipsoid(0.11, 0.04, 0.16).translate(-0.455, 0.262, 0.0)

    # ---------------- eyes: black ovals bulging from the head
    eyes = []
    for sz in (1, -1):
        d = np.array([-0.78, 0.42, 0.46 * sz]); d /= np.linalg.norm(d)
        p = hc + d * 0.26
        eyes.append(ellipsoid(0.031, 0.043, 0.022).orient((0, 0, 1), d).translate(*(p - d * 0.008)))
    eyes = union(*eyes)

    parts = [
        Part("body", torso, DUCK_YELLOW, detail=1.0, voxel=0.0042),
        Part("wings", wings, DUCK_YELLOW, detail=1.5, voxel=0.0032, min_tris=80),
        Part("beak", beak, DUCK_BEAK, detail=1.6, voxel=0.0035),
        Part("mouth", mouth, DUCK_MOUTH, detail=0.6, voxel=0.0035, collide=False),
        Part("eyes", eyes, DUCK_EYE, detail=1.0, voxel=0.0025, min_tris=40, collide=False),
    ]
    return Item("rubber_duck", parts, length=0.94,  # 1.08 on the L1 capture / L1 itemScale 1.15
                budget=3200, voxel=0.0042,
                display_name="Rubber Duck", icon_view=(78.0, 9.0),
                # ducks lie on a side, rolled ~30 deg toward the back (wing + bill width visible)
                ref_poses=[("art/ref/duck_left.png", ("up", (0, -0.1, 0.995)), 0.0),
                           ("art/ref/duck_mid.png", ("up", (0, 0.5, -0.866)), 66.0),
                           ("art/ref/duck_right.png", ("up", (0, 0.2, -0.98)), -90.0)],
                icon_ref=("research/items/goalcard-duck-strawberry.png", (45, 40, 175, 180)))
