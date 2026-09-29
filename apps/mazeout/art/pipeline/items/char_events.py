"""EVENT HEADERS (characters lane): our BLUE workers in the Claw Challenge header and the Streak Race header,
reproduced from the phone v552 (looked at only: 023-claw-challenge-c, meta-039; meta-045 / 203 Streak Race).

workerClawPair (023, header 393 x 240 pt; the scene lane's clawHeaderArt composites this render centred at (200, 115)
pt, behind its claw + prize heap):
  LEFT  navy cap tilted back, turned to screen right, huge open laugh, eyes up-right; fist raised at the left
        (px 80..185 x 325..425), the other hand gripping the machine's red-knob joystick (px 480..610 x 350..420).
        Bean x 165..500 px, cap top y ~115, eyes L 245..330 x 210..340 (close-up: eyes ~1.4x the home ones).
  RIGHT green cap tilted back, big black glasses (frames x 690..950, y 200..360), open smile, one open hand raised by
        the head (px 590..690 x 210..330), the other waving out at the right (px 1000..1120 x 345..460).
  Bodies below y ~460 px are hidden by the prize heap, so the frame (360 x 170 pt, x 20..380 / y 30..200 pt on the
  header) cuts them: full bleed at the bottom by design.
  Scale: their bean ~330 px (110 pt) wide at the eyes = 1.3 u -> 86 pt/u (1.5x the home workers).

    $PY art/pipeline/items/char_make.py render char_workerClawPair
"""
from __future__ import annotations

import numpy as np

import char_kit as K
import char_worker as W
from uikit import Part, capsule, gloss, satin, sphere, union  # noqa: F401

VOXEL = 0.006
LIGHT = W.WORKER_LIGHT_BLUE
COLOUR = "blue"

# ------------------------------------------------------------------ Claw Challenge header: the pair
_FEET = W.HOME_L["feet"]
CLAW_L = dict(
    eyes="open", look=(0.45, 0.35), eye_c=(0.20, 1.46), eye_r=(0.20, 0.27, 0.14), mouth="open", mouth_w=0.44, mouth_h=0.32,
    mouth_y=0.98, hat="navy", hat_tilt=(-16, 0, 14), brim_yaw=-30, hat_size=0.92, brows=(0.30, 0.15), girth=1.08,
    # v2: the cheering fist is pumped at mouth level beside the body (023: px 80..185 x 325..425), not out sideways
    arms=dict(L=((-0.56, 1.00, 0.02), (-0.86, 0.72, 0.20), (-0.80, 1.02, 0.38), (0.05, 1.0, 0.15), (0.3, 0.0, 1.0), "fist"),
              R=((0.56, 1.00, 0.04), (0.92, 0.84, 0.34), (0.96, 1.00, 0.66), (0.1, 1.0, 0.3), (-1.0, 0.0, 0.2), "grip")),
    feet=_FEET, belt=dict(buckle=(0.10, 0.64), pouch=None, wrench=(-0.22, 0.80), wrench_scale=1.2),
)
CLAW_R = dict(
    eyes="open", look=(-0.35, 0.15), eye_c=(0.25, 1.44), eye_r=(0.19, 0.25, 0.13), mouth="open", mouth_w=0.34, mouth_h=0.20,
    hat="green", hat_tilt=(-14, 0, -14), brim_yaw=40, hat_size=0.92, glasses=True, brows=(0.25, 0.0),
    # v2: one open hand up at eye level beside the glasses (023: px 590..690 x 210..330), the other held out low at the
    # right, palm to the viewer (px 1000..1120 x 345..460)
    arms=dict(L=((-0.56, 1.02, 0.02), (-0.84, 1.02, 0.22), (-0.66, 1.28, 0.44), (0.1, 1.0, 0.1), (0.1, 0.0, 1.0), "wave"),
              R=((0.56, 1.02, 0.02), (0.88, 0.80, 0.14), (0.94, 0.94, 0.30), (0.35, 1.0, 0.1), (-0.1, 0.0, 1.0), "wave")),
    feet=_FEET, belt=dict(buckle=(-0.10, 0.64), pouch=(0.42, 0.60), wrench=None),
)


def joystick(knob, stick_len=0.52, r_knob=0.12):
    """The claw machine's joystick the left worker grips: a red ball knob on a white stick with a grey boot."""
    k = np.asarray(knob, float)
    base = k + np.array([0.02, -stick_len, 0.0])
    stick = capsule(tuple(k), tuple(base), 0.035)
    return [Part("jknob", sphere(r_knob).translate(*k), gloss("e_jknob", "#E8262E", rough=0.25, ior=1.45), voxel=0.003),
            Part("jstick", stick, gloss("e_jstick", "#F2F2F6", rough=0.3), voxel=0.003),
            Part("jboot", sphere(0.07).scale_xyz(1.0, 0.55, 1.0).translate(*base), satin("e_jboot", "#9097B2", rough=0.4),
                 voxel=0.003)]


def claw_left():
    parts, vx = W.worker(CLAW_L, COLOUR)
    wr = np.array(CLAW_L["arms"]["R"][2]) + np.array([0.07, 0.0, 0.0])      # arm_push (worker() pushes arms out)
    return parts + joystick(wr + np.array([0.02, -0.05, 0.10])), vx


CLAW_SCALE = 86.0
CLAW_FRAME = (360, 170)
# view centred on the frame centre (= header (200, 115) pt); workers placed by their eyes: left eyes ~ (96, 93) pt,
# right glasses centre ~ (273, 93) pt on the header (v2: their left eyes span 245..400 px -> centre ~107 pt; the turned
# head's eye midpoint projects ~3 pt right of the body axis)
CLAW_VIEW = K.view_bounds(CLAW_FRAME, scale_pt=CLAW_SCALE, center=(0.0, 0.0), zr=(-1.4, 1.4), margin=1.0)
CLAW_POS_L = ((104 - 200) / CLAW_SCALE, (115 - 93) / CLAW_SCALE - 1.46, 0.0)
CLAW_POS_R = ((276 - 200) / CLAW_SCALE, (115 - 95) / CLAW_SCALE - 1.44, -0.15)

MODELS = {"claw_L": claw_left, "claw_R": lambda: W.worker(CLAW_R, COLOUR)}
ASSETS = {
    "char_workerClawPair": dict(scene=[("claw_L", dict(yaw=22, pitch=4, center=False, pos=CLAW_POS_L)),
                                       ("claw_R", dict(yaw=-16, pitch=4, center=False, pos=CLAW_POS_R))],
                                bounds=CLAW_VIEW, frame=CLAW_FRAME, fov=18, light=LIGHT, no_fit=True),
}


# ================================================================== Streak Race header (workerRacers, 393 x 290 pt)
# meta-045 / meta-050 / 203 (phone v552, looked at only): a pink spiral slide seen from above-front -- a small far turn
# at the upper left (the "9" loop, its hole showing the room), the chute descending on the right and sweeping across
# the front to the bottom-left; four workers ride cyan glowing sleds: two small ones up the chute (navy caps, arms up;
# one lying back), two big ones on the front sweep (LEFT navy kepi, arms out, laughing; RIGHT green cap + glasses,
# crouched, hands on the sled). Room: lavender ceiling with pipes + lamps, a cream machine with an orange-framed screen
# at the left, crates at both sides, tiled floor, a checkered banner at the bottom-left. The logo plate (live text) sits
# over the bottom edge. Track colours sampled by eye: inner purple #9A56D6 -> pink #EE6AB0 at the rims, outer #EC5FA3.
# Built as ONE render (track + sleds + riders; near-orthographic camera, the chute's perspective faked by its width
# growing toward the viewer, riders tipped 22 deg toward the camera) over a painted, defocused room (post_fit).
# Our workers BLUE (owner 02:55).
#     $PY art/pipeline/items/char_make.py render char_workerRacers      (~80 s; --draft for a quick look)
import math as _m  # noqa: E402

from mesher import Material as _Mat  # noqa: E402
from uikit import box, cylinder  # noqa: E402

import char_fur as _FUR  # noqa: E402  (fur_part = the generic premeshed Part)
import char_props as CP  # noqa: E402

RACE_FRAME = (393, 290)
RACE_SCALE = 40.0                 # pt per unit (a near-orthographic camera, fov 10: the illustration's perspective is
#                                   faked by the chute widening toward the viewer, as theirs does)
# v2: the chute follows a SCREEN path traced by eye on meta-045 (the "9": entry hidden under the stem, the loop at the
# upper left, the small riders at its top-right, the stem down the right, the wide sweep across the front to the exit at
# the bottom-left). Points: (x, y) pt on the 393 x 290 header, inner trough width pt, depth (u, + toward the viewer).
RACE_PATH = [    # v3: widths x1.2-1.7 (v2's loop read as a ribbon; theirs is a wide trough)
    (240, 133, 52, -3.0), (160, 147, 56, -2.8), (107, 120, 58, -2.6), (89, 76, 60, -2.4), (116, 36, 62, -2.2),
    (169, 20, 64, -2.0), (222, 31, 66, -1.7), (267, 58, 72, -1.4), (289, 89, 84, -1.1), (289, 133, 100, -0.7),
    (271, 178, 120, -0.2), (231, 218, 136, 0.4), (169, 249, 150, 1.0), (111, 271, 160, 1.5), (49, 302, 166, 2.0),
    (-27, 338, 170, 2.4)]
RACE_OPEN = (0.0, 0.45, 1.0)       # the trough opens toward the camera, a little up-screen (we look down into it)
RACE_BANK = 38.0                   # deg: the floor tilts toward the inside of each bend (shows the outer pink wall)


def _path_samples(n=560):
    from scipy.interpolate import CubicSpline
    P = np.array(RACE_PATH, float)
    d = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]), np.diff(P[:, 1])))]
    cs = CubicSpline(d, P, bc_type="natural")
    t = np.linspace(0, d[-1], n)
    Q = cs(t)
    C = np.stack([(Q[:, 0] - RACE_FRAME[0] / 2) / RACE_SCALE, -(Q[:, 1] - RACE_FRAME[1] / 2) / RACE_SCALE, Q[:, 3]], -1)
    width = Q[:, 2] / RACE_SCALE
    return C, width


def track_frames(n=560):
    C, width = _path_samples(n)
    T = np.gradient(C, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    op = np.asarray(RACE_OPEN, float) / np.linalg.norm(RACE_OPEN)
    L = np.cross(op[None], T)
    L /= np.linalg.norm(L, axis=1, keepdims=True)
    U = np.cross(T, L)
    # bank toward the inside of the bend (curvature direction projected on L)
    dT = np.gradient(T, axis=0)
    side = np.sign(np.sum(dT * L, axis=1))
    k = np.clip(np.linalg.norm(dT, axis=1) / 0.02, 0, 1)
    b = np.radians(RACE_BANK) * side * k
    from scipy.ndimage import gaussian_filter1d
    b = gaussian_filter1d(b, 12)
    L2 = L * np.cos(b)[:, None] + U * np.sin(b)[:, None]
    U2 = np.cross(T, L2)
    return C, T, L2, U2, width


def _track_profile(w=0.78, d=0.52, lip=0.07, n=40):
    """Closed U profile (s lateral, h up, u texture coordinate): inner trough, left lip, outer wall, right lip."""
    pts = []
    th = np.linspace(0.0, _m.pi, n)
    pts += [(w * _m.cos(a), -d * _m.sin(a)) for a in th]                               # inner: right rim -> left rim
    pts += [(-w - lip - lip * _m.cos(a), lip * _m.sin(a)) for a in np.linspace(0, _m.pi, 8)[1:-1]]   # left lip
    W, D = w + 2 * lip, d + 2 * lip
    pts += [(W * _m.cos(a), -D * _m.sin(a)) for a in th[::-1]]                          # outer: left -> right
    pts += [(w + lip - lip * _m.cos(a), lip * _m.sin(a)) for a in np.linspace(0, _m.pi, 8)[1:-1][::-1]]  # right lip
    P = np.array(pts)
    seg = np.r_[0, np.cumsum(np.hypot(*np.diff(np.vstack([P, P[:1]]), axis=0).T))]
    u = seg[:-1] / seg[-1]
    return P, u, n / len(P)            # (profile, u per point, u at the end of the inner trough)


def track_mesh(n_path=560):
    C, T, L2, U2, width = track_frames(n_path)
    P, u, u_in = _track_profile(w=1.0, d=0.62, lip=0.08)
    sc = (width / 2.0)[:, None, None]                       # the profile is authored for an inner width of 2 u
    V = (C[:, None, :] + sc * (P[None, :, 0:1] * L2[:, None, :] + P[None, :, 1:2] * U2[:, None, :])).reshape(-1, 3)
    n_p = len(P)
    ii, jj = np.meshgrid(np.arange(n_path - 1), np.arange(n_p), indexing="ij")
    a = ii * n_p + jj
    b_ = ii * n_p + (jj + 1) % n_p
    c = (ii + 1) * n_p + (jj + 1) % n_p
    d = (ii + 1) * n_p + jj
    F = np.concatenate([np.stack([a, b_, c], -1).reshape(-1, 3), np.stack([a, c, d], -1).reshape(-1, 3)])
    fn = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, F[:, k], fn)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    UV = np.stack([np.tile(u, n_path) * 0.999, np.repeat(np.linspace(0, 0.999, n_path), n_p)], -1)
    return V, F, N, UV, u_in


def _track_texture(u_in):
    purple, pink, lip, outer, outer_hi = (K.hexrgb(h) for h in ("#A968E2", "#F27CC0", "#FFB8DA", "#EF69AC", "#F898CA"))

    def tex(u, v):
        out = np.zeros(u.shape + (3,))
        inner = u < u_in
        q = np.clip(u / u_in, 0, 1)
        e = np.abs(2 * q - 1) ** 1.1                       # 0 at the trough floor, 1 at the rims
        col = purple[None, None] * (1 - e[..., None]) + pink[None, None] * e[..., None]
        streak = 0.06 * (np.sin(v * 140.0 + q * 3.0) > 0.92)
        col = col + streak[..., None]
        out[inner] = col[inner]
        rim = (~inner)
        uo = np.clip((u - u_in) / (1 - u_in), 0, 1)
        lipness = np.clip(1 - np.minimum(uo, 1 - uo) / 0.08, 0, 1)
        oc = outer[None, None] * (1 - lipness[..., None]) + lip[None, None] * lipness[..., None]
        oc = oc + (outer_hi - outer)[None, None] * np.clip(1 - np.abs(uo - 0.2) / 0.2, 0, 1)[..., None] * 0.6
        out[rim] = oc[rim]
        return np.clip(out, 0, 1)
    return tex


def track_parts():
    V, F, N, UV, u_in = track_mesh()
    mat = _Mat("r_track", "#E462A8", roughness=0.30, ior=1.38, clearcoat=0.3, clearcoat_roughness=0.2,
               texture=_track_texture(u_in), texture_size=512)
    p = _FUR.fur_part("track", mat, lambda: (V, F, N, UV))
    p.__dict__["occluder"] = True
    return [p], VOXEL


def sled():
    top = box(0.50, 0.07, 0.72, round=0.07)
    rim = box(0.56, 0.035, 0.78, round=0.05).translate(0, -0.075, 0)
    pad = box(0.40, 0.012, 0.58, round=0.04).translate(0, 0.07, 0)
    return [Part("sled", top, gloss("r_sled", "#39C9F2", rough=0.22, ior=1.45, clearcoat=0.4), voxel=0.006),
            Part("sledglow", rim, _Mat("r_glow", "#8FF4FF", roughness=0.4, emissive="#35D8F5"), voxel=0.006),
            Part("sledpad", pad, gloss("r_pad", "#1FA7E0", rough=0.35), voxel=0.005)], VOXEL


_UPL = ((-0.56, 1.02, 0.02), (-0.92, 1.30, 0.10), (-0.86, 1.72, 0.20), (0.0, 1.0, 0.0), (0.2, 0.0, 1.0), "wave")
_UPR = ((0.56, 1.02, 0.02), (0.92, 1.30, 0.10), (0.86, 1.72, 0.20), (0.0, 1.0, 0.0), (-0.2, 0.0, 1.0), "wave")
RIDERS = {
    # front-left big: navy kepi, arms flung out, laughing
    "A": dict(eyes="open", look=(0.25, 0.25), mouth="laugh", mouth_w=0.40, mouth_h=0.30, hat="navy", hat_tilt=(0, 0, 10),
              brim_yaw=-20, hat_size=0.80, brows=(0.30, 0.1), eye_r=(0.19, 0.25, 0.13), eye_c=(0.20, 1.44), girth=1.06,
              arms=dict(L=((-0.56, 1.00, 0.02), (-0.95, 0.98, 0.16), (-1.28, 0.92, 0.30), (-1.0, 0.25, 0.1), (0.0, 0.2, 1.0), "wave"),
                        R=((0.56, 1.02, 0.02), (0.92, 1.24, 0.10), (1.10, 1.58, 0.22), (0.3, 1.0, 0.0), (-0.1, 0.0, 1.0), "wave")),
              feet=dict(L=((-0.22, 0.30, 0.0), (-0.30, 0.0, 0.14), (-0.3, 0, 1)), R=((0.22, 0.30, 0.0), (0.30, 0.0, 0.10), (0.3, 0, 1))),
              belt=dict(buckle=(0.12, 0.64), pouch=(0.42, 0.62), wrench=(-0.24, 0.80), wrench_scale=1.2), lean=(-6.0, 0.0)),
    # front-right big: green cap + glasses, crouched, hands on the sled's nose
    "B": dict(eyes="open", look=(-0.2, -0.1), mouth="laugh", mouth_w=0.34, mouth_h=0.22, hat="green", hat_tilt=(0, 0, -20),
              brim_yaw=40, hat_size=0.90, glasses=True, brows=(0.25, 0.0), eye_c=(0.25, 1.44),
              arms=dict(L=((-0.56, 1.00, 0.02), (-0.74, 0.62, 0.30), (-0.52, 0.30, 0.62), (0.1, -1.0, 0.4), (0.0, -0.4, 1.0), "open"),
                        R=((0.56, 1.00, 0.02), (0.74, 0.62, 0.30), (0.52, 0.30, 0.62), (-0.1, -1.0, 0.4), (0.0, -0.4, 1.0), "open")),
              feet=dict(L=((-0.24, 0.26, 0.10), (-0.34, 0.0, 0.42), (-0.3, 0, 1)), R=((0.24, 0.26, 0.10), (0.34, 0.0, 0.42), (0.3, 0, 1))),
              belt=dict(buckle=(-0.10, 0.64), pouch=(0.42, 0.60), wrench=None), lean=(0.0, 14.0)),
    # far small: navy cap, both arms up
    "C": dict(eyes="open", look=(0.1, 0.1), mouth="laugh", mouth_w=0.34, mouth_h=0.22, hat="navy", hat_size=0.80,
              brows=(0.3, 0.1), arms=dict(L=_UPL, R=_UPR), feet=W.HOME_L["feet"], lean=(0.0, 0.0)),
    # mid small: navy cap, lying back on the sled, arms up
    "D": dict(eyes="open", look=(-0.1, 0.2), mouth="grin", mouth_w=0.28, hat="navy", hat_size=0.80, brows=(0.2, 0.0),
              arms=dict(L=_UPL, R=_UPR), feet=dict(L=((-0.22, 0.30, 0.0), (-0.28, 0.30, 0.55), (-0.2, 0.4, 1)),
                                                       R=((0.22, 0.30, 0.0), (0.30, 0.34, 0.55), (0.2, 0.4, 1))),
              lean=(0.0, -32.0)),
}
# (rider, screen point of the sled centre (pt), rider scale, rider yaw, sled heading deg about the view axis, depth)
RIDES = [("C", (222, 44), 0.55, -20.0, -25.0, -1.5), ("D", (283, 84), 0.62, -35.0, -60.0, -0.9),
         ("B", (262, 198), 1.40, -12.0, -120.0, 0.35), ("A", (122, 262), 1.45, 14.0, -160.0, 1.6)]
RIDER_TILT = 22.0                  # deg: riders + sleds tipped toward the camera (we see them from above, like theirs)


def _rot(axis, deg):
    return K.rotate_matrix(axis, deg)


def _ride_pose(xy, scale, yaw, heading, depth):
    x = (xy[0] - RACE_FRAME[0] / 2) / RACE_SCALE
    y = -(xy[1] - RACE_FRAME[1] / 2) / RACE_SCALE
    base = np.array([x, y, depth + 0.6])
    Rtilt = _rot((1, 0, 0), RIDER_TILT)
    sled_R = Rtilt @ _rot((0, 1, 0), heading)
    rider_R = Rtilt @ _rot((0, 1, 0), yaw)
    # director r2 (grader B: the riders stood on floating plates): sink each rider into its sled so the shorts and legs
    # are inside it (seated), and the sled a little into the chute
    lift = Rtilt @ np.array([0.0, -0.34 * scale, -0.05 * scale])
    return base.tolist(), sled_R.tolist(), (base + lift).tolist(), rider_R.tolist()


RACE_VIEW = K.view_bounds(RACE_FRAME, scale_pt=RACE_SCALE, center=(0.0, 0.0), zr=(-4.0, 4.5), margin=1.0, fov=10.0)

MODELS["race_track"] = track_parts
MODELS["race_sled"] = sled
for _k, _sp in RIDERS.items():
    MODELS[f"race_rider{_k}"] = (lambda s=_sp: W.worker(s, COLOUR))


def _race_scene():
    sc = [("race_track", dict(center=False, pos=(0.0, 0.0, 0.0)))]
    for k, xy, s_, yaw, heading, depth in RIDES:
        pos_s, R_s, pos_r, R_r = _ride_pose(xy, s_, yaw, heading, depth)
        sc.append(("race_sled", dict(center=False, R=R_s, pos=pos_s, scale=s_ * 1.3)))
        sc.append((f"race_rider{k}", dict(center=False, R=R_r, pos=pos_r, scale=s_)))
    return sc





def paint_room(W=1179, H=870):
    """The Streak Race room behind the slide (meta-045; painted in code, softly defocused like theirs): lavender ceiling
    with beams, pipes + brass collars, two warm lamps, the back wall, a cream machine with an orange-framed screen at
    the left, crates at both sides, a tiled floor in perspective, a checkered banner at the bottom-left."""
    from PIL import Image as _I, ImageDraw as _D, ImageFilter as _F
    S = 2
    w, h = W * S, H * S
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    top, wall, floor0, floor1 = (np.array(K.hexrgb(c)) for c in ("#B7A8EE", "#A6A6EA", "#CDD2F6", "#AEB8EC"))
    hz = 400 * S                                                       # the floor line (their back wall meets the floor)
    t = np.clip(yy / hz, 0, 1)[..., None]
    col = top * (1 - t) + wall * t
    tf = np.clip((yy - hz) / (h - hz), 0, 1)[..., None]
    col = np.where((yy >= hz)[..., None], floor0 * (1 - tf) + floor1 * tf, col)
    img = _I.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).convert("RGBA")
    d = _D.Draw(img)
    vp = (600 * S, 250 * S)
    grout = (150, 156, 214, 255)
    for k in range(-14, 15):                                            # floor tiles: radial lines from the VP
        x_far = vp[0] + k * 90 * S
        x_near = vp[0] + k * 520 * S
        y0 = hz
        xa = vp[0] + (x_far - vp[0]) * (y0 - vp[1]) / (hz - vp[1] + 1)
        d.line([(xa, y0), (x_near, h + 200 * S)], fill=grout, width=2 * S)
    y = hz
    step = 34 * S
    while y < h:
        d.line([(0, y), (w, y)], fill=grout, width=2 * S)
        step *= 1.32
        y += step
    beam, panel = (148, 132, 214, 255), (206, 196, 244, 255)
    for x0 in (60, 420, 800):                                           # ceiling panels + beams
        d.rounded_rectangle([x0 * S, -40 * S, (x0 + 300) * S, 70 * S], radius=18 * S, fill=panel)
    d.rectangle([0, 70 * S, w, 84 * S], fill=beam)
    d.rectangle([0, 230 * S, w, 244 * S], fill=(172, 164, 228, 255))
    pipe, pipe_d, brass = (205, 190, 236, 255), (160, 146, 214, 255), (222, 184, 124, 255)
    d.rounded_rectangle([-20 * S, 92 * S, 260 * S, 140 * S], radius=24 * S, fill=(232, 150, 206, 255))   # pink pipe (left)
    d.rounded_rectangle([130 * S, -10 * S, 190 * S, 250 * S], radius=28 * S, fill=pipe)                   # grey pipe down
    d.rectangle([150 * S, -10 * S, 168 * S, 250 * S], fill=(225, 214, 246, 255))
    for (bx, by, bw, bh) in ((118, 60, 84, 30), (118, 170, 84, 30), (230, 86, 36, 60)):
        d.rounded_rectangle([bx * S, by * S, (bx + bw) * S, (by + bh) * S], radius=10 * S, fill=brass)
    d.rounded_rectangle([900 * S, 20 * S, 1200 * S, 80 * S], radius=30 * S, fill=pipe)                    # right pipes
    d.rounded_rectangle([930 * S, -20 * S, 990 * S, 120 * S], radius=28 * S, fill=pipe_d)
    d.rounded_rectangle([905 * S, 60 * S, 1015 * S, 92 * S], radius=12 * S, fill=brass)
    d.rounded_rectangle([1080 * S, 20 * S, 1110 * S, 80 * S], radius=8 * S, fill=brass)
    for (lx, ly) in ((330, 40), (1130, 118)):                           # warm lamps + glow
        g = np.exp(-(((xx - lx * S) / (120 * S)) ** 2 + ((yy - (ly + 40) * S) / (90 * S)) ** 2))
        glow = _I.fromarray((np.clip(g, 0, 1) * 150).astype(np.uint8))
        img.paste(_I.new("RGBA", img.size, (255, 236, 190, 255)), (0, 0), glow)
        d = _D.Draw(img)
        d.pieslice([(lx - 44) * S, (ly - 10) * S, (lx + 44) * S, (ly + 60) * S], 180, 360, fill=(96, 92, 150, 255))
        d.ellipse([(lx - 26) * S, (ly + 14) * S, (lx + 26) * S, (ly + 38) * S], fill=(255, 238, 170, 255))
    # the back-wall machine seen through the loop (grey-lavender block with a screen)
    d.rounded_rectangle([470 * S, 250 * S, 700 * S, 400 * S], radius=16 * S, fill=(206, 204, 240, 255))
    d.rounded_rectangle([500 * S, 280 * S, 640 * S, 360 * S], radius=10 * S, fill=(150, 146, 214, 255))
    # the cream machine at the left + its orange-framed screen
    d.rounded_rectangle([30 * S, 300 * S, 300 * S, 480 * S], radius=26 * S, fill=(236, 226, 222, 255))
    d.rounded_rectangle([30 * S, 440 * S, 300 * S, 480 * S], radius=14 * S, fill=(196, 186, 206, 255))
    d.rounded_rectangle([40 * S, 290 * S, 290 * S, 318 * S], radius=12 * S, fill=(160, 170, 226, 255))
    d.rounded_rectangle([150 * S, 334 * S, 250 * S, 424 * S], radius=18 * S, fill=(236, 160, 64, 255))
    d.rounded_rectangle([166 * S, 350 * S, 234 * S, 408 * S], radius=10 * S, fill=(110, 100, 196, 255))
    crate, crate_d, crate_hi = (206, 140, 88, 255), (164, 104, 60, 255), (226, 170, 116, 255)
    for (cx, cy, cw, ch) in ((-10, 400, 140, 130), (1050, 560, 150, 150), (1100, 470, 110, 100)):
        d.rounded_rectangle([cx * S, cy * S, (cx + cw) * S, (cy + ch) * S], radius=8 * S, fill=crate)
        d.rectangle([cx * S, cy * S, (cx + cw) * S, (cy + 18) * S], fill=crate_hi)
        d.line([(cx + 10) * S, (cy + 26) * S, (cx + cw - 10) * S, (cy + ch - 10) * S], fill=crate_d, width=6 * S)
    # the checkered banner at the bottom-left, curving with the floor
    for i in range(7):
        for j in range(6):
            x0 = (-20 + i * 42 - j * 14) * S
            y0 = (640 + j * 44 + i * 8) * S
            if (i + j) % 2 == 0:
                d.polygon([(x0, y0), (x0 + 42 * S, y0 + 8 * S), (x0 + 28 * S, y0 + 52 * S), (x0 - 14 * S, y0 + 44 * S)],
                          fill=(40, 36, 58, 255))
            else:
                d.polygon([(x0, y0), (x0 + 42 * S, y0 + 8 * S), (x0 + 28 * S, y0 + 52 * S), (x0 - 14 * S, y0 + 44 * S)],
                          fill=(246, 244, 252, 255))
    img = img.resize((W, H), _I.LANCZOS).filter(_F.GaussianBlur(1.6))
    return img


def _race_post(im):
    """post_fit: the painted room behind the 3D render (the ride keeps its crisp edges; the room is defocused)."""
    room = paint_room(*im.size)
    room.alpha_composite(im)
    return room


ASSETS["char_workerRacers"] = dict(scene=_race_scene(), bounds=RACE_VIEW, frame=RACE_FRAME, fov=10, light=LIGHT,
                                   no_fit=True, post_fit=_race_post)
