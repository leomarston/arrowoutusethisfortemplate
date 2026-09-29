"""Grader B: manifest_sheets side-by-sides for every family-3d entry of a merged manifest -> art/ui/sheets/gradeB/m_<id>.png
    ~/.venvs/mf3d/bin/python art/review/tools/gradeB_sheets.py build/ui-art/review/merged.json"""
import sys, os, json
sys.path.insert(0, "art/tools")
import manifest as MF
MF.use_manifest(sys.argv[1])
import manifest_sheets as MS
dest = "art/ui/sheets/gradeB"
os.makedirs(dest, exist_ok=True)
m = MF.load()
for e in m["entries"]:
    if e["family"] != "3d": continue
    try:
        p = MS.sheet(e, dest=dest)
    except Exception as ex:
        p = f"ERR {ex!r}"
    print(e["id"], "->", p, "| ref:", json.dumps(e.get("ref"))[:160])
