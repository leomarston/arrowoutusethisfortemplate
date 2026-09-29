"""AVATARS: the profile / leaderboard / race portraits -- the phone v552 Edit Profile set (meta-003 / meta-004, a 3 x 3
grid; also seen as Sky Jump fans 066-068 / 094 and Streak Race rows; looked at only), reproduced with OUR characters in
the new colours (workers BLUE, the scientist PINK): square head-and-shoulders portraits, 64 x 64 pt @3x (the manifest
size; the Edit Profile cell interior is ~60 pt, the top bar / rows / race chips scale it down), each on its own soft
gradient plate sampled on the cells. The frame around the portrait (blue; green = the player) is UI chrome (avatarFrame).

  cell 1  avatarDefault     grey silhouette -- SVG, art/ui/src/characters/gen_avatars.py
  cell 2  avatarWalkie      navy cap, waving, open laugh, wrench + pouch      plate: green -> yellow
  cell 3  avatarCapGlasses  green cap + big black glasses, leaning in         plate: pink-magenta
  cell 4  avatarDetective   deerstalker + moustache + hand on chin + trench   plate: pink-red
  cell 5  avatarBurger      biting a burger in gloved hands                   plate: orange-red   (new id)
  cell 6  avatarScientist   the scientist, open smile, coat                   plate: VIOLET (theirs pink behind a purple
                            character; ours is pink, so the plate turns violet -- the one deliberate change)
  cell 7  avatarParty       party hat + pink glasses, arm out                 plate: purple
  cell 8  avatarNotebook    green cap + glasses, fist up, notebook           plate: SUNNY yellow (theirs sky blue:
                            our blue worker disappears on it -- the second deliberate plate change)  (new id)
  cell 9  avatarBoxHead     a flat box overhead, gloves, walkie at the belt   plate: green-teal
Cases are char_<id> -> art/out/char_<id>@3x.png (plated; v1's 44 pt char_av* + cut-outs are superseded).
"""
from __future__ import annotations

import math

import numpy as np

import char_kit as K
import char_worker as W
from uikit import Part, box, capsule, capped_cone, cylinder, ellipsoid, gloss, satin, sphere, torus, union  # noqa: F401

VOXEL = 0.006
FRAME = (64, 64)          # the manifest size (Edit Profile cell interior ~60 pt; rows / chips scale it down)
LIGHT = W.WORKER_LIGHT_BLUE

PLATES = {   # (centre, edge) of a soft radial gradient; sampled on meta-003's cells (corners not covered by the character)
    "pink": ("#F98DA6", "#E2506F"), "purple": ("#B76BFF", "#6A12F2"), "violet": ("#A88BFF", "#5F48D8"),
    "greenyellow": ("#E0E23A", "#5ECF78"), "orange": ("#FFC062", "#F2692E"), "orangered": ("#FF8A3A", "#D23300"),
    "pinkmagenta": ("#F58BC2", "#D2438F"), "sky": ("#6AD4FF", "#0098F0"), "sunny": ("#FFE27A", "#F5A01C"), "teal": ("#5CF0B8", "#0FC486"),
}


# ------------------------------------------------------------------ accessories
def party_hat(top=1.90, tilt=18.0):
    cone = capped_cone(0.46, 0.26, 0.02, round=0.02).translate(0, top + 0.18, 0.0)
    dots = []
    rng = np.random.default_rng(4)
    for i in range(14):
        t = 0.1 + 0.8 * rng.random()
        a = rng.random() * 2 * math.pi
        r = 0.26 * (1 - t) + 0.02 * t + 0.008
        dots.append(sphere(0.028).translate(r * math.cos(a), top - 0.05 + t * 0.46, r * math.sin(a)))
    pom = sphere(0.075).translate(0, top + 0.43, 0)
    R = K.rotate_matrix((0, 0, 1), -tilt)
    piv = np.array([0, top - 0.1, 0])

    def xf(s):
        return s.translate(*(-piv)).transform(R).translate(*piv).translate(0.08, 0, -0.04)
    return xf(cone), xf(union(*dots)), xf(pom)


def deerstalker(top=1.90):
    crown = ellipsoid(0.42, 0.24, 0.40).translate(0, top - 0.05, -0.02).intersect(box(1, 0.3, 1).translate(0, top - 0.12 + 0.3, 0))
    band = ellipsoid(0.425, 0.05, 0.405).translate(0, top - 0.12, -0.02)
    brim_f = ellipsoid(0.26, 0.025, 0.18).translate(0, top - 0.14, 0.40).intersect(box(1, 1, 0.5).translate(0, 0, 0.72))
    brim_b = ellipsoid(0.26, 0.025, 0.18).translate(0, top - 0.14, -0.44).intersect(box(1, 1, 0.5).translate(0, 0, -0.76))
    button = sphere(0.035).translate(0, top + 0.19, -0.02)
    flaps = [ellipsoid(0.05, 0.10, 0.14).translate(sx * 0.40, top - 0.02, -0.02) for sx in (-1, 1)]
    return union(crown, band, brim_f.transform(K.rotate_matrix((1, 0, 0), -10)), brim_b, *flaps, k=0.02), button


def moustache(y=1.12, z=0.52):
    lobes = []
    for sx in (-1, 1):
        pts = [np.array([sx * 0.02, y, z + 0.01]), np.array([sx * 0.14, y - 0.03, z - 0.005]), np.array([sx * 0.26, y - 0.01, z - 0.06]),
               np.array([sx * 0.33, y + 0.07, z - 0.11])]
        lobes.append(K.limb(pts, [0.055, 0.068, 0.048, 0.024], k=0.02))
    return union(*lobes, k=0.02)


def top_hat(top=1.90, tilt=-12.0):
    crown = cylinder(0.24, 0.20, round=0.03).translate(0, top + 0.22, 0)
    brim = cylinder(0.38, 0.025, round=0.02).translate(0, top + 0.01, 0)
    band = cylinder(0.245, 0.04).translate(0, top + 0.08, 0)
    R = K.rotate_matrix((0, 0, 1), tilt)
    piv = np.array([0, top, 0])

    def xf(s):
        return s.translate(*(-piv)).transform(R).translate(*piv).translate(-0.10, -0.03, 0)
    return xf(union(crown, brim, k=0.02)), xf(band)


def burger(center, s=1.0):
    c = np.asarray(center, float)
    bun_b = ellipsoid(0.30 * s, 0.07 * s, 0.26 * s).translate(*(c + [0, -0.10 * s, 0]))
    patty = ellipsoid(0.31 * s, 0.05 * s, 0.27 * s).translate(*(c + [0, -0.03 * s, 0]))
    cheese = box(0.25 * s, 0.012 * s, 0.25 * s, round=0.01).translate(*(c + [0, 0.02 * s, 0]))
    lettuce = torus(0.25 * s, 0.035 * s).translate(*(c + [0, 0.045 * s, 0]))
    tomato = ellipsoid(0.26 * s, 0.025 * s, 0.23 * s).translate(*(c + [0, 0.075 * s, 0]))
    bun_t = ellipsoid(0.30 * s, 0.14 * s, 0.26 * s).translate(*(c + [0, 0.10 * s, 0])).intersect(
        box(1, 0.3, 1).translate(*(c + [0, 0.10 * s + 0.3, 0])))
    rng = np.random.default_rng(2)
    seeds = [ellipsoid(0.018 * s, 0.009 * s, 0.011 * s).translate(*(c + [rng.uniform(-0.18, 0.18) * s, 0.21 * s,
                                                                         rng.uniform(-0.05, 0.2) * s])) for _ in range(9)]
    return dict(bunb=bun_b, patty=patty, cheese=cheese, lettuce=lettuce, tomato=tomato, bunt=bun_t, seeds=union(*seeds))


BURGER_MATS = {"bunb": ("#E39A4C", 0.5), "patty": ("#6A3518", 0.55), "cheese": ("#FFC933", 0.35), "lettuce": ("#63C23F", 0.45),
               "tomato": ("#E8402A", 0.35), "bunt": ("#EFA24E", 0.45), "seeds": ("#FFF4DC", 0.4)}


def extra_parts(spec):
    """Accessories beyond char_worker's kit, as Parts (body space, before the lean)."""
    out = []
    b = W.bean()
    if spec.get("party"):
        cone, dots, pom = party_hat()
        out += [Part("partyhat", cone, gloss("a_party", "#F25CAB", rough=0.35), voxel=0.004),
                Part("partydots", dots, gloss("a_dots", "#FFE45C", rough=0.3), voxel=0.003),
                Part("partypom", pom, gloss("a_pom", "#FFE45C", rough=0.4), voxel=0.003)]
    if spec.get("deerstalker"):
        hat, btn = deerstalker()
        out += [Part("deer", hat, K.skin("a_deer", [(0.0, "#B49078"), (0.45, "#8E6A55"), (0.75, "#6E4F3E"), (1.0, "#46302A")], None,
                                         vfn=None, rough=0.7, ior=1.2), voxel=0.004),
                Part("deerbtn", btn, satin("a_deerbtn", "#5E4234"), voxel=0.003)]
    if spec.get("moustache"):
        z = K.surface_z_of(b, 0.0, 1.16) + 0.02
        out.append(Part("moustache", moustache(1.16, z), satin("a_stache", "#3A2418", rough=0.55), voxel=0.003))
    if spec.get("trench"):
        coll = b.offset(0.06).intersect(box(1.2, 0.22, 1.2).translate(0, 0.72, 0), k=0.02).subtract(
            box(0.22, 0.4, 1).translate(0, 0.72, 0.9))
        out.append(Part("trench", coll, K.skin("a_trench", [(0.0, "#FBF1DE"), (0.45, "#EADBC0"), (0.75, "#D3BF9E"), (1.0, "#A58D6A")],
                                               None, vfn=None, rough=0.7, ior=1.2), voxel=0.005))
    if spec.get("tophat"):
        hat, band = top_hat()
        out += [Part("tophat", hat, K.skin("a_tophat", [(0.0, "#A08CC8"), (0.45, "#7A68A8"), (0.75, "#5C4C86"), (1.0, "#3A2E5C")], None,
                                           vfn=None, rough=0.5, ior=1.25), voxel=0.004),
                Part("tophatband", band, satin("a_band", "#2A2240", rough=0.5), voxel=0.003)]
    if spec.get("burger"):
        B = burger(spec["burger"], s=spec.get("burger_s", 1.0))
        for nm, sd in B.items():
            col, rg = BURGER_MATS[nm]
            out.append(Part(nm, sd, gloss(f"a_{nm}", col, rough=rg), voxel=0.003))
    return out


def avatar_worker(spec, colour="blue"):
    parts, vx = W.worker(spec, colour)
    extra = extra_parts(spec)
    roll, pitch = spec.get("lean", (0.0, 0.0))
    if roll or pitch:
        Rl = K.rotate_matrix((0, 0, 1), roll) @ K.rotate_matrix((1, 0, 0), pitch)
        for p in extra:
            p.sdf = p.sdf.transform(Rl)
    if spec.get("red_glasses"):
        for p in parts:
            if p.name == "glasses":
                p.material = gloss("a_redglasses", "#E8406A", rough=0.3, ior=1.4)
    fld = K.field_for(("avatar", repr(sorted((k, repr(v)) for k, v in spec.items())), colour), parts + extra)
    K.shade(extra, field=fld)
    return parts + extra, vx


# ------------------------------------------------------------------ the portraits
_ST = dict(feet=dict(L=((-0.22, 0.30, 0.0), (-0.25, 0.0, 0.08), (-0.2, 0, 1)), R=((0.22, 0.30, 0.0), (0.26, 0.0, 0.08), (0.2, 0, 1))),
           belt=dict(buckle=(-0.12, 0.64), pouch=None, wrench=(0.30, 0.80), wrench_scale=1.1))
_DOWN = dict(L=((-0.60, 1.02, 0.02), (-0.78, 0.74, 0.10), (-0.74, 0.46, 0.20), (0.0, -1.0, 0.2), (0.3, 0.0, 1.0), "open"),
             R=((0.60, 1.02, 0.02), (0.78, 0.74, 0.10), (0.74, 0.46, 0.20), (0.0, -1.0, 0.2), (-0.3, 0.0, 1.0), "open"))
_WAVE_R = ((0.60, 1.04, 0.04), (0.92, 1.20, 0.10), (0.96, 1.62, 0.20), (0.1, 1.0, 0.0), (-0.2, 0.0, 1.0), "wave")
_FIST_L = ((-0.60, 1.02, 0.02), (-0.98, 1.04, 0.16), (-0.92, 1.44, 0.30), (0.1, 1.0, 0.2), (0.2, 0.0, 1.0), "fist")

AVATARS = {
    # v2 (2026-09-25): the PHONE v552 Edit Profile set (meta-003, 3 x 3 grid; cell 1 = avatarDefault, an SVG), in its
    # order, at the manifest size 64 x 64 pt; plates sampled on the cells (looked at only). Case = char_<manifest id>.
    # cell 2: navy cap, waving, big open laugh, wrench + pouch (green -> yellow plate)
    "char_avatarWalkie": (dict(_ST, eyes="open", look=(0.35, 0.10), mouth="laugh", mouth_w=0.36, mouth_h=0.24, hat="navy",
                               hat_tilt=(0, 0, 16), brim_yaw=-30, hat_size=0.82, brows=(0.25, 0.1), eye_c=(0.20, 1.44),
                               eye_r=(0.185, 0.225, 0.13), arms=dict(L=_DOWN["L"], R=_WAVE_R), lean=(6.0, 0.0),
                               belt=dict(buckle=(0.14, 0.64), pouch=(0.44, 0.62), wrench=(-0.30, 0.80), wrench_scale=1.1)),
                          dict(yaw=22, pitch=4), "greenyellow"),
    # cell 3: green cap + big black glasses, leaning in, open laugh (pink plate)
    "char_avatarCapGlasses": (dict(_ST, eyes="open", look=(0.05, 0.05), mouth="laugh", mouth_w=0.32, mouth_h=0.18, hat="green",
                                   hat_tilt=(0, 0, -24), brim_yaw=50, hat_size=0.9, glasses=True, brows=(0.2, -0.1),
                                   eye_c=(0.25, 1.44), arms=dict(L=_DOWN["L"], R=_DOWN["R"]), lean=(14.0, 0.0)),
                              dict(yaw=-26, pitch=4), "pinkmagenta"),
    # cell 4: detective -- deerstalker, moustache, half lids, hand on chin, trench collar (pink-red plate)
    "char_avatarDetective": (dict(_ST, eyes="half", look=(0.35, 0.0), mouth="smile", mouth_w=0.26, hat=None, deerstalker=True,
                                  moustache=True, trench=True, brows=(0.12, -0.25),
                                  arms=dict(L=_DOWN["L"], R=((0.60, 1.00, 0.04), (0.62, 0.66, 0.46), (0.22, 0.90, 0.66),
                                                             (-0.3, 1.0, 0.2), (0.0, 0.2, 1.0), "fist"))),
                             dict(yaw=-20, pitch=4), "pink"),
    # cell 5: biting a burger held in both gloved hands, huge eyes (orange-red plate)
    "char_avatarBurger": (dict(_ST, eyes="open", look=(-0.1, 0.25), mouth="open", mouth_w=0.36, mouth_h=0.24, hat=None,
                               brows=(0.25, 0.0), burger=(0.02, 1.02, 0.70), burger_s=1.35, gloves=True, eye_r=(0.20, 0.25, 0.13),
                               arms=dict(L=((-0.60, 1.02, 0.02), (-0.72, 0.80, 0.40), (-0.34, 0.98, 0.70), (0.8, 0.3, 0.2),
                                            (1.0, 0.0, 0.2), "grip"),
                                         R=((0.60, 1.02, 0.02), (0.72, 0.80, 0.40), (0.34, 0.98, 0.70), (-0.8, 0.3, 0.2),
                                            (-1.0, 0.0, 0.2), "grip"))),
                          dict(yaw=6, pitch=4), "orangered"),
    # cell 7: party hat + pink glasses, arms out, wrench (purple plate)
    "char_avatarParty": (dict(_ST, eyes="open", look=(0.1, 0.05), mouth="laugh", mouth_w=0.30, mouth_h=0.18, hat=None, party=True,
                              glasses=True, red_glasses=True, brows=(0.18, 0.1), eye_c=(0.25, 1.44),
                              arms=dict(L=_DOWN["L"], R=_WAVE_R)),
                         dict(yaw=18, pitch=4), "purple"),
    # cell 8: green cap + glasses, fist up, the spiral notebook (clipboard) held at his side (sky-blue plate)
    "char_avatarNotebook": (dict(_ST, eyes="open", look=(0.05, 0.05), mouth="grin", mouth_w=0.30, hat="green",
                                 hat_tilt=(0, 0, -24), brim_yaw=50, hat_size=0.9, glasses=True, brows=(0.2, -0.1),
                                 eye_c=(0.25, 1.44), arms=dict(L=_FIST_L, R=((0.60, 1.00, 0.02), (0.80, 0.74, 0.30),
                                                                             (0.62, 0.92, 0.56), (-0.4, 1.0, 0.2),
                                                                             (-0.8, 0.0, 0.6), "grip")),
                                 props=[("clipboard", dict(center=(0.74, 1.06, 0.52), up=(-0.2, 1.0, 0.1),
                                                           facing=(-0.6, 0.0, 1.0), s=1.25))]),
                            dict(yaw=-22, pitch=4), "sunny"),   # theirs sky blue: a BLUE worker vanished on it
    # cell 9: the box carrier -- a flat box overhead in gloved hands, walkie at the belt (green-teal plate)
    "char_avatarBoxHead": (dict(_ST, eyes="open", look=(0.0, 0.35), mouth="laugh", mouth_w=0.34, mouth_h=0.22, hat=None,
                                no_brows=True, gloves=True, eye_r=(0.19, 0.24, 0.13),
                                arms=dict(L=((-0.60, 1.14, 0.0), (-0.86, 1.55, 0.10), (-0.60, 1.96, 0.22), (0.2, 1.0, 0.1),
                                             (0.3, 0.0, 1.0), "grip"),
                                          R=((0.60, 1.14, 0.0), (0.86, 1.55, 0.10), (0.60, 1.96, 0.22), (-0.2, 1.0, 0.1),
                                             (-0.3, 0.0, 1.0), "grip")),
                                props=[("box", dict(center=(0.0, 2.24, 0.10), up=(0.0, 1.0, 0.0), facing=(-0.3, 0.0, 1.0),
                                                    shape=dict(w=1.8, h=0.36, d=1.0))),
                                       ("walkie", dict(center=(-0.64, 0.70, 0.22), up=(0.0, 1.0, 0.0), facing=(-0.8, 0.0, 0.6),
                                                       s=0.9))],
                                belt=dict(buckle=(-0.10, 0.64), pouch=None, wrench=(0.36, 0.80), wrench_scale=1.1)),
                           dict(yaw=8, pitch=-6), "teal"),
}
# not in the v552 set (kept as a model for the loading crowd): the top-hat worker
EXTRA = {"tophat": dict(_ST, eyes="open", look=(0.2, 0.1), mouth="open", mouth_w=0.30, mouth_h=0.16, hat=None, tophat=True,
                        brows=(0.2, 0.0), arms=dict(L=_DOWN["L"], R=_WAVE_R))}

# framing (v2, measured on meta-003): the frame (UI) covers ~4.5 pt of each edge, so the visible interior is the central
# 55 pt; their bean is ~70 % of that interior wide (115 of 165 phone px) with the eyes at ~40 % of its height and the belt
# near its bottom -> 30 pt/u at 64 pt, the view centred 0.19 u below the eyes (v1 at 44 pt: 26 pt/u, eyes centred,
# read ~25 % too big inside the frame)
# director round 2 (grader B: every portrait ~0.7x of the phone's close-up, frontal, one shared grin): the camera 1.4x
# closer (the bean now spans the interior width and the head is cropped by the frame on the tall ones), eyes at ~40 %
# of the tile height, the belt at the bottom edge; 3/4 turns per cell; the open mouths use the worker "laugh" (one
# tooth band) instead of the two-buck-teeth D; the scientist smiles (the loading "grin")
AV_SCALE = 40.0 * FRAME[0] / 64.0
MODELS = {}
ASSETS = {}


def _plate(colours):
    c0, c1 = (K.hexrgb(h) for h in colours)

    def post(im):
        from PIL import Image as _I
        W_, H_ = im.size
        yy, xx = np.mgrid[0:H_, 0:W_]
        r = np.clip(np.hypot((xx - W_ * 0.45) / W_, (yy - H_ * 0.38) / H_) / 0.75, 0, 1)[..., None]
        col = c0 * (1 - r) + c1 * r
        bg = _I.fromarray((col * 255).astype(np.uint8)).convert("RGBA")
        bg.alpha_composite(im)
        return bg
    return post


for _name, (_spec, _pose, _plate_name) in AVATARS.items():
    MODELS[_name] = (lambda s=_spec: avatar_worker(s))
    _view = K.view_bounds(FRAME, scale_pt=AV_SCALE, center=(0.04, 1.43 if _name != "char_avatarBoxHead" else 1.52),
                          zr=(-0.8, 1.0), margin=1.0)
    _common = dict(scene=[(_name, dict(_pose, center=False))], bounds=_view, frame=FRAME, fov=18, light=LIGHT, no_fit=True)
    ASSETS[_name] = dict(post_fit=_plate(PLATES[_plate_name]), **_common)

# the scientist portrait (cell 6): head + coat collar, open smile, looking at the viewer. Plate VIOLET: theirs is pink
# behind a PURPLE character; ours is pink, so the plate turns violet (the one deliberate change).
import char_scientist as SC  # noqa: E402

SC.POSES["portrait"] = dict(yaw=-8.0, lean=0.0, head=dict(roll=-4.0, yaw=6.0, nod=4.0), arms="console")
_SPOSE = dict(yaw=0, pitch=2, center=False)
MODELS["char_avatarScientist"] = lambda: SC.scientist("portrait", mouth="grin", view_pose=_SPOSE, look=(0.05, -0.05),
                                                     n_strands=30000)
_sview = K.view_bounds(FRAME, scale_pt=34.0 * FRAME[0] / 64.0, center=(-0.06, 1.98), zr=(-1.0, 1.2), margin=1.0)  # r2: 27.5 -> 37 pt/u
_sc = dict(scene=[("char_avatarScientist", _SPOSE)], bounds=_sview, frame=FRAME, fov=18, light=K.light(), no_fit=True)
ASSETS["char_avatarScientist"] = dict(post_fit=_plate(PLATES["violet"]), **_sc)

# the Edit Profile order (meta-003, row-major; avatarDefault is the SVG silhouette)
PROFILE_ORDER = ["avatarDefault", "avatarWalkie", "avatarCapGlasses", "avatarDetective", "avatarBurger", "avatarScientist",
                 "avatarParty", "avatarNotebook", "avatarBoxHead"]
