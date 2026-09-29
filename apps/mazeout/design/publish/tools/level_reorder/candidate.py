"""level_reorder/candidate.py — writes the candidate levels.json (today's boards in the candidate order; nothing but `level`
changes) to a path you give, so the EXISTING tools can check it without touching design/:
  python3 design/publish/tools/level_reorder/candidate.py /tmp/x/candidate_levels.json
  python3 design/tools/validate_levels.py /tmp/x/candidate_levels.json   (NOTE: it overwrites design/tools/work/validate_report.json)
  python3 design/tools/repeats.py /tmp/x/candidate_levels.json
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(APP, 'design', 'tools'))
import build_levels as BL  # noqa: E402

out = sys.argv[1]
doc = json.load(open(os.path.join(APP, 'design', 'levels.json')))
order = {int(s): o for s, o in json.load(open(sys.argv[2] if len(sys.argv) > 2 else
                                             os.path.join(HERE, 'level_order_candidate.json')))['order'].items()}
old = {l['level']: l for l in doc['levels']}
new = []
for s in range(1, len(old) + 1):
    l = copy.deepcopy(old[order[s]])
    l['level'] = s
    new.append(l)
assert BL.feature_first_levels(new) == BL.feature_first_levels(doc['levels']), 'a teaching level moved'
doc['levels'] = new
BL.write_doc(doc, out)
print('wrote', out)
