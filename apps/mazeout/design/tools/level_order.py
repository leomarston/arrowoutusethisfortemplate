#!/usr/bin/env python3
"""level_order.py — board identity after the level re-order (PUBLISH item 12; SPEC.md rulings 37e + 39 OD8;
design/publish/level-reorder.md §5, §9). Imported by reorder_levels.py and by every tool that used to look a board up by its
level NUMBER (validator_selftest.py, overlay_recast.py, levels_report.py, tools/levels/render.py + replay_bundle.py,
Packages/PathCore/Tests/tools/c4b_bot_replay.py + c4_reference.py).

After the re-order a level number names a SLOT, not a board. A board is named by its RESEARCH SLOT (`rslot`): its number in
the research order, i.e. design/levels.json as `build_levels.py assemble` lays it out before the re-order:
  phone board (source "recorded")      v552's own level number, from its capture (research/shots/NNN-L0nn-..., bot/tmp/L0nn-...)
  video board L1-L31 (source "video")  the video's level number, from its capture (research/video-frames/V1|V2/L0nn-start.png)
  V2 substitute / spare                the phone slot it substitutes ("... the phone's L35 (...)" in `_from`)
  designed stand-in                    the phone slot it stands in for ("... the phone's L81 (...)" in `_from`)
  generated board (L106-L150)          none: it never moves (the re-order zone ends at L105), so its level number
The rslot comes from the board's own provenance (capture / _from), never from its position, so it survives any permutation.
design/levels.json keeps that provenance; the SHIPPED bundle does not (strip_provenance.py), so a tool reading the bundle joins
each bundled board to its design/levels.json record first (`with_provenance`), which also proves the two agree.

  python3 design/tools/level_order.py [design/levels.json]     prints slot -> board, marks moved boards, and the plan state
"""
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))
LEVELS_JSON = os.path.join(APP, 'design', 'levels.json')
PLAN_JSON = os.path.join(APP, 'design', 'level-order.json')
RESEARCH_LEVELS = os.path.join(APP, 'research', 'levels')
RECORDED_END = 105                  # = build_levels.RECORDED_END: nothing past it has a research slot (and nothing past it moves)

_CAP_PHONE = re.compile(r'[/-]L0*(\d+)-')                 # research/shots/003-L32-start.png, research/bot/tmp/L063-1129..
_CAP_VIDEO = re.compile(r'/(V[12])/L0*(\d+)-')            # research/video-frames/V2/L032-start.png
_PHONE_SLOT = re.compile(r"the phone's L0*(\d+)\b")        # _from of a V2 substitute / spare / designed stand-in
_V2_FROM = re.compile(r'^(V2)-L0*(\d+)\b')


class ProvenanceError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------------------- one board
def rslot(l):
    """The board's research slot (see the module doc), or None for a generated board without provenance."""
    src, cap, frm = l.get('source'), l.get('capture') or '', l.get('_from') or ''
    if frm.startswith('V2-L') or frm.startswith('designed stand-in'):
        m = _PHONE_SLOT.search(frm)
        if not m:
            raise ProvenanceError('L%s: _from names no phone slot: %r' % (l.get('level'), frm[:120]))
        return int(m.group(1))
    if src == 'recorded':
        m = _CAP_PHONE.search(cap)
        if not m:
            raise ProvenanceError('L%s: recorded board without a v552 number in its capture %r' % (l.get('level'), cap))
        return int(m.group(1))
    if src == 'video':
        m = _CAP_VIDEO.search(cap)
        if not m:
            raise ProvenanceError('L%s: video board without a video level in its capture %r' % (l.get('level'), cap))
        return int(m.group(2))
    if frm:
        raise ProvenanceError('L%s: unknown _from form %r' % (l.get('level'), frm[:120]))
    return None


def video_board(l):
    """('V1'|'V2', n): the video board this level was read from (None for a phone / designed board)."""
    if l.get('source') != 'video':
        return None
    m = _V2_FROM.match(l.get('_from') or '')
    if m:
        return (m.group(1), int(m.group(2)))
    m = _CAP_VIDEO.search(l.get('capture') or '')
    return (m.group(1), int(m.group(2))) if m else None


def is_substitute(l):
    """A V2 board shipped in a phone slot (ORCH 19 substitutes, ORCH 26 spares)."""
    return l.get('source') == 'video' and (l.get('_from') or '').startswith('V2-L')


def research_json(l):
    """The research reading of the board: research/levels/Lnnn.json (phone, video L1-L31) or research/levels/video/V2-Lnnn.json
    (a V2 substitute / spare). None for a designed board."""
    if is_substitute(l):
        v, n = video_board(l)
        return os.path.join(RESEARCH_LEVELS, 'video', '%s-L%03d.json' % (v, n))
    if l.get('source') in ('recorded', 'video'):
        return os.path.join(RESEARCH_LEVELS, 'L%03d.json' % rslot(l))
    return None


def label(l):
    """Human name of the board: 'v552 L54', 'video L21', 'V2-L033', 'stand-in for phone L81', 'designed L120'."""
    r = rslot(l)
    if is_substitute(l):
        return '%s-L%03d' % video_board(l)
    if l.get('source') == 'recorded':
        return 'v552 L%d' % r
    if l.get('source') == 'video':
        return 'video L%d' % r
    if r is not None:
        return 'stand-in for phone L%d' % r
    return 'designed L%d' % l['level']


def ships_at(l):
    """'' when the board sits at its research slot, else ' (ships at Lk)'. Keeps un-re-ordered output byte-identical."""
    r = rslot(l)
    return '' if r is None or r == l['level'] else ' (ships at L%d)' % l['level']


# ---------------------------------------------------------------------------------------------------------- a level list
def slot_map(levels):
    """{rslot: slot} for every board (generated boards map to themselves). Asserts a bijection and that no board without
    provenance sits inside the research range (it could have been moved there, and then nothing would name it)."""
    out = {}
    for l in levels:
        r = rslot(l)
        if r is None:
            if l['level'] <= RECORDED_END:
                raise ProvenanceError('L%d: a board without provenance inside L1-L%d' % (l['level'], RECORDED_END))
            r = l['level']
        if r in out:
            raise ProvenanceError('research slot %d named twice (L%d and L%d)' % (r, out[r], l['level']))
        out[r] = l['level']
    if sorted(out) != sorted(out.values()):
        raise ProvenanceError('research slots %s are not a permutation of the levels' % sorted(set(out) ^ set(out.values())))
    return out


def order_of(levels):
    """{slot: rslot}: the permutation this list is in (identity for the research order)."""
    return {s: r for r, s in slot_map(levels).items()}


def resolver(doc):
    """lv(d, n) = the level object holding research board n in d (a copy of doc with the same order), and slot(n)."""
    sm = slot_map(doc['levels'])

    def slot(n):
        return sm[n]

    def lv(d, n):
        l = d['levels'][sm[n] - 1]
        assert l['level'] == sm[n], 'levels are not in slot order'
        return l
    return lv, slot


# ---------------------------------------------------------------------------------------------------------- the bundle
def norm_level(l):
    """The bundle schema's elisions (tools/levels/bundle_check.py): null keys, arrow layer 1, empty obstacle lists."""
    out = {}
    for k, v in l.items():
        if v is None:
            continue
        if k == 'arrows':
            v = [{ak: av for ak, av in a.items() if av is not None and not (ak == 'layer' and av == 1)} for a in v]
        elif k == 'obstacles':
            v = [{ok: ov for ok, ov in o.items() if ov is not None and not (ok in ('arrows', 'ends', 'reveals') and ov == [])}
                 for o in v]
        out[k] = v
    return out


# FIX-2 B (N-01): `source` left the list — the publish form no longer ships it (provenance, restored below like `capture`)
GAMEPLAY = ('arrows', 'obstacles', 'cols', 'rows', 'mask', 'timer_s', 'hearts', 'tag', 'unlock', 'seed')
_design_cache = {}


def design_levels(path=None):
    path = path or LEVELS_JSON
    st = os.stat(path)
    key = (path, st.st_mtime_ns, st.st_size)
    if key not in _design_cache:
        _design_cache.clear()
        _design_cache[key] = {l['level']: l for l in json.load(open(path))['levels']}
    return _design_cache[key]


def with_provenance(b, path=None):
    """A bundled board (provenance stripped or not) with its design/levels.json provenance restored: `capture`, `_from`,
    `source`, `metrics` (FIX-2 B, N-01: the publish form strips those two as well) and `_rslot`. Raises when the bundle and
    design/levels.json disagree on the board's gameplay (a stale bundle or design)."""
    d = design_levels(path).get(b['level'])
    if d is None:
        raise ProvenanceError('L%d is in the bundle but not in design/levels.json' % b['level'])
    nb, nd = norm_level(b), norm_level(d)
    bad = [k for k in GAMEPLAY if nb.get(k) != nd.get(k)]
    if bad:
        raise ProvenanceError('L%d: the bundle and design/levels.json disagree on %s: re-bundle (lv.sh bundle) or re-pin'
                              % (b['level'], ', '.join(bad)))
    out = dict(b)
    for k in ('capture', '_from', 'source', 'metrics'):
        if d.get(k) is not None:
            out[k] = d[k]
    out['_rslot'] = rslot(d) if rslot(d) is not None else d['level']
    return out


# ---------------------------------------------------------------------------------------------------------- the plan
def file_sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def load_plan(path=None):
    path = path or PLAN_JSON
    return json.load(open(path)) if os.path.exists(path) else None


def plan_state(levels_path=None, plan_path=None):
    """('none' | 'research' | 'applied' | 'stale', plan): what the levels file is relative to the plan."""
    plan = load_plan(plan_path)
    if plan is None:
        return 'none', None
    sha = file_sha(levels_path or LEVELS_JSON)
    if sha == plan['input']['sha256']:
        return 'research', plan
    if sha == plan['output']['sha256']:
        return 'applied', plan
    return 'stale', plan


def main(argv):
    path = argv[0] if argv else LEVELS_JSON
    levels = json.load(open(path))['levels']
    sm = slot_map(levels)
    moved = 0
    for l in levels:
        r = rslot(l)
        mv = r is not None and r != l['level']
        moved += mv
        if l['level'] <= RECORDED_END + 1 or mv:
            print('L%-3d %-28s%s' % (l['level'], label(l), '  <- research L%d' % r if mv else ''))
    state, plan = plan_state(path)
    print('%d levels, %d boards away from their research slot; bijection ok (%d slots); plan %s: %s' % (
        len(levels), moved, len(sm), os.path.relpath(PLAN_JSON, APP), state))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
