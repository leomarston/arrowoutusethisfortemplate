"""Characters lane kit: shared helpers for the 3D character recipes (char_doc.py, char_worker.py).

Not a board item (no build()): the characters are UI/scene renders driven by char_make.py, which runs the
pipeline's ui3d.py READ-ONLY with these recipes (see art/lanes/requests.md #1).

What lives here
  - cartoon limbs: hand() (palm + stubby fingers + thumb), limb() (shoulder -> elbow -> wrist tube)
  - eyes: glossy_eye() (sclera/iris/pupil/highlights) and bead_eye() (small dark eye with a big highlight)
  - SHADING: toy renders of the reference glow warm in their creases and read translucent at thin edges. PBR in
    RealityKit has neither AO nor SSS, so the albedo is driven per VERTEX: the whole character's soft occupancy is
    voxelised once, blurred at two radii (volumetric obscurance), and each shaded part gets uv = (cavity, custom)
    into a small 2D LUT texture: u < 0.5 = convex/thin (lighter, warmer: fake SSS), 0.5 = flat (base colour),
    u > 0.5 = creases (deeper, SATURATED hue shift: the warm glow). v is a per-part term (blush, root->tip ...).
  - the home-scene rig: a blue/lavender room environment (the home screen's walls and floor) and CHAR_LIGHT.

Authoring: +Y up, +Z toward the viewer, units ~ one character height of 2.
"""
from __future__ import annotations

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PIPE = os.path.dirname(HERE)
ART = os.path.dirname(PIPE)
APP = os.path.dirname(ART)
for _p in (PIPE, os.path.join(ART, "ui", "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from mesher import Material  # noqa: E402
from sdf import SDF, capsule, ellipsoid, round_cone, sphere, union  # noqa: E402

F = np.float32


# ------------------------------------------------------------------ small vector helpers

def unit(v):
    v = np.asarray(v, float)
    return v / max(np.linalg.norm(v), 1e-9)


def frame_from(d, n):
    """Orthonormal frame: y = d, z = n made perpendicular to d, x = y cross z. Returns R with columns (x, y, z)."""
    y = unit(d)
    z = np.asarray(n, float) - y * (np.dot(n, y))
    z = unit(z if np.linalg.norm(z) > 1e-6 else np.cross(y, [1.0, 0, 0]))
    x = np.cross(y, z)
    return np.stack([x, y, z], 1)


def rotate_about(v, axis, deg):
    a = unit(axis)
    t = math.radians(deg)
    v = np.asarray(v, float)
    return v * math.cos(t) + np.cross(a, v) * math.sin(t) + a * np.dot(a, v) * (1 - math.cos(t))


def local_ellipsoid(radii, R, center):
    """Ellipsoid with semi-axes along R's columns (x, y, z)."""
    return ellipsoid(*radii).transform(R).translate(*np.asarray(center, float))


# ------------------------------------------------------------------ limbs

def limb(points, radii, k=0.04):
    """A soft tube through shoulder -> elbow -> wrist (round cones, smooth-joined)."""
    segs = [round_cone(tuple(points[i]), tuple(points[i + 1]), radii[i], radii[i + 1]) for i in range(len(points) - 1)]
    return union(*segs, k=k)


def hand(wrist, d, palm_n, r=0.12, fingers=3, finger_len=0.95, finger_r=0.40, spread=24.0, curl=28.0, thumb=1.0,
         thumb_side=1, thumb_angle=55.0, palm_flat=0.72, k=0.30):
    """A stubby cartoon hand. wrist: point; d: forearm direction (toward the fingers); palm_n: where the palm faces.
    r = palm radius; finger_len / finger_r are fractions of r; spread = degrees between fingers; curl = how far each
    finger bends toward the palm; thumb_side +1/-1 = which side of the palm (x of the frame) the thumb is on."""
    R = frame_from(d, palm_n)
    ex, ey, ez = R[:, 0], R[:, 1], R[:, 2]
    wrist = np.asarray(wrist, float)
    c = wrist + ey * r * 0.85
    palm = local_ellipsoid((r * 1.0, r * 0.95, r * palm_flat), R, c)
    parts = [palm]
    fr = r * finger_r
    L = r * finger_len
    n = fingers
    for i in range(n):
        a = (i - (n - 1) / 2) * spread
        fd = rotate_about(ey, ez, -a)                     # fan in the palm plane
        base = c + fd * r * 0.62 + ez * r * 0.05
        mid = base + fd * L * 0.55
        tipdir = rotate_about(fd, np.cross(fd, ez), curl)  # curl toward the palm side
        tip = mid + unit(tipdir) * L * 0.45
        parts.append(round_cone(tuple(base), tuple(mid), fr * 1.05, fr))
        parts.append(round_cone(tuple(mid), tuple(tip), fr, fr * 0.92))
    if thumb:
        tb = c + ex * thumb_side * r * 0.70 - ey * r * 0.15 + ez * r * 0.15
        td = unit(rotate_about(ey, ez, -thumb_side * thumb_angle) + ez * 0.35)
        tt = tb + td * r * 0.75 * thumb
        parts.append(round_cone(tuple(tb), tuple(tt), fr * 1.15, fr * 1.0))
    return union(*parts, k=r * k)


# ------------------------------------------------------------------ eyes

def bead_eye(center, r, look=(0.0, 0.0, 1.0), hl=(0.35, 0.42), hl_size=0.42):
    """A small dark glossy bead eye with one big + one small highlight (Doc).
    Returns (eye_sdf, highlight_sdf)."""
    c = np.asarray(center, float)
    eye = ellipsoid(r, r * 1.12, r * 0.8).translate(*c)
    lk = unit(look)
    front = c + lk * r * 0.62
    h1 = sphere(r * hl_size).translate(*(front + np.array([-hl[0] * r, hl[1] * r, 0.0])))
    h2 = sphere(r * hl_size * 0.45).translate(*(front + np.array([hl[0] * r * 0.9, -hl[1] * r * 0.9, 0.0])))
    return eye, union(h1, h2)


# ------------------------------------------------------------------ shading: per-vertex obscurance -> LUT albedo

def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255.0


def _ramp(stops, u):
    us = np.array([s[0] for s in stops], float)
    cs = np.array([hexrgb(s[1]) for s in stops])
    out = np.empty(u.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(u, us, cs[:, ch])
    return out


def lut(ramp0, ramp1=None):
    """2D LUT texture fn(u, v) -> sRGB. ramp0 at v=0, ramp1 at v=1 (lists of (u, hex)); linear blend in v."""
    def fn(u, v):
        a = _ramp(ramp0, u)
        if ramp1 is None:
            return a
        b = _ramp(ramp1, u)
        return a + (b - a) * v[..., None]
    return fn


def skin(name, ramp0, ramp1=None, vfn=None, rough=0.42, ior=1.30, clearcoat=0.0, cc_rough=0.18, emissive=None,
         size=(128, 32)):
    """ramp0/ramp1: [(u, hex)]: u = 0 thin/convex, 0.5 flat, 1 deep crease. vfn(points) -> [0,1] (or None)."""
    m = Material(name, ramp0[len(ramp0) // 2][1], roughness=rough, ior=ior, clearcoat=clearcoat,
                 clearcoat_roughness=cc_rough, emissive=emissive, texture=lut(ramp0, ramp1), texture_size=size)
    m.__dict__["_vfn"] = vfn  # dataclass without slots: carry the per-part v term
    return m


class Field:
    """Soft occupancy of a whole character, blurred at two radii (volumetric obscurance)."""

    def __init__(self, parts, spacing=0.013, sig_f=0.035, sig_b=0.11, log=print):
        from scipy import ndimage
        lo = np.min([p.sdf.lo for p in parts], 0) - 2 * sig_b
        hi = np.max([p.sdf.hi for p in parts], 0) + 2 * sig_b
        n = np.ceil((hi - lo) / spacing).astype(int) + 1
        occ = np.zeros(tuple(n), np.float32)
        for p in parts:
            if not getattr(p, "occluder", True):
                continue
            a = np.clip(np.floor((p.sdf.lo - lo) / spacing).astype(int) - 2, 0, n - 1)
            b = np.clip(np.ceil((p.sdf.hi - lo) / spacing).astype(int) + 3, 1, n)
            xs = lo[0] + np.arange(a[0], b[0]) * spacing
            ys = lo[1] + np.arange(a[1], b[1]) * spacing
            zs = lo[2] + np.arange(a[2], b[2]) * spacing
            for ix in range(0, len(xs), 24):  # slabs: bounded memory
                X, Y, Z = np.meshgrid(xs[ix:ix + 24], ys, zs, indexing="ij")
                P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).astype(F)
                d = p.sdf(P).reshape(X.shape)
                soft = np.clip(0.5 - d / spacing, 0, 1).astype(np.float32)
                sl = occ[a[0] + ix:a[0] + ix + X.shape[0], a[1]:b[1], a[2]:b[2]]
                np.maximum(sl, soft, out=sl)
        self.lo, self.spacing = lo, spacing
        self.fine = ndimage.gaussian_filter(occ, sig_f / spacing)
        self.broad = ndimage.gaussian_filter(occ, sig_b / spacing)
        log(f"    field {tuple(n)} voxels @ {spacing}")

    def sample(self, pts):
        from scipy.ndimage import map_coordinates
        q = ((np.asarray(pts, float) - self.lo) / self.spacing).T
        return (map_coordinates(self.fine, q, order=1, mode="nearest"),
                map_coordinates(self.broad, q, order=1, mode="nearest"))


def cavity_u(field, pts, gain=2.2, w_fine=0.55):
    f, b = field.sample(pts)
    cav = w_fine * (f - 0.5) + (1 - w_fine) * (b - 0.5)
    return np.clip(0.5 + gain * cav, 0.02, 0.98)


def shade(parts, full=None, field=None, gain=2.2):
    """Give every part with a LUT material a per-vertex uv sampler. The obscurance field is built from `full`
    (the WHOLE character in this pose), so a layer rendered alone keeps the creases of the full character."""
    fld = field or Field(full or parts)
    for p in parts:
        tex = getattr(p.material, "texture", None)
        if tex is None or "_vfn" not in p.material.__dict__:
            continue
        vfn = p.material.__dict__["_vfn"]

        def sampler(v, vfn=vfn, g=gain):
            u = cavity_u(fld, v, gain=g)
            vv = np.clip(vfn(v), 0.03, 0.97) if vfn else np.full(len(v), 0.03)
            return np.stack([u, vv], 1)
        p.uv = ("fn", sampler)
    return parts


# ------------------------------------------------------------------ the home-scene rig

def char_env(path=None):
    """Equirect environment of the home scene's room: pale lavender ceiling, blue-lavender walls, a light lavender
    floor (home.floor #D0D2ED, walls ~#8FA0DC on 002), a big warm soft box upper-left-front (the key's reflection)
    and a cool bright strip right-back (the rim's reflection). Made once into build/ui-art/char_env.png."""
    from PIL import Image
    path = path or os.path.join(APP, "build", "ui-art", "char_env.png")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    W, H = 512, 256
    u, v = np.meshgrid((np.arange(W) + 0.5) / W, (np.arange(H) + 0.5) / H)
    phi = (u - 0.5) * 2 * math.pi
    theta = v * math.pi
    d = np.stack([np.sin(theta) * np.sin(phi), np.cos(theta), -np.sin(theta) * np.cos(phi)], -1)
    t = d[..., 1]
    ceil = np.array([0.86, 0.88, 0.98]); wall = np.array([0.50, 0.57, 0.88]); floor = np.array([0.78, 0.79, 0.93])
    col = np.where(t[..., None] > 0, wall + (ceil - wall) * np.clip(t, 0, 1)[..., None] ** 0.8,
                   wall + (floor - wall) * np.clip(-t * 2.2, 0, 1)[..., None])
    for k, amp, width in (((-0.55, 0.62, 0.56), np.array([0.62, 0.56, 0.46]), 0.78),
                          ((0.78, 0.22, -0.58), np.array([0.34, 0.40, 0.52]), 0.86)):
        kk = unit(k)
        col = col + np.clip((d @ kk - width) / (1 - width), 0, 1)[..., None] ** 1.3 * amp
    Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(path)
    return path


# key warm from the upper left in front, a cool lavender rim from the right-back (the blue room), a warm bounce
# from below-front (fakes the reference bodies' warm translucency), the room as the ambient dome.
# Levels calibrated on the reference's value distribution (002: fur V p50 0.83, coat V p50 0.88): 0.72x the first
# rig, which clipped the coat and skin to V 1.0 (iteration log in art/lanes/characters.md).
CHAR_LIGHT = dict(key_dir=(0.50, -0.62, -0.60), key_lux=1730.0, key_color=(1.0, 0.965, 0.92),
                  rim_dir=(-0.72, -0.30, 0.62), rim_lux=1080.0, rim_color=(0.80, 0.86, 1.0),
                  fill_dir=(0.15, 0.85, -0.50), fill_lux=375.0, fill_color=(1.0, 0.80, 0.62),
                  ibl_exp=-1.02)


def light(**over):
    d = dict(CHAR_LIGHT, env=char_env())
    d.update(over)
    return d


# ------------------------------------------------------------------ misc recipe helpers

def rotate_matrix(axis, deg):
    from sdf import _rot
    return _rot(axis, deg)


def surface_z_of(s, x, y, z0=2.5):
    """Sphere-trace along -Z at (x, y) from z0 down to the surface of `s`; returns z (front surface)."""
    z = z0
    for _ in range(400):
        d = float(s(np.array([[x, y, z]], np.float32))[0])
        if d < 1e-4:
            break
        z -= max(d, 1e-4)
    return z


_FIELDS = {}


def field_for(key, parts):
    """One obscurance Field per (character, pose) per process (layers of one pose share it)."""
    if key not in _FIELDS:
        _FIELDS[key] = Field(parts)
    return _FIELDS[key]


def view_bounds(frame, scale_pt, center, zr=(-1.0, 1.0), focus_z=None, margin=1.06, fov=18.0):
    """Bounds for ui3d's scene_job so that the render maps `scale_pt` pt per unit at depth focus_z (default: the
    middle of zr), with the view centred on center=(x, y). Frame aspect = bounds aspect (no_fit keeps registration)."""
    fw, fh = frame
    z0, z1 = zr
    zf = (z0 + z1) / 2 if focus_z is None else focus_z
    t = math.tan(math.radians(fov) / 2)
    half_h = fh / (2 * scale_pt) - t * (z1 - zf)
    ext_y = 2 * (half_h - 0.02) / margin
    ext_x = ext_y * fw / fh
    cx, cy = center
    return ((cx - ext_x / 2, cy - ext_y / 2, z0), (cx + ext_x / 2, cy + ext_y / 2, z1))


# ------------------------------------------------------------------ explicit rigs (rig.py "explicit" mode, built here)

def explicit_rig(models, assets, name, factory, frame, bounds, pose, light, layers, full_kw=None, fov=18.0,
                 full_anchors=None, full_case=None):
    """Register one character's full case + one case per puppet layer on a recipe's MODELS / ASSETS, all sharing ONE
    view (explicit bounds, no_fit, center=False), and return the RIGS spec for art/ui/tools/rig.py.

    factory(only=set|None, **kw) -> (parts, voxel): builds the whole character (so obscurance / fur see all of it) and
    returns only the named parts. layers: [dict(name, parts={...}, kw={...}, holdout={...} (parts of the layers BEHIND
    this one, rendered as a matte so the layer keeps only what the full render shows), pivots={k: xyz}, group, default,
    overlay, parent, note)] back -> front."""
    import hashlib
    full_kw = full_kw or {}
    pose = dict(pose, center=False)
    common = dict(bounds=bounds, frame=frame, fov=fov, light=light, no_fit=True)
    fm = f"{name}_full"
    models[fm] = lambda: factory(**full_kw)
    full_case = full_case or f"char_{name}"
    assets[full_case] = dict(scene=[(fm, pose)], **common)
    if full_anchors:
        assets[full_case]["anchors"] = {k: [list(v)] for k, v in full_anchors.items()}
    out_layers, notes = [], {}
    for L in layers:
        kw = dict(full_kw, **L.get("kw", {}))
        mn = f"{name}_{L['name']}"
        models[mn] = (lambda L=L, kw=kw: factory(only=set(L["parts"]), **kw))
        scene = [(mn, pose)]
        if L.get("holdout"):
            hkw = dict(full_kw, **L.get("holdout_kw", {}))
            key = hashlib.sha1((",".join(sorted(L["holdout"])) + repr(sorted(hkw.items()))).encode()).hexdigest()[:8]
            hm = f"{name}_ho_{key}"
            models[hm] = (lambda L=L, hkw=hkw: factory(only=set(L["holdout"]), **hkw))
            scene.append((hm, dict(pose, holdout=True)))
        case = f"char_{name}_L_{L['name']}"
        assets[case] = dict(scene=scene, dest="parts", **common)
        if L.get("pivots"):
            assets[case]["anchors"] = {k: [list(v)] for k, v in L["pivots"].items()}
        out_layers.append((L["name"], case))
        notes[L["name"]] = {k: L[k] for k in ("group", "default", "overlay", "parent", "note") if k in L}
    return dict(full=full_case, layers=out_layers, layer_notes=notes)


# ------------------------------------------------------------------ comparison sheets (reference LOOKED AT only)

def shot(path_rel, width=1178):
    """A capture as RGBA at phone px (store shots, 1320 px wide, are scaled to the phone's 1178 px = 393 pt)."""
    from PIL import Image
    im = Image.open(os.path.join(APP, path_rel)).convert("RGBA")
    if im.width != width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    return im


def layer_composite(rig_dir, names):
    """Compose named rig layers (in rig z order) into the full frame (@3x)."""
    import json as _json
    from PIL import Image
    rj = _json.load(open(os.path.join(rig_dir, "rig.json")))
    fw, fh = rj["frame_pt"]
    cv = Image.new("RGBA", (round(fw * 3), round(fh * 3)), (0, 0, 0, 0))
    for L in rj["layers"]:
        if L["name"] in names:
            im = Image.open(os.path.join(rig_dir, L["file"])).convert("RGBA")
            cv.alpha_composite(im, (round(L["rect_pt"][0] * 3), round(L["rect_pt"][1] * 3)))
    return cv, rj


def on_shot(base, im3x, x_pt, y_pt, s_pt=1178 / 393.0):
    """Paste an @3x image with its top-left at (x_pt, y_pt) on a phone-px shot (returns a copy)."""
    from PIL import Image
    out = base.copy()
    sm = im3x.resize((max(1, round(im3x.width * s_pt / 3)), max(1, round(im3x.height * s_pt / 3))), Image.LANCZOS)
    out.alpha_composite(sm, (round(x_pt * s_pt), round(y_pt * s_pt)))
    return out


def flat_like(base, box, color=None):
    """A flat backdrop the size of `base` in the median colour of the box's top rows (or `color`)."""
    from PIL import Image
    if color is None:
        a = np.asarray(base.convert("RGB"))[box[1]:box[1] + 16, box[0]:box[2]].reshape(-1, 3)
        color = tuple(int(v) for v in np.median(a, 0))
    return Image.new("RGBA", base.size, tuple(color) + (255,))


def diffuse_fill(im, mask, iters=400):
    """Crude clean plate for colour reads on the sheets: fill mask (bool HxW) by iterated neighbour averaging
    (a smooth blob where the reference character stood). Only used on comparison sheets, never shipped."""
    from PIL import Image
    from scipy import ndimage
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    m = mask.astype(bool)
    out = a.copy()
    out[m] = 0
    w = (~m).astype(np.float32)
    k = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], np.float32)
    # multigrid-ish: start from a heavy blur of the known pixels, then relax
    num = ndimage.gaussian_filter(out * w[..., None], (40, 40, 0))
    den = ndimage.gaussian_filter(w, 40)[..., None]
    out[m] = (num / np.maximum(den, 1e-4))[m]
    for _ in range(iters):
        nb = np.stack([ndimage.convolve(out[..., c], k, mode="nearest") for c in range(3)], -1) / 4
        out[m] = nb[m]
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).convert("RGBA")
