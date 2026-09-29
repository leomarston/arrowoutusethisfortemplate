"""Grader B: merge MANIFEST.json + every lane scratch manifest (characters, 3d-hud, 3d-events, scene) into ONE copy.
    cd apps/mazeout; ~/.venvs/mf3d/bin/python art/review/tools/gradeB_merge.py build/ui-art/review/merged.json
Nothing in art/ is written (MANIFEST.json untouched)."""
import sys, json
sys.path.insert(0, "art/tools")
import manifest as MF
m = MF.load()
lanes = ["art/lanes/characters.entries.json", "art/lanes/3d-hud.entries.json", "art/lanes/3d-events.entries.json",
         "build/ui-art/scene/scene_manifest.json"]
for lp in lanes:
    lane = MF.load(lp)
    d = MF.merge_diff(m, lane)
    print(lp, len(d), "diffs", sum(1 for x in d if x[1]=="new"), "new")
    MF.merge_apply(m, d, validate=False)
import os
os.makedirs(os.path.dirname(os.path.abspath(sys.argv[1])), exist_ok=True)
MF.save(m, sys.argv[1])
es = [e for e in m["entries"] if e["family"] == "3d"]
print(len(es), "3d entries")
for e in es:
    print(f'{e["id"]:22s} {e.get("route"):3s} {e.get("group",""):22s} {str(e.get("size_pt")):12s} {e.get("status"):6s} {e.get("owner"):11s} {e.get("file")}  conf={e.get("confirmed",True)}')
