"""Format example + self-test for art/ui/tools/rig.py's AUTO mode (not a shipped character; the characters lane owns
the real rigs in art/pipeline/items/char_*.py).

    ~/.venvs/mf3d/bin/python art/ui/tools/rig.py --recipes art/pipeline/examples workerExample [--draft]

It rigs the art-spike worker (art/ui/recipes/worker.py, imported read-only): torso (everything else), the raised
right arm, and an EYES swap group (open = the modelled eyes; closed = lids made here) -- the same mechanism serves
eyes open/half/closed and mouth shapes. Pivots: the right shoulder and the eyes' centre.
"""
import numpy as np

from uikit import Part, ellipsoid, union, gloss  # noqa: F401
import worker as W

VOXEL = W.VOXEL
EYE_PARTS = {"eyes", "irises", "pupils", "glints"}


def _factory(eyes="open"):
    parts, vx = W.worker("wave", split_arm="R")
    if eyes == "closed":   # lids: body-coloured shells over each eye (a blink frame)
        lids = union(*[ellipsoid(0.168, 0.198, 0.128).translate(sx * 0.19, 1.30, 0.405) for sx in (-1, 1)])
        parts = [p for p in parts if p.name not in EYE_PARTS] + [Part("lids", lids, gloss("w_body", W.BODY, rough=0.40, ior=1.28),
                                                                       voxel=0.004)]
    return parts, vx


ASSETS = {}
MODELS = {}
RIGS = {"workerExample": dict(
    dir="rig_worker_example", scratch=True,          # a self-test: output under build/ui-art/rigs/, never art/out
    auto=dict(factory=_factory, pose=dict(yaw=-16, pitch=6), frame=(112, 120), margin=1.06, fov=18, light=W.WORKER_LIGHT,
              layers=[
                  dict(name="torso", parts=lambda p: p.name not in EYE_PARTS | {"armR", "lids"}),
                  dict(name="eyesOpen", parts=EYE_PARTS, group="eyes", default=True, parent="torso",
                       pivots={"eyes": [0.0, 1.30, 0.45]}),
                  dict(name="eyesClosed", parts={"lids"}, kw=dict(eyes="closed"), group="eyes", parent="torso",
                       pivots={"eyes": [0.0, 1.30, 0.45]}),
                  dict(name="armR", parts={"armR"}, parent="torso", pivots={"shoulderR": [0.50, 0.98, 0.05]}),
              ])),
}
