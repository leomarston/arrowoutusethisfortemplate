# T8 LV-TOOLS — staged files for B0 (Wave 0 fence: not installed)

PLAN-P T8 (item 12). These four tools live in fenced paths (`tools/levels/**` existing files, `Packages/**`), so T8 could not
edit them in place. Each file here is the complete re-pointed version; `patches/` holds the same change as a unified diff.
They were proven on scratch trees by `../t8_prove.py` (evidence: `build/p/T8/evidence/`).

| staged file | base sha256 (the file T8 changed) | what changed |
|---|---|---|
| `tools/levels/render.py` | `507384d8d91085bc…` | bundled boards joined to design/levels.json (`level_order.with_provenance`); research files by research slot; the stale slot map `SUBST` emptied; reveals file by research slot |
| `tools/levels/replay_bundle.py` | `386f9b8f5cfa3e2e…` | `plays()` takes the board: V2 board from its provenance, video number = research slot; stale `SUBST` removed |
| `Packages/PathCore/Tests/tools/c4b_bot_replay.py` | `203bc254d98850c7…` | the six LOG levels (v552 69/73/76/79/80/82) found by provenance, replayed under the log's number, `slot` written per row |
| `Packages/PathCore/Tests/tools/c4_reference.py` | `d785e2859c2f5412…` | `negatives`: the 20 targets resolved by research slot; `levels` = the slots they ship at (not in PLAN-P's list of 6: it keeps its own copy of the 20 mutations) |

Full base shas: `build/p/T8/evidence/tool-shas.json` (`originals`). Install:

```
for f in tools/levels/render.py tools/levels/replay_bundle.py \
         Packages/PathCore/Tests/tools/c4b_bot_replay.py Packages/PathCore/Tests/tools/c4_reference.py; do
  shasum -a 256 "$f"          # must equal tool-shas.json "originals"; if not, apply patches/<f>.diff by hand instead
  cp "design/publish/tools/level_reorder/staged/$f" "$f"
done
```

All four import `design/tools/level_order.py` (already in place). With the provenance-stripped bundle, `render.py` and
`replay_bundle.py` MUST be the staged versions (the originals read `capture` from the bundle). `overlay_recast.py` (in place)
works with either `render.py`; its `--reveals` path needs the staged one after the re-order.

B0's order of steps (each proven on scratch except the Swift ones):

1. install the four files above;
2. `python3 design/tools/reorder_levels.py plan` (or copy `build/p/T8/evidence/level-order.json`, sha256 `2eba197b…`) and
   `python3 design/tools/reorder_levels.py apply` -> design/levels.json sha256 `8ace3d3a…`; `… check` -> H1-H10 hold;
3. `python3 design/tools/pin_fixtures.py`, `python3 Packages/PathCore/Tests/tools/c4_reference.py negatives`,
   `python3 Packages/PathCore/Tests/tools/c4b_bot_replay.py`;
4. `tools/levels/lv.sh bundle design/levels.json App/Resources/Levels` (Swift), then
   `python3 design/tools/strip_provenance.py check-bundle design/levels.json App/Resources/Levels` (must be 0 differ: the
   Python mirror = lvtool) -> `strip-levels App/Resources/Levels` -> `check-bundle … --publish` (0 differ);
5. the Swift / test / project changes listed in design/publish/level-reorder.md §14.4 (not doable in Wave 0).
