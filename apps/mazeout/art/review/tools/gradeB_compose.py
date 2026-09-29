"""Grader B: composed proofs. Home = homeBackdrop + sci rig (torso/head) + homeConsole + sci arms + homePlatform + homeCapsuleMachine
+ pile + LEVEL plate mock + worker rigs (rig.json placement_pt) + mocked top bar / streak badge / Play / nav (our icons, PIL chrome
stand-ins, PCDisplay-Black text). Loading = loadingBackdrop + char_loading_layout.json cast + logoArrowOut at the original logo's
spot (x 21..218, y 65..217 pt on V1 t=0). Outputs art/ui/sheets/gradeB/p_*.png next to 002 / V1 t=0 / store 8.
    cd apps/mazeout; ~/.venvs/mf3d/bin/python art/review/tools/gradeB_compose.py"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
Image.MAX_IMAGE_PIXELS = None
APP = os.getcwd()
OUT = "art/out"; UIO = "art/ui/out"; SH = "art/ui/sheets/gradeB"
S = 3  # px per pt
FONT = "App/Resources/Fonts/PCDisplay-Black.ttf"

def F(pt): return ImageFont.truetype(FONT, round(pt * S))
def img(p): return Image.open(p).convert("RGBA")
def put(cv, im, x_pt, y_pt, w_pt=None, h_pt=None):
    if w_pt:
        im = im.resize((round(w_pt * S), round((h_pt or w_pt * im.height / im.width) * S)), Image.LANCZOS)
    cv.alpha_composite(im, (round(x_pt * S), round(y_pt * S))) if x_pt >= 0 and y_pt >= 0 else cv.paste(im, (round(x_pt*S), round(y_pt*S)), im)

def rig(name, pick):
    d = f"{OUT}/char_{name}_rig"; rj = json.load(open(f"{d}/rig.json"))
    px, py = rj["placement_pt"]["x"], rj["placement_pt"]["y"]
    L = [l for l in rj["layers"] if not l.get("overlay") and (not l.get("group") or l.get("default")) and pick(l["name"])]
    L.sort(key=lambda l: l.get("z", 0))
    return [(img(f"{d}/{l['file']}"), px + l["rect_pt"][0], py + l["rect_pt"][1]) for l in L]

def se_mask(w, h, n=4.5, ss=4):
    W, H = round(w * S * ss), round(h * S * ss)
    y, x = np.mgrid[0:H, 0:W]
    u = np.abs((x + 0.5) / W * 2 - 1); v = np.abs((y + 0.5) / H * 2 - 1)
    m = ((u ** n + v ** n) <= 1).astype(np.uint8) * 255
    return Image.fromarray(m, "L").resize((round(w * S), round(h * S)), Image.LANCZOS)

def se_fill(cv, x, y, w, h, top, bot, n=4.5, outline=None, ow=1.0):
    if outline:
        m = se_mask(w, h, n); lay = Image.new("RGBA", m.size, outline + (255,)); lay.putalpha(m); put(cv, lay, x, y)
        x, y, w, h = x + ow, y + ow, w - 2 * ow, h - 2 * ow
    m = se_mask(w, h, n)
    g = np.linspace(0, 1, m.size[1])[:, None, None]
    arr = (np.array(top)[None, None] * (1 - g) + np.array(bot)[None, None] * g) * np.ones((1, m.size[0], 1))
    lay = Image.fromarray(arr.astype(np.uint8), "RGB").convert("RGBA"); lay.putalpha(m); put(cv, lay, x, y)

def text(cv, s, cx, cy, pt, fill, outline=None, ow=0.0, drop=0.0):
    d = ImageDraw.Draw(cv); f = F(pt)
    kw = dict(font=f, anchor="mm")
    if outline and drop:
        d.text((cx * S, (cy + drop) * S), s, fill=outline, stroke_width=round(ow * S), stroke_fill=outline, **kw)
    d.text((cx * S, cy * S), s, fill=fill, stroke_width=round(ow * S) if outline else 0, stroke_fill=outline, **kw)

def hex2(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def home(ui=True, pile="homeArrowPileFull"):
    cv = Image.new("RGBA", (393 * S, 852 * S), (0, 0, 0, 255))
    put(cv, img(f"{OUT}/homeBackdrop@3x.png"), 0, 0)
    for im, x, y in rig("sci_home", lambda n: not n.startswith("arm")): put(cv, im, x, y)
    put(cv, img(f"{OUT}/homeConsole@3x.png"), 95, 266)
    for im, x, y in rig("sci_home", lambda n: n.startswith("arm")): put(cv, im, x, y)
    put(cv, img(f"{OUT}/homePlatform@3x.png"), 0, 576)
    put(cv, img(f"{OUT}/homeCapsuleMachine@3x.png"), 95, 365)
    put(cv, img(f"{OUT}/{pile}@3x.png"), 104, 402)
    if ui:
        text(cv, "LEVEL", 168.5 + 27.5, 518.8 + 8.8, 14.1, hex2("#FFFFFF"), hex2("#093198"), 0.8, 0.8)
        se_fill(cv, 147.5, 536.8, 98.4, 32.4, hex2("#2BE62A"), hex2("#03B800"), n=3.2, outline=hex2("#066A01"), ow=1.4)
        text(cv, "32", 147.5 + 49.2, 536.8 + 16.5, 30.6, hex2("#FFFFFF"), hex2("#066A01"), 2.1, 0.5)
    for w in ("wk_homeL_blue", "wk_homeR_blue"):
        for im, x, y in rig(w, lambda n: True): put(cv, im, x, y)
    if ui:
        # top bar
        se_fill(cv, 18.7, 36.7, 63.4, 61.4, hex2("#0AA3FF"), hex2("#0060E8"), n=3.6, outline=hex2("#0040C0"), ow=1.2)
        av = img(f"{UIO}/avatarDefault@3x.png"); m = se_mask(51, 49, 3.6); av = av.resize(m.size, Image.LANCZOS); av.putalpha(m); put(cv, av, 24.9, 42.9)
        se_fill(cv, 126.8, 56, 73.7, 27.4, hex2("#EAF4FF"), hex2("#C9DFFF"), n=5, outline=hex2("#5F86C8"), ow=1.0)
        text(cv, "2240", 126.8 + 42, 56 + 13.9, 18.8, hex2("#093896"))
        put(cv, img(f"{UIO}/iconCoin@3x.png"), 95.7, 53, 34, 34)
        put(cv, img(f"{UIO}/iconPlusGreen@3x.png"), 118.8, 73.7, 18.7, 18.7)
        se_fill(cv, 242.2, 56, 76.7, 27.4, hex2("#EAF4FF"), hex2("#C9DFFF"), n=5, outline=hex2("#5F86C8"), ow=1.0)
        text(cv, "Full", 242.2 + 45, 56 + 13.9, 19.1, hex2("#093896"))
        put(cv, img(f"{UIO}/heartLives@3x.png"), 212.5, 53, 39, 36.7)
        text(cv, "5", 226.9 + 10, 61.7 + 10.7, 22.8, hex2("#FFFFFF"), hex2("#870400"), 0.9, 1)
        se_fill(cv, 334.3, 49, 40, 39.7, hex2("#0AA3FF"), hex2("#0070F0"), n=3.5, outline=hex2("#0040C0"), ow=2)
        put(cv, img(f"{UIO}/glyphGear@3x.png"), 334.3 + 7, 49 + 6.8)
        # streak badge (anchor 40,82 of the 80x84 frame on 002's ring bottom centre)
        put(cv, img(f"{UIO}/eventBadgeStreak@3x.png"), 49.0 - 40, 198.9 - 82)
        text(cv, "9h 42m", 49.0, 198.9 - 82 + 68, 11.5, hex2("#FFFFFF"), hex2("#0F2C80"), 1.0, 0.6)
        # play
        se_fill(cv, 82.7, 622.2, 228.2, 103.8, hex2("#00A9FB"), hex2("#0E58C3"), n=4.4, outline=hex2("#0C3B91"), ow=1.2)
        se_fill(cv, 91.1, 628.2, 211.2, 86.7, hex2("#12E61E"), hex2("#00C200"), n=4.7, outline=hex2("#0C3B01"), ow=1.3)
        text(cv, "Play", 91.1 + 105.6, 628.2 + 41, 48.8, hex2("#F1FFF2"), hex2("#066A01"), 2.2, 2.2)
        # nav
        bar = np.zeros((round(81.1 * S), 393 * S, 3))
        g = np.linspace(0, 1, bar.shape[0])[:, None]
        c0, c1 = np.array(hex2("#00A0FF")), np.array(hex2("#134BEF"))
        bar[:] = (c0 * (1 - g) + c1 * g)[:, None, :]
        bar[:round(1 * S)] = hex2("#003BCB")
        bi = Image.fromarray(bar.astype(np.uint8)).convert("RGBA"); put(cv, bi, 0, 771.7)
        se_fill(cv, 126.8, 753.6, 140.1, 99.1, hex2("#25DAFF"), hex2("#0DB8FF"), n=6, outline=hex2("#0050D0"), ow=1.5)
        put(cv, img(f"{UIO}/navShop@3x.png"), 38, 772)
        put(cv, img(f"{UIO}/navHome@3x.png"), 157, 730)   # director r2: 80 x 86 frame
        put(cv, img(f"{UIO}/navTrophy@3x.png"), 288, 772)
        text(cv, "Home", 196.5, 822, 15.1, hex2("#FFFFFF"), hex2("#16388C"), 1.0, 0.6)
    return cv

def loading(logo=True):
    cv = img(f"{OUT}/loadingBackdrop@3x.png").copy()
    lay = json.load(open(f"{OUT}/char_loading_layout.json"))["characters"]
    for name, c in sorted(lay.items(), key=lambda kv: kv[1]["z"]):
        put(cv, img(f"{OUT}/{c['file']}"), c["x"], c["y"])
    if logo:
        lg = img(f"{UIO}/logoArrowOut@3x.png")
        s = 197.0 / (299.33 - 8.67)
        put(cv, lg, 21 - 8.67 * s, 65 - 1.67 * s, 306 * s, 236 * s)
        text(cv, "Loading..", 196.5, 784, 22, hex2("#FFFFFF"), hex2("#2A2A60"), 1.2, 1.0)
    return cv

def pair(ours, ref, dst, k=2, labels=("ours", "reference")):
    ours = ours.convert("RGB").resize((393 * k, 852 * k), Image.LANCZOS)
    ref = ref.convert("RGB").resize((393 * k, 852 * k), Image.LANCZOS)
    out = Image.new("RGB", (393 * k * 2 + 30, 852 * k + 40), (236, 236, 240)); d = ImageDraw.Draw(out)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
    d.text((10, 8), labels[0], fill=(0, 0, 0), font=f); d.text((393 * k + 30, 8), labels[1], fill=(0, 0, 0), font=f)
    out.paste(ours, (0, 40)); out.paste(ref, (393 * k + 30, 40)); out.save(dst); print(dst, out.size)

def crop_pair(ours, ref, box_pt, dst, k=3):
    x0, y0, x1, y1 = box_pt
    a = ours.convert("RGB").crop((round(x0 * S), round(y0 * S), round(x1 * S), round(y1 * S)))
    b = ref.convert("RGB").resize((393 * S, 852 * S), Image.LANCZOS).crop((round(x0 * S), round(y0 * S), round(x1 * S), round(y1 * S)))
    if k != S:
        a = a.resize((round(a.width * k / S), round(a.height * k / S)), Image.LANCZOS); b = b.resize(a.size, Image.LANCZOS)
    out = Image.new("RGB", (a.width * 2 + 20, a.height), (236, 236, 240)); out.paste(a, (0, 0)); out.paste(b, (a.width + 20, 0)); out.save(dst); print(dst, out.size)

if __name__ == "__main__":
    os.makedirs(SH, exist_ok=True)
    r002 = img("research/shots/002-home-L32.png")
    h = home(); h.save(f"{SH}/home_composed.png")
    pair(h, r002, f"{SH}/p_home.png", labels=("ours (scene + rigs + mocked UI)", "002 (looked at only)"))
    h0 = home(ui=False)
    pair(h0, r002, f"{SH}/p_home_noui.png", labels=("ours (art only)", "002"))
    crop_pair(h0, r002, (0, 150, 393, 620), f"{SH}/p_home_mid.png", k=2)
    crop_pair(h, r002, (0, 480, 393, 852), f"{SH}/p_home_low.png", k=2)
    crop_pair(h, r002, (0, 20, 393, 210), f"{SH}/p_home_top.png", k=2)
    for p, ref in (("homeArrowPileHalf", "research/shots/168-home-L055.png"), ("homeArrowPileLow", "research/shots/070-home-L40-skyjump-joined.png")):
        hh = home(pile=p); crop_pair(hh, img(ref), (60, 340, 340, 620), f"{SH}/p_home_{p}.png", k=2)
    rl = img("build/ui-art/refcrops/loadingBackdrop.png")
    lo = loading(); lo.save(f"{SH}/loading_composed.png")
    pair(lo, rl, f"{SH}/p_loading.png", labels=("ours (backdrop + cast + logoArrowOut)", "V1 t=0 (looked at only)"))
    s8 = img("research/store/iphone-8.png")
    pair(lo, s8, f"{SH}/p_loading_s8.png", labels=("ours", "store 8 (looked at only)"))
