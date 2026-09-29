# Verifier progress (video levels 1-38)

- Random re-extraction picks (seed 1790312444, one per range 1-10 / 11-20 / 21-31): **L1, L11, L29**; bonus from 2-10 (L1 has only 3
  arrows): **L3**. Picked before opening any of their JSON files.
- [ ] 1 V1 vs V2 L11-20 diff (own code)
- [ ] 2 V2 L32-38 vs phone + full cross-match video L1-38 x phone L32-61
- [x] 3 independent re-extraction L1, L3, L11, L29 -> diff vs batch: ALL IDENTICAL (L1 3/3, L3 8/8, L11 14/14 + 2 boxes 8/13 from V1 AND V2,
  L29 68/68 incl. batch C's hand-added arrow 67 + 3 pipes with batch C's fixed mouths). Files indep/*.json, indep/diff-*.json.
- [ ] 3b extend myread (ties, mixed obstacles, elevators) and run it on every start frame of L1-38 (third reader)
- [ ] 4 validate L001-L031 (schema, own solver, replay reports, overlays looked at)
- [ ] 5 completeness + consolidated research/video-levels.md
- [x] 3b third reader (myread2.py auto: ties, V1 purple / V2 cyan boxes, pipes with badge gap, elevator platforms) over all 48 start
  frames + 5 reveal frames (runall.py -> thirdreader.json): see numbers in video-levels.md §Verifier.
- [x] 1 V1 vs V2 L11-20 (lvldiff on levels/video/V1-* vs V2-*): 316/316 arrows, 12/12 boxes + counters, 5/5 ties; V2 file == final file.
- [x] 2 cross-match (xmatch.py): 4 video boards are in v552 (L12=L051, L14=L052, L21=L035, L26=L045, all arrows + obstacle cells, shift 0);
  every other video board <= 5 identical arrows vs any phone L32-61 under 8 symmetries; video L32-38 match nothing.
- [x] 4 validate.py (own schema/invariants/solver): 38/38 files 0 errors, all solvable, 0/100 random dead ends; negative controls caught.
  replay re-run (vextract) on all 48 level/video pairs: 0 inconsistent. Overlays of L001-L031 rendered + LOOKED at (final/sheet-*.png).
- [x] 5 research/video-levels.md written (verdicts, 38-row table, gaps, unlocks/captions, difficulty curve, file list). Batch files kept.
DONE 2026-09-25 (verifier). Nothing committed.
