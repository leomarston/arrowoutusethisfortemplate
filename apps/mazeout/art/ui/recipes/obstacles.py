"""Board obstacles, 3D route (art spike): the pink TAPE bundle that binds N parallel arrows.

Measured on runner shot 003 (L32, 4-arrow tapes, fit zoom, pitch 53.59 px = 17.88 pt): the tape is 53 x 186 px
(0.99 x 3.47 pitch; length = (N - 1) pitch + 0.47 pitch), a darker pink base band (#D72169 / #E12870) under two
glossy straps (#FF3B84, highlight #FF7DA7 -> #FF93B4 near the ends) that run corner to corner and cross in the
middle (an X ~8 deg off the tape axis), strap gaps shaded #B31E58, and a soft grey drop shadow (#D9D9D9, #989898
under the bottom end). Our model: base slab + two rounded strap slabs; authored in pitch units (1 unit = 1 cell),
lying in XY with +Z toward the viewer, rendered straight down.
"""
import math

from uikit import Part, box, gloss, satin, union  # noqa: F401

VOXEL = 0.006
PINK_BASE = "#D21E66"
PINK_STRAP = "#FF3A83"


def tape(n=4):
    from uikit import extrude, rect2
    L = (n - 1) + 0.47
    W = 0.99
    base = box(0.92 * W / 2, (L - 0.1) / 2, 0.03, round=0.028).translate(0, 0, -0.1)
    sw = 0.49 * W                                         # two straps side by side at each end
    ang = math.degrees(math.atan2(0.5 * W, L - sw))       # end-centre to end-centre, corner to corner
    sl = (L - sw) / math.cos(math.radians(ang)) + sw
    strap2 = rect2(sw / 2, sl / 2, round=0.13)
    th = 0.05                                             # half-thickness; round ~ th -> a soft cross-section
    k = 0.07                                              # the straps arch over the bundle: ends 0.18 lower (the
    #                                                       capture's bright top end and shaded bottom end)

    def arch(sd):
        from sdf import SDF, F
        f = sd.fn

        def fn(p):
            q = p.copy()
            q[:, 2] = q[:, 2] + F(k) * q[:, 1] * q[:, 1]
            return f(q) * F(0.9)
        lo = sd.lo.copy(); lo[2] -= k * float(max(abs(sd.lo[1]), abs(sd.hi[1]))) ** 2
        return SDF(fn, lo, sd.hi)
    a = arch(extrude(strap2, th, round=th * 0.9)).rotate_z(-ang).translate(0, 0, 0.1)
    b = arch(extrude(strap2, th, round=th * 0.9)).rotate_z(ang).translate(0, 0, 0.19)
    return [Part("base", base, satin("tape_base", PINK_BASE, rough=0.42)),
            Part("strap_a", a, gloss("tape_strap_a", PINK_STRAP, rough=0.24, ior=1.45), voxel=0.004),
            Part("strap_b", b, gloss("tape_strap_b", PINK_STRAP, rough=0.24, ior=1.45), voxel=0.004)], VOXEL


def _shadow(im):
    """The capture's soft grey drop shadow: the alpha, blurred, offset 3 px down, 35 % grey under the art."""
    from PIL import Image, ImageFilter
    a = im.getchannel("A")
    sh = Image.new("RGBA", im.size, (40, 40, 48, 0))
    sa = a.filter(ImageFilter.GaussianBlur(2.2)).point(lambda v: int(v * 0.42))
    sh.putalpha(sa)
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 3))
    out.alpha_composite(im)
    return out


MODELS = {f"tape{n}": (lambda n=n: tape(n)) for n in (2, 3, 4, 5, 6)}

# frame: the pink body lands exactly on the measured 53 x 186 px inside a 60 x 195 px (20 x 65 pt) frame
ASSETS = {
    "tapeV4_3d": dict(model="tape4", yaw=0, pitch=0, frame=(20, 65), fill=(53 / 60, 186 / 195), align=(0.5, 0.4),
                      fov=8, post_fit=_shadow, dest="route3d"),
    "tapeH4_3d": dict(model="tape4", yaw=0, pitch=0, roll=90, frame=(65, 20), fill=(186 / 195, 53 / 60), align=(0.5, 0.4),
                      fov=8, post_fit=_shadow, dest="route3d"),
}
