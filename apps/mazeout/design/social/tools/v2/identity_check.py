#!/usr/bin/env python3
"""identity_check.py — proves the v2 switches leave the pinned models untouched: regenerates the reference goldens
(design/social/tools/make_fixtures.py -> design/social/fixtures/*.json) and SOC1's goldens
(Packages/PathCore/Tests/tools/soc_fixtures.py reference|v552 -> Tests/Fixtures/soc_<model>_*.json) into a SCRATCH folder
(never into the tree: Packages/** belongs to B2) and compares them byte for byte with the files in the tree.

    python3 design/social/tools/v2/identity_check.py [--out DIR] [reference] [v552] [design]
Writes DIR/identity.json (default build/p/T6). Exit 1 if any file differs.
"""
import os, sys, json, hashlib, subprocess, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.normpath(os.path.join(HERE, '..', '..', '..', '..'))
TOOLS = os.path.join(APP, 'design', 'social', 'tools')
PKG_TOOLS = os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'tools')
PKG_FIX = os.path.join(APP, 'Packages', 'PathCore', 'Tests', 'Fixtures')
DES_FIX = os.path.join(APP, 'design', 'social', 'fixtures')


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def patched(src, repl):
    s = open(src, encoding='utf-8').read()
    for a, b in repl:
        assert s.count(a) == 1, (src, a)
        s = s.replace(a, b)
    return s


def run(script_text, name, args, tmp):
    path = os.path.join(tmp, name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(script_text)
    t = time.time()
    r = subprocess.run(['nice', '-n', '19', sys.executable, path] + args, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-2000:], r.stderr[-4000:])
        raise SystemExit('%s failed' % name)
    return time.time() - t


def main():
    out = os.path.join(APP, 'build', 'p', 'T6')
    argv = sys.argv[1:]
    if '--out' in argv:
        out = argv[argv.index('--out') + 1]
        argv = [a for a in argv if a not in ('--out', out)]
    which = argv or ['design', 'reference', 'v552']
    os.makedirs(out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix='soc_identity_')
    res = dict(when=time.strftime('%Y-%m-%d %H:%M:%S'), scratch=tmp, files={}, seconds={})
    if 'design' in which:
        d = os.path.join(tmp, 'design')
        os.makedirs(d)
        txt = patched(os.path.join(TOOLS, 'make_fixtures.py'), [
            ("sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))", "sys.path.insert(0, %r)" % TOOLS),
            ("OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'fixtures'))", "OUT = %r" % d)])
        res['seconds']['design'] = round(run(txt, 'make_fixtures.py', [], tmp), 1)
        for f in sorted(os.listdir(d)):
            res['files']['design/social/fixtures/' + f] = dict(same=sha(os.path.join(d, f)) == sha(os.path.join(DES_FIX, f)),
                                                               sha256=sha(os.path.join(d, f)))
    for model in ('reference', 'v552'):
        if model not in which:
            continue
        d = os.path.join(tmp, 'pkg_' + model)
        os.makedirs(d)
        txt = patched(os.path.join(PKG_TOOLS, 'soc_fixtures.py'), [
            ("HERE = os.path.dirname(os.path.abspath(__file__))", "HERE = %r" % PKG_TOOLS),
            ("OUT = os.path.normpath(os.path.join(HERE, '..', 'Fixtures'))", "OUT = %r" % d)])
        res['seconds'][model] = round(run(txt, 'soc_fixtures.py', [model], tmp), 1)
        for f in sorted(os.listdir(d)):
            res['files']['Packages/PathCore/Tests/Fixtures/' + f] = dict(
                same=sha(os.path.join(d, f)) == sha(os.path.join(PKG_FIX, f)), sha256=sha(os.path.join(d, f)))
    res['all_identical'] = all(v['same'] for v in res['files'].values()) and bool(res['files'])
    with open(os.path.join(out, 'identity.json'), 'w') as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1))
    sys.exit(0 if res['all_identical'] else 1)


if __name__ == '__main__':
    main()
