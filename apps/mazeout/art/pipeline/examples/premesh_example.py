"""Format example + self-test for PREMESHED parts (ui3d.mesh_parts, characters lane request 4) and the rig colour BAKE
(rig.py `bake=True`, request 5). Not shipped art: a gloss ball with a tuft of strand cards on top.

    PY=~/.venvs/mf3d/bin/python
    $PY art/ui/tools/ui3d.py --recipes art/pipeline/examples premeshExample --draft   # -> build/ui-art/draft/
    $PY art/ui/tools/rig.py --recipes art/pipeline/examples premeshExample            # -> build/ui-art/rigs/ (scratch)

A premeshed Part has no SDF (sdf=None) and carries `premesh() -> (v, f, n, uv)` as an INSTANCE attribute (mesher.Part is
Match Factory's verbatim dataclass, so there is no field for it): ui3d takes the arrays as they are (no marching cubes,
no decimation, no reprojection; uv may be None). This is how char_fur.fur_part carries the scientist's strand cards.
The rig below puts the ball and the tuft on separate layers; the tuft's shadow on the ball only exists in the full
render, so the unbaked composite misses it and `bake=True` copies it into the ball layer where the ball is top-most.
"""
import numpy as np

from uikit import Part, gloss, satin, sphere

VOXEL = 0.01
R = 0.5


def tuft_mesh(n=160, segs=4, length=0.34, width=0.035, seed=3):
    """n tapered strand ribbons rooted on the ball's upper cap, combed toward +x, facing +Z (the camera), both windings.
    -> (v, f, n, uv=None)."""
    rng = np.random.default_rng(seed)
    th = rng.uniform(0, 0.55, n)                # polar angle from +Y
    ph = rng.uniform(0, 2 * np.pi, n)
    N = np.stack([np.sin(th) * np.cos(ph), np.cos(th), np.sin(th) * np.sin(ph)], 1)
    root = N * (R - 0.01)                       # roots slightly buried
    comb = np.array([0.55, 0.0, 0.0])
    V, F, NN = [], [], []
    for i in range(n):
        d = N[i] + comb * rng.uniform(0.6, 1.2)
        d /= np.linalg.norm(d)
        side = np.cross(d, [0.0, 0.0, 1.0])
        side /= max(np.linalg.norm(side), 1e-6)
        L = length * rng.uniform(0.7, 1.1)
        base = len(V)
        for k in range(segs + 1):
            t = k / segs
            p = root[i] + d * L * t + np.array([0.0, -0.10, 0.0]) * L * t * t   # a little gravity toward the tip
            w = width * (1 - 0.85 * t)
            V += [p - side * w, p + side * w]
            NN += [N[i], N[i]]
        for k in range(segs):
            a, b, c, e = base + 2 * k, base + 2 * k + 1, base + 2 * k + 2, base + 2 * k + 3
            F += [(a, b, c), (b, e, c), (a, c, b), (b, c, e)]   # both windings: visible from either side
    return np.asarray(V, float), np.asarray(F, np.int64), np.asarray(NN, float), None


def premeshed_part(name, material, build):
    p = Part(name, None, material, occluder=False, collide=False)
    p.__dict__["premesh"] = build
    return p


def ball(tuft=True):
    parts = [Part("ball", sphere(R), gloss("pm_ball", "#3E8DF2", rough=0.32), voxel=VOXEL)]
    if tuft:
        parts.append(premeshed_part("tuft", satin("pm_tuft", "#F2548E", rough=0.6), tuft_mesh))
    return parts, VOXEL


MODELS = {"premesh_ball": ball}
ASSETS = {"premeshExample": dict(model="premesh_ball", yaw=0, pitch=8, frame=(60, 60), dest="route3d"),
          # exact_px self-test (art_batch: a non-@3x, opaque full-bleed raster like the app icon -> RGB, exact size)
          "iconExample": dict(model="premesh_ball", yaw=0, pitch=8, frame=(100 / 3, 100 / 3), no_fit=True,
                              bounds=((-0.75, -0.75, -0.6), (0.75, 0.75, 0.6)), margin=1.0, background=(0.93, 0.95, 1.0, 1.0),
                              dest="route3d")}
RIGS = {"premeshExample": dict(
    dir="rig_premesh_example", scratch=True, bake=True,     # a self-test: output under build/ui-art/rigs/, never art/out
    auto=dict(factory=ball, pose=dict(yaw=0, pitch=8), frame=(60, 60), margin=1.08, fov=18,
              layers=[dict(name="ball", parts={"ball"}),
                      dict(name="tuft", parts={"tuft"}, parent="ball", pivots={"root": [0.0, R, 0.0]})]))}
