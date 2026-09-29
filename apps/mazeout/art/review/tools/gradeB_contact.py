"""Grader B: compact contacts [reference | ours on the ref backdrop | ours in place] at game scale -> art/ui/sheets/gradeB/c_<name>.png
    ~/.venvs/mf3d/bin/python art/review/tools/gradeB_contact.py build/ui-art/review/merged.json '{"boosters": {"ids": ["boosterFreeze"], "k": 1.0}}'"""
import sys, os, json
sys.path.insert(0, "art/tools")
import manifest as MF
MF.use_manifest(sys.argv[1])
import manifest_sheets as MS
import numpy as np
from PIL import Image, ImageDraw
Image.MAX_IMAGE_PIXELS = None
OUT = "art/ui/sheets/gradeB"
m = MF.load(); by = {e["id"]: e for e in m["entries"]}

def tiles(e, pad=6, bgfixed=None):
    ref, _ = MF.ref_crop(e, pad_pt=pad)
    op = MS.ours_path(e)
    r = e["ref"]
    o = Image.open(op).convert("RGBA")
    scale = r.get("scale", 1.0)
    if e.get("exact_px"):
        pass
    og = o.resize((max(1, round(o.width * scale)), max(1, round(o.height * scale))), Image.LANCZOS)
    fw, fh = (e.get("size_pt") or [o.width / 3, o.height / 3])
    ax, ay = e.get("anchor_pt") or [fw / 2, fh / 2]
    bx0, by0, bx1, by1 = MF.ref_box_pt(r)
    rax, ray = r.get("anchor_pt") or [(bx0 + bx1) / 2, (by0 + by1) / 2]
    px = round((rax - (bx0 - pad)) * 3 - ax * 3 * scale)
    py = round((ray - (by0 - pad)) * 3 - ay * 3 * scale)
    a = np.asarray(ref)
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = bgfixed or tuple(int(v) for v in np.median(edge, 0))
    solo = Image.new("RGBA", ref.size, bg + (255,)); solo.paste(og, (px, py), og)
    inp = ref.convert("RGBA"); inp.paste(og, (px, py), og)
    return [ref.convert("RGB"), solo.convert("RGB"), inp.convert("RGB")]

def contact(name, ids, k=1.0, maxw=2600, cols=None, which=(0,1,2)):
    rows = []
    for i in ids:
        e = by[i]
        try:
            t = tiles(e)
        except Exception as ex:
            print("skip", i, ex); continue
        t = [t[j] for j in which]
        if k != 1.0:
            t = [x.resize((max(1,round(x.width*k)), max(1,round(x.height*k))), Image.LANCZOS) for x in t]
        w = sum(x.width for x in t) + 12 * (len(t) - 1)
        h = max(x.height for x in t) + 26
        im = Image.new("RGB", (w, h), (236, 236, 240)); d = ImageDraw.Draw(im)
        d.text((2, 4), f"{i}  {e.get('size_pt')}", fill=(10, 10, 20), font=MS._font(18))
        x = 0
        for tt in t:
            im.paste(tt, (x, 26)); x += tt.width + 12
        rows.append(im)
    # pack rows into lines up to maxw
    lines, cur, cw = [], [], 0
    for r in rows:
        if cur and cw + r.width + 30 > maxw:
            lines.append(cur); cur, cw = [], 0
        cur.append(r); cw += r.width + 30
    if cur: lines.append(cur)
    W = max(sum(r.width + 30 for r in l) for l in lines)
    H = sum(max(r.height for r in l) + 20 for l in lines)
    out = Image.new("RGB", (W, H), (200, 200, 208))
    y = 0
    for l in lines:
        x = 0
        for r in l:
            out.paste(r, (x, y)); x += r.width + 30
        y += max(r.height for r in l) + 20
    p = os.path.join(OUT, f"c_{name}.png"); out.save(p); print(p, out.size)

if __name__ == "__main__":
    spec = json.loads(sys.argv[2])
    for name, cfg in spec.items():
        contact(name, cfg["ids"], k=cfg.get("k", 1.0), maxw=cfg.get("maxw", 2600), which=tuple(cfg.get("which", (0,1,2))))
