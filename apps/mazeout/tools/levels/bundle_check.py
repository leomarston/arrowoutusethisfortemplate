#!/usr/bin/env python3
"""bundle_check.py — an independent (Python) proof that App/Resources/Levels carries design/levels.json without loss
(CONTENT, L1; the Swift side is `lvtool bundle --check`, which proves the folder is its byte-for-byte output).

  python3 tools/levels/bundle_check.py [design/levels.json] [App/Resources/Levels] [--publish] [--report FILE]

--publish (PUBLISH B0; SPEC.md ruling 39 OD8): the folder is the SHIPPED form (lvtool bundle --publish), which carries
no provenance: the source's `capture`, "_" notes, `source` and `metrics` (FIX-2 B, N-01) are left out of the comparison,
and a bundle file that still holds any of them is a difference. App/Resources/Levels is always the publish form since B0.

For every level the bundle file and the source object must hold the same values once the bundle schema's elisions are
applied (LevelJSON.swift encodes: null keys omitted; arrow `layer` 1 omitted; empty obstacle `arrows` / `ends` / `reveals`
omitted). Numbers compare as parsed (Python ints are exact, so 64-bit seeds are checked digit for digit). sessions.json,
unlocks.json and tutorials.json must equal the source sections. Nothing else may be in the folder but curve.json (L2) and
.gitkeep. Exit 1 on any difference.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.abspath(os.path.join(HERE, '..', '..'))


def norm_level(l):
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


def diff(a, b, path=''):
    if type(a) != type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return ['%s: %r vs %r' % (path, a, b)]
    if isinstance(a, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append('%s.%s only in %s' % (path, k, 'source' if k in a else 'bundle'))
            else:
                out += diff(a[k], b[k], path + '.' + k)
        return out
    if isinstance(a, list):
        if len(a) != len(b):
            return ['%s: %d vs %d items' % (path, len(a), len(b))]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, '%s[%d]' % (path, i))
        return out
    return [] if a == b else ['%s: %r vs %r' % (path, a, b)]


def main(argv):
    rp = argv[argv.index('--report') + 1] if '--report' in argv else None
    publish = '--publish' in argv
    pos = [a for a in argv if not a.startswith('--') and a != rp]
    src = pos[0] if len(pos) > 0 else os.path.join(APP, 'design', 'levels.json')
    out = pos[1] if len(pos) > 1 else os.path.join(APP, 'App', 'Resources', 'Levels')
    doc = json.load(open(src))
    errs, n = [], 0
    produced = {'sessions.json', 'unlocks.json', 'tutorials.json'}
    for l in doc['levels']:
        name = 'level_%04d.json' % l['level']
        produced.add(name)
        p = os.path.join(out, name)
        if not os.path.exists(p):
            errs.append('%s missing' % name)
            continue
        raw = open(p, encoding='utf-8').read()
        if not raw.endswith('}\n') or raw.count('\n') != 1:
            errs.append('%s: not one compact line with a trailing newline' % name)
        b = json.loads(raw)
        want = l
        if publish:
            strip = ('capture', 'source', 'metrics')                                  # FIX-2 B (N-01): + source, metrics
            want = {k: v for k, v in l.items() if k not in strip and not k.startswith('_')}
            left = sorted(k for k in b if k in strip or k.startswith('_'))
            if left:
                errs.append('%s: provenance keys %s in the publish form' % (name, left))
        d = diff(norm_level(want), norm_level(b), 'L%d' % l['level'])
        errs += d
        n += 1
    for name, key in (('sessions.json', 'sessions'), ('unlocks.json', 'unlocks'), ('tutorials.json', 'tutorials')):
        p = os.path.join(out, name)
        if not os.path.exists(p):
            errs.append('%s missing' % name)
            continue
        b = json.load(open(p))
        if b.get('schema') != 1:
            errs.append('%s: schema %r' % (name, b.get('schema')))
        errs += diff(doc[key], b.get(key), name)
    extra = sorted(f for f in os.listdir(out) if f not in produced and f not in ('curve.json', '.gitkeep'))
    errs += ['extra file %s' % f for f in extra]
    rep = dict(source=os.path.relpath(src, APP), folder=os.path.relpath(out, APP), levels=n, errors=errs)
    if rp:
        with open(rp, 'w') as fh:
            json.dump(rep, fh, indent=1)
            fh.write('\n')
    print('bundle_check: %d levels + sessions/unlocks/tutorials compared value for value with %s: %d difference(s)%s' % (
        n, os.path.relpath(src, APP), len(errs), '' if not extra else '; extra files %s' % extra))
    for e in errs[:30]:
        print('DIFF', e)
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
