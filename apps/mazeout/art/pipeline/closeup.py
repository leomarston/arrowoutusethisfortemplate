"""Studio close-ups of one item (side / back / 3-4 / top) on a neutral backdrop, for shape review."""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import preview as P  # noqa: E402


def closeup(name, views=((0, 0), (-90, 0), (-35, 25), (0, 89))):
    meta = json.load(open(os.path.join(P.OUT, f"{name}.json")))
    c = -np.array(meta["bbox_center"])
    rs = []
    for i, (yaw, pitch) in enumerate(views):
        s = P.base_scene(os.path.join(P.PREV, f"_close_{name}{i}.png"), 500, 500,
                         dict(type="persp", position=[0, 0, 6], target=[0, 0, 0], up=[0, 1, 0], fov=12, near=0.1, far=20),
                         floor=False, background=[0.36, 0.43, 0.53, 1])
        s["ibl"]["exponent"] = P.RIG_CFG["ibl_exponent"] + 0.8
        s["lights"][0]["direction"] = [0.35, -0.6, -0.7]
        s["items"] = [dict(usdz=os.path.join(P.OUT, f"{name}.usdz"), matrix=P.upright_matrix(yaw, pitch, tuple(c)))]
        rs.append(s)
    P.run_job(rs, f"close_{name}")
    ims = [Image.open(s["out"]) for s in rs if os.path.exists(s["out"])]
    sh = Image.new("RGB", (500 * len(ims), 500))
    for i, im in enumerate(ims):
        sh.paste(im, (500 * i, 0))
    out = os.path.join(P.PREV, f"{name}_closeup.png")
    sh.save(out)
    for s in rs:
        if os.path.exists(s["out"]):
            os.remove(s["out"])
    print(out)


if __name__ == "__main__":
    P.make_rig_assets()
    for n in sys.argv[1:]:
        closeup(n)
