"""Characters: the default avatar (A-20, our own pinata-llama portrait) and the factory mascot (A-35: a red blob in
blue overalls, a yellow hard hat and big eyes), in poses for the splash, loading and Teams art.

Both are OUR designs in the same toy style. References (looked at only): design/ui-crops/icon-avatar.png,
research/shots/036 (Teams), 014 (level splash), meta-006 (loading).
"""
import math

import numpy as np

from uikit import (F, SDF, PAL, Part, box, capsule, cylinder, ellipsoid, gloss, glass, metal, round_cone, satin, sphere,
                   textured, torus, union, extrude, rect2)

VOXEL = 0.005
RED = "#E3262B"
DENIM = "#2F6FD6"
GLOVE = "#FFC61C"


# ------------------------------------------------------------------ A-20 the pinata llama avatar

def _fringe(sdf, pitch=0.085, depth=0.03):
    """Pinata paper fringe: horizontal layers, each flaring out a little at its lower edge (a sawtooth in y)."""
    f = sdf.fn

    def fn(p):
        t = (p[:, 1] / pitch) % 1.0
        return f(p) - F(depth) * (t.astype(F) - F(0.5))
    return SDF(fn, sdf.lo - depth, sdf.hi + depth)


def _band_tex(stops):
    """Colour bands by height: stops = [(v, hex)], blended smoothly (v from the planar UV)."""
    cs = [(v, np.array(PAL._rgb(h))) for v, h in stops]

    def fn(u, v):
        out = np.zeros(v.shape + (3,))
        for i in range(len(cs) - 1):
            v0, c0 = cs[i]; v1, c1 = cs[i + 1]
            m = (v >= v0) & (v <= v1)
            t = ((v - v0) / max(v1 - v0, 1e-6))[..., None]
            out = np.where(m[..., None], c0 * (1 - t) + c1 * t, out)
        out = np.where((v < cs[0][0])[..., None], cs[0][1], out)
        out = np.where((v > cs[-1][0])[..., None], cs[-1][1], out)
        # paper grain: fine horizontal fringe lines
        lines = 0.95 + 0.05 * np.cos(v * 2 * math.pi * 36)
        return out * lines[..., None]
    return fn


def llama():
    cranium = box(0.33, 0.29, 0.27, round=0.21).translate(-0.05, 0.3, 0)
    snout = box(0.22, 0.19, 0.21, round=0.14).rotate_z(-18).translate(0.3, 0.14, 0)
    neck = capsule((-0.12, 0.15, 0), (-0.22, -0.3, 0), 0.29)
    head = union(cranium, snout, neck, k=0.1)
    head = _fringe(head).intersect(box(2, 1, 2).translate(0, -0.27 + 1, 0))  # the portrait crops the neck
    tex = _band_tex([(0.0, "#8B3FD8"), (0.22, "#B63FD6"), (0.45, "#EC4AA6"), (0.66, "#FF7462"), (0.82, "#FFA83E"), (0.97, "#FFD64A")])
    nose = box(0.08, 0.14, 0.19, round=0.07).rotate_z(-18).translate(0.5, 0.08, 0)
    nostrils = union(*[sphere(0.03).translate(0.585, 0.08 + dy, 0.08) for dy in (0.045, -0.045)])
    eye_w = ellipsoid(0.115, 0.125, 0.06).translate(0.04, 0.33, 0.25)
    iris = sphere(0.07).scale_xyz(1, 1, 0.5).translate(0.05, 0.32, 0.297)
    pupil = sphere(0.036).scale_xyz(1, 1, 0.5).translate(0.055, 0.315, 0.318)
    glint = sphere(0.018).translate(0.03, 0.345, 0.325)
    lashes = union(*[capsule((0.02 + 0.09 * math.cos(a), 0.32 + 0.1 * math.sin(a), 0.25), (0.02 + 0.12 * math.cos(a), 0.32 + 0.13 * math.sin(a), 0.25), 0.008)
                     for a in (math.radians(d) for d in (200, 225, 250))])
    tufts = [(box(0.05, 0.09, 0.05, round=0.03).rotate_z(-10).translate(-0.12 + 0.1 * k, 0.62 + 0.02 * (k % 2), -0.02 + 0.03 * k), c)
             for k, c in enumerate(("#FFC93C", "#FF6FB0", "#FFD64A", "#5ED3E6"))]
    mane = [(box(0.045, 0.045, 0.045, round=0.02).translate(-0.3 + 0.04 * k, 0.5 - 0.1 * k, 0.1 + 0.02 * k), c)
            for k, c in enumerate(("#5ED3E6", "#FF6FB0", "#5ED3E6"))]
    parts = [Part("head", head, textured(satin("ll_paper", "#FF7A57", rough=0.55), tex, 512), uv=("planar", (0, -0.62, 0), (1, 0, 0), (0, 1, 0), 0.74)),
             Part("nose", nose, satin("ll_nose", "#F46FA0", rough=0.5), voxel=0.0035),
             Part("nostrils", nostrils, satin("ll_nostril", "#B8326A"), voxel=0.003),
             Part("eye", eye_w, gloss("ll_eye", "#FFFFFF", rough=0.3), voxel=0.003),
             Part("iris", iris, gloss("ll_iris", "#6B46C8", rough=0.25), voxel=0.0025),
             Part("pupil", pupil, gloss("ll_pupil", "#1D1030", rough=0.2), voxel=0.0025),
             Part("glint", glint, gloss("ll_glint", "#FFFFFF", rough=0.2), voxel=0.002),
             Part("lashes", lashes, satin("ll_lash", "#2A1040"), voxel=0.0025)]
    for i, (t, c) in enumerate(tufts + mane):
        parts.append(Part(f"tuft{i}", t, satin(f"ll_tuft{i}", c, rough=0.5), voxel=0.003))
    return parts, VOXEL


# ------------------------------------------------------------------ A-35 the mascot

POSES = {
    # hands (x, y, z) relative to the body, feet spread, hat tilt
    "stand": dict(hands=((-0.44, 0.42, 0.12), (0.44, 0.42, 0.12)), feet=0.13, hat=6),
    "wave": dict(hands=((-0.44, 0.42, 0.12), (0.46, 1.32, 0.05)), feet=0.14, hat=-8),
    "cheer": dict(hands=((-0.5, 1.2, 0.1), (0.5, 1.2, 0.1)), feet=0.16, hat=4),
    "fall": dict(hands=((-0.62, 1.0, 0.1), (0.6, 0.95, -0.05)), feet=0.26, hat=14),
    "hold": dict(hands=((-0.22, 0.62, 0.42), (0.22, 0.62, 0.42)), feet=0.13, hat=-4),
    "megaphone": dict(hands=((-0.52, 1.02, 0.22), (0.44, 0.42, 0.12)), feet=0.13, hat=8),
}


def mascot(pose="stand", eyes="open"):
    P = POSES[pose]
    body = union(capsule((0, 0.42, 0), (0, 1.02, 0), 0.31), ellipsoid(0.35, 0.3, 0.32).translate(0, 0.42, 0), k=0.12)
    # eyes: big whites with dark pupils, looking at the viewer
    eyes_w, pupils, glints = [], [], []
    for sx in (-1, 1):
        c = np.array([sx * 0.11, 0.99, 0.23])
        eyes_w.append(ellipsoid(0.105, 0.135, 0.075).translate(*c))
        pupils.append(sphere(0.048).scale_xyz(1, 1.15, 0.6).translate(c[0] - sx * 0.015, c[1] - 0.01, c[2] + 0.065))
        glints.append(sphere(0.016).translate(c[0] - sx * 0.005, c[1] + 0.025, c[2] + 0.09))
    nose = sphere(0.075).scale_xyz(1.1, 0.9, 1).translate(0, 0.86, 0.3)
    mouth = ellipsoid(0.06, 0.025, 0.03).translate(0, 0.79, 0.3)
    # overalls: the lower body in denim + bib + straps, yellow buttons, a pocket
    over = body.offset(0.018).intersect(box(1, 0.33, 1).translate(0, 0.28, 0), k=0.01)
    bib = body.offset(0.018).intersect(box(0.2, 0.12, 1).translate(0, 0.62, 0.5), k=0.01)
    straps = [body.offset(0.018).intersect(box(0.04, 0.13, 1).rotate_z(sx * 10).translate(sx * 0.25, 0.8, 0), k=0.008) for sx in (-1, 1)]
    buttons = union(*[sphere(0.034).scale_xyz(1, 1, 0.6).translate(sx * 0.19, 0.71, 0.29) for sx in (-1, 1)])
    pocket = box(0.09, 0.06, 0.02, round=0.018).translate(0, 0.58, 0.345)
    denim = PAL.stripes(["#2F6FD6", "#2A64C4"], n=60, axis="u", slant=1.0, soft=0.006)
    # arms and gloves
    arms, gloves = [], []
    for sx, h in zip((-1, 1), P["hands"]):
        sh = np.array([sx * 0.27, 0.8, 0.0])
        hnd = np.array(h)
        el = (sh + hnd) / 2 + np.array([sx * 0.06, -0.05, -0.02])
        arms.append(union(capsule(tuple(sh), tuple(el), 0.085), capsule(tuple(el), tuple(hnd), 0.08), k=0.03))
        d = hnd - el; d /= np.linalg.norm(d)
        gloves.append(union(sphere(0.11).scale_xyz(1, 1.05, 0.9).translate(*(hnd + d * 0.05)),
                            capsule(tuple(hnd + d * 0.03 + np.array([sx * 0.06, 0.06, 0.02])), tuple(hnd + d * 0.03 + np.array([sx * 0.11, 0.12, 0.02])), 0.04),
                            torus(0.075, 0.03).orient((0, 1, 0), tuple(d)).translate(*(hnd - d * 0.04)), k=0.02))
    # legs (boots)
    legs = []
    for sx in (-1, 1):
        fx = sx * P["feet"]
        legs.append(union(capsule((sx * 0.12, 0.2, 0), (fx, 0.06, 0.02), 0.11), ellipsoid(0.13, 0.07, 0.17).translate(fx, 0.02, 0.05), k=0.04))
    # hard hat
    hat_dome = ellipsoid(0.3, 0.24, 0.32).intersect(box(1, 0.3, 1).translate(0, 0.3, 0), k=0.02)
    hat_crest = ellipsoid(0.32, 0.26, 0.34).intersect(box(0.045, 0.3, 1).translate(0, 0.3, 0), k=0.02)
    hat_brim = union(cylinder(0.33, 0.016, round=0.014).translate(0, 0.02, 0), ellipsoid(0.26, 0.022, 0.16).translate(0, 0.022, 0.27), k=0.08)
    bolts = union(*[cylinder(0.025, 0.035, round=0.012).translate(sx * 0.12, 0.21, -0.02) for sx in (-1, 1)])
    hat = union(hat_dome, hat_crest, hat_brim, k=0.02).rotate_z(P["hat"]).translate(0.02, 1.2, -0.02)
    parts = [
        Part("body", union(body, *arms, *legs, nose, k=0.03), gloss("m_red", RED, rough=0.34)),
        Part("mouth", mouth, satin("m_mouth", "#7A1216"), voxel=0.003),
        Part("eyes", union(*eyes_w), gloss("m_eye", "#FFFFFF", rough=0.3), voxel=0.0035),
        Part("pupils", union(*pupils), gloss("m_pupil", "#161218", rough=0.2), voxel=0.003),
        Part("glints", union(*glints), gloss("m_glint", "#FFFFFF", rough=0.2), voxel=0.0025),
        Part("overalls", union(over, bib, *straps, pocket, k=0.01), textured(satin("m_denim", DENIM, rough=0.6), denim, 512),
             uv=("cyl", (0, 0.5, 0), (0, 1, 0), 2.0)),
        Part("buttons", buttons, gloss("m_button", "#FFC61C", rough=0.3), voxel=0.003),
        Part("gloves", union(*gloves), gloss("m_glove", GLOVE, rough=0.3), voxel=0.0035),
        Part("hat", hat, gloss("m_hat", "#FFC21A", rough=0.28), voxel=0.004),
        Part("hat_bolts", bolts.rotate_z(P["hat"]).translate(0.02, 1.2, -0.02), satin("m_hat_bolt", "#2C2A30"), voxel=0.003),
    ]
    return parts, VOXEL


def megaphone():
    horn = union(round_cone((0, 0, 0), (0.32, 0, 0), 0.06, 0.2)).subtract(round_cone((0.02, 0, 0), (0.36, 0, 0), 0.03, 0.18), k=0.01)
    band = torus(0.2, 0.025).rotate_z(90).translate(0.32, 0, 0)
    handle = capsule((0.08, -0.05, 0), (0.06, -0.2, 0), 0.035)
    return [Part("horn", horn, gloss("mg_white", "#EEF1F6", rough=0.3)), Part("band", band, gloss("mg_band", "#E8B53A", rough=0.3), voxel=0.003),
            Part("handle", handle, gloss("mg_handle", "#E8B53A", rough=0.3), voxel=0.003)], VOXEL


def mascot_with_megaphone():
    """The Teams page's left mascot, holding a megaphone up in its raised left hand, horn pointing up-left."""
    from dataclasses import replace
    parts, vx = mascot("megaphone")
    mparts, _ = megaphone()
    hand = np.array(POSES["megaphone"]["hands"][0])
    d = np.array([-0.7, 0.55, 0.45]); d /= np.linalg.norm(d)
    for p in mparts:
        s = p.sdf.scale(1.1).orient((1, 0, 0), tuple(d)).translate(*(hand + np.array([0.0, 0.1, 0.05])))
        parts.append(replace(p, sdf=s))
    return parts, vx


MODELS = dict(llama=llama, megaphone=megaphone, mascot_megaphone_held=mascot_with_megaphone,
              **{f"mascot_{p}": (lambda p=p: mascot(p)) for p in POSES})


def _green_bg(im):
    """The avatar portrait sits on #5BCB8A (SPEC-ui S-04); SHELL clips it to the r 12 frame."""
    from PIL import Image
    bg = Image.new("RGBA", im.size, (91, 203, 138, 255))
    bg.alpha_composite(im)
    return bg


ASSETS = {
    "avatarDefault": dict(model="llama", yaw=-30, pitch=6, frame=(56, 56), fill=(0.98, 0.95), align=(0.6, 1.0), post_fit=_green_bg),
    "_mascotPreview": dict(scene=[("mascot_stand", dict(yaw=-10, pitch=6, pos=(-0.9, 0, 0))), ("mascot_wave", dict(yaw=15, pitch=6, pos=(0.0, 0, 0))),
                                  ("mascot_fall", dict(yaw=0, pitch=6, pos=(0.95, 0, 0)))], frame=(200, 110), fill=0.97, dest="parts"),
}
