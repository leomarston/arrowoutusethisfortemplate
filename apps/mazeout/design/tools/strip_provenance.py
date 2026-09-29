#!/usr/bin/env python3
"""strip_provenance.py — what ships must not say where it came from (PUBLISH item 12 + gate G4c; SPEC.md ruling 39 OD8
"STRIP provenance from every shipped file"; design/publish/level-reorder.md §11 D3; PLAN-P B0).

The SHIPPED set is what project.yml puts in the .app (VERIFIED against build/v3/app/ArrowOut.app, 2026-09-27):
  App/Resources/{Levels,Sounds,Music,Tuning,Fonts,Social}/**  folder references, copied as they are
  App/Resources/Localizable.xcstrings                          compiled to <lang>.lproj/Localizable.strings (comments dropped)
  App/Resources/Assets.xcassets                                compiled to Assets.car
  App/Board/LabBoards/*.json                                   copied to the bundle ROOT (Debug and Release)
  NOT shipped: App/Resources/Strings/**, App/Resources/StoreKit/** (project.yml excludes)
Provenance = the original's research trail: `research/` paths, the word "phone" (the owner's phone), the original's version
tag (v552 / v582), the original's level names (L0nn), recast notes. Brand stems (maze out, grand games, arrowjam, tap away)
and "simulat" are reported too (gate G4c), never rewritten here.

RULES (each hit class has exactly one action; `rules` prints them with their evidence):
  level:capture        Levels/level_NNNN.json "capture"          drop   runtime reads no capture (LevelSpec.capture only feeds
                                                                        the content validators) — companion: publish-form tests
  level:_comment       Levels/level_NNNN.json "_from" ...        drop   "_" keys are comments for every reader
  level:source         Levels/level_NNNN.json "source"           drop   FIX-2 B (N-01): "recorded" / "video" says where a board
                                                                        was read; the runtime reads no source (LevelJSON decodes
                                                                        an absent one as "designed") — companion: publish-form tests
  level:metrics        Levels/level_NNNN.json "metrics"          drop   FIX-2 B (N-01): the bot's measurements ("bot_time_left");
                                                                        the runtime reads none (the validators recompute them)
  curve:_comment       Levels/curve.json "_about"                keep   B0: NEUTRALISED at the source instead (design/levels.json
                                                                        curve + build_levels.py + CurveSpec.default literal: "the
                                                                        recorded" / "v552" removed, a text-only sha re-pin), so the
                                                                        bundled curve stays == CurveSpec.default; the scan must
                                                                        still find 0 provenance tokens in it
  tuning:_comment      Tuning/*.json "_about"/"_doc"/"_sources"… drop   every reader skips "_" keys (EconomyRules, RulesTuning,
                                                                        Tunable, SocialConfig decode named keys only)
  tuning:worldModel    Tuning/social.json "worldModel": "v552"   rewrite -> "shipped": SocialWorldModel.named(_) maps every
                                                                        name but "reference" to the shipped model — companion:
                                                                        SocialConfig default, SocialNamesTests:170, the model name
  xcstrings:comment    Localizable.xcstrings "comment"           compiled away (VERIFIED: .lproj/Localizable.strings 0 hits)
  labboard:*           App/Board/LabBoards/lab*_L0nn.json        exclude from the Release .app (lab-only boards; project.yml)
  social:blocklist     Social/block_names.txt, social_names.json "iphone"   keep: a username brand block, not provenance; it
                                                                        contains the letters "phone" only (the word check says 0).
                                                                        B0: the literal acceptance regex EXCLUDES exactly this
                                                                        token in exactly these two files (ACCEPT_ALLOW, reason
                                                                        printed by `scan`): a blocklist must name what it blocks
  (binary) the Swift executable, Info.plist, CodeResources: reported by `scan`, fixed in source (B0/B2), never patched here.
JSON edits are made on the TEXT: a dropped member is cut out with its separator, every other byte stays (lvtool's number
forms, the tuning files' layout), and the result must parse to exactly the parsed original minus the dropped keys.

  python3 design/tools/strip_provenance.py scan PATH... [--json FILE]      hit classes of files, folders or a built .app
  python3 design/tools/strip_provenance.py publish --out DIR [--app ROOT]  the publish copy of the whole shipped set
  python3 design/tools/strip_provenance.py strip-levels DIR                in place, after `lv.sh bundle` (B0)
  python3 design/tools/strip_provenance.py strip-json FILE...              in place (Tuning; B0's choice: source or build phase)
  python3 design/tools/strip_provenance.py bundle LEVELS.JSON DIR [--publish]   the Python mirror of lvtool's bundle writer
  python3 design/tools/strip_provenance.py check-bundle LEVELS.JSON DIR [--publish]  DIR == the mirror, byte for byte
  python3 design/tools/strip_provenance.py rules
Exit 1 when `scan` finds a provenance hit that no rule allows.
"""
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(os.path.dirname(HERE))

# ------------------------------------------------------------------------------------------------ patterns
ACCEPT_RE = re.compile(rb'research/|phone|v552|L0\d\d')          # PLAN-P T8 acceptance, literal
# B0 (PLAN-P §4.4 acceptance `grep -rE "research/|phone|v552" App/Resources` = 0): the ONE stated exclusion. The username
# blocklists must name the brand they block, and "iphone" contains the letters "phone" — a functional entry (a player may
# not be called "iphone"), not the research trail. Excluded: that token, in those two files, nothing else.
ACCEPT_ALLOW = {('Social/block_names.txt', b'iphone'): 'username blocklist entry "iphone" (a brand players may not use as a '
                                                       'name; contains the letters "phone", is not provenance)',
                ('Social/social_names.json', b'iphone'): 'username blocklist entry "iphone" in blockNames (same list, '
                                                          'shipped as JSON; not provenance)'}
CLASSES = [                                                        # (class, bytes regex) — provenance
    ('research-path', re.compile(rb'research/')),
    ('phone-word', re.compile(rb'(?i)(?<![a-z])phone')),          # phone, phone's, Phone, phoneShots
    ('phone-substring', re.compile(rb'(?i)(?<=[a-z])phone')),     # iphone, iPhoneSimulator, headphone: not the word
    ('version-tag', re.compile(rb'v5[58]2')),
    ('level-name', re.compile(rb'L0\d\d')),
]
INFO = [('level-ref', re.compile(rb'(?<![A-Za-z0-9])L\d{2,3}(?![0-9])'))]   # any L34-style number: reported, not judged
BRAND = [('brand', re.compile(rb'(?i)maze ?out|grand ?games|arrow ?jam|tap ?away')),
         ('sim-string', re.compile(rb'(?i)simulat'))]
SHIPPED = [('App/Resources/Levels', 'folder'), ('App/Resources/Sounds', 'folder'), ('App/Resources/Music', 'folder'),
           ('App/Resources/Tuning', 'folder'), ('App/Resources/Fonts', 'folder'), ('App/Resources/Social', 'folder'),
           ('App/Resources/Localizable.xcstrings', 'compiled'), ('App/Resources/Assets.xcassets', 'compiled'),
           ('App/Board/LabBoards', 'root')]
NOT_SHIPPED = ['App/Resources/Strings', 'App/Resources/StoreKit']
WORLD_MODEL_NAME = 'shipped'
PROVENANCE = ('research-path', 'phone-word', 'version-tag', 'level-name')   # phone-substring / brand / sim-string: reported


# ------------------------------------------------------------------------------------------------ a byte-preserving JSON reader
_WS = re.compile(r'[ \t\n\r]*')
_STR = re.compile(r'"(?:[^"\\]|\\.)*"', re.S)
_NUM = re.compile(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?')


class Node:
    __slots__ = ('kind', 'start', 'end', 'members', 'items')

    def __init__(self, kind, start):
        self.kind, self.start, self.end, self.members, self.items = kind, start, None, None, None


def parse(text):
    """The JSON value tree with spans: objects carry members (key, key_start, value_node), arrays their items."""
    def value(i):
        i = _WS.match(text, i).end()
        c = text[i]
        if c == '{':
            n = Node('object', i)
            n.members = []
            i = _WS.match(text, i + 1).end()
            if text[i] == '}':
                n.end = i + 1
                return n, n.end
            while True:
                m = _STR.match(text, i)
                key = json.loads(m.group(0))
                j = _WS.match(text, m.end()).end()
                assert text[j] == ':', 'expected : at %d' % j
                v, j = value(j + 1)
                n.members.append((key, i, v))
                j = _WS.match(text, j).end()
                if text[j] == ',':
                    i = _WS.match(text, j + 1).end()
                    continue
                assert text[j] == '}', 'expected } at %d' % j
                n.end = j + 1
                return n, n.end
        if c == '[':
            n = Node('array', i)
            n.items = []
            i = _WS.match(text, i + 1).end()
            if text[i] == ']':
                n.end = i + 1
                return n, n.end
            while True:
                v, j = value(i)
                n.items.append(v)
                j = _WS.match(text, j).end()
                if text[j] == ',':
                    i = j + 1
                    continue
                assert text[j] == ']', 'expected ] at %d' % j
                n.end = j + 1
                return n, n.end
        if c == '"':
            m = _STR.match(text, i)
            n = Node('string', i)
            n.end = m.end()
            return n, n.end
        for lit in ('true', 'false', 'null'):
            if text.startswith(lit, i):
                n = Node('literal', i)
                n.end = i + len(lit)
                return n, n.end
        m = _NUM.match(text, i)
        assert m and m.end() > i, 'bad JSON at %d' % i
        n = Node('number', i)
        n.end = m.end()
        return n, n.end
    root, end = value(0)
    assert _WS.match(text, end).end() == len(text), 'trailing data'
    return root


def path_at(root, text, off):
    """JSON path of the innermost value / key containing offset `off` ('/key/sub[3]', key names included)."""
    path, n = '', root
    while True:
        if n.kind == 'object':
            for key, ks, v in n.members:
                if ks <= off < v.end:
                    path += '/' + key
                    if off < v.start:
                        return path + ' (key)'
                    n = v
                    break
            else:
                return path
        elif n.kind == 'array':
            for i, v in enumerate(n.items):
                if v.start <= off < v.end:
                    path += '[%d]' % i
                    n = v
                    break
            else:
                return path
        else:
            return path


def edit_json(text, drop, rewrite=None):
    """Cuts every member for which drop(path, key) is true out of the text (with its separator) and replaces the string
    value of every member rewrite(path, key) names (-> new string). Returns (new_text, [(action, path)])."""
    root = parse(text)
    edits, done = [], []

    def walk(n, path):
        if n.kind == 'array':
            for i, v in enumerate(n.items):
                walk(v, '%s[%d]' % (path, i))
            return
        if n.kind != 'object':
            return
        ms = n.members
        dropped = [drop(path, k) for k, _, _ in ms]
        kept = [i for i, d in enumerate(dropped) if not d]
        if ms and not kept:
            edits.append((ms[0][1], ms[-1][2].end, ''))
        else:
            last_kept = kept[-1] if kept else -1
            for i, (k, ks, v) in enumerate(ms):
                if dropped[i] and i < last_kept:
                    edits.append((ks, ms[i + 1][1], ''))
            if ms and last_kept < len(ms) - 1:
                edits.append((ms[last_kept][2].end, ms[-1][2].end, ''))
        for i, (k, ks, v) in enumerate(ms):
            p = '%s/%s' % (path, k)
            if dropped[i]:
                done.append(('drop', p))
                continue
            new = rewrite(path, k) if rewrite else None
            if new is not None and v.kind == 'string':
                edits.append((v.start, v.end, json.dumps(new)))
                done.append(('rewrite', p))
                continue
            walk(v, p)
    walk(root, '')
    out, last = [], 0
    for a, b, rep in sorted(edits):
        assert a >= last, 'overlapping edits'
        out.append(text[last:a])
        out.append(rep)
        last = b
    out.append(text[last:])
    return ''.join(out), done


def transform(obj, drop, rewrite=None, path=''):
    """The same edits on the parsed value (the proof edit_json's text means what it should)."""
    if isinstance(obj, list):
        return [transform(v, drop, rewrite, '%s[%d]' % (path, i)) for i, v in enumerate(obj)]
    if not isinstance(obj, dict):
        return obj
    out = {}
    for k, v in obj.items():
        if drop(path, k):
            continue
        new = rewrite(path, k) if rewrite else None
        out[k] = new if (new is not None and isinstance(v, str)) else transform(v, drop, rewrite, '%s/%s' % (path, k))
    return out


# ------------------------------------------------------------------------------------------------ the rules
def is_comment(path, key):
    return key.startswith('_')


def level_drop(path, key):
    return path == '' and (key in ('capture', 'source', 'metrics') or key.startswith('_'))   # FIX-2 B (N-01): + source, metrics


def tuning_rewrite(name):
    def rw(path, key):
        return WORLD_MODEL_NAME if (name == 'social.json' and path == '' and key == 'worldModel') else None
    return rw


def xcstrings_drop(path, key):
    return key == 'comment'


def strip_file_text(rel, text):
    """(new_text, actions) for one shipped JSON file by its bundle-relative path; None when no rule applies."""
    base = os.path.basename(rel)
    if rel.startswith('Levels/') and base.startswith('level_'):
        drop, rw = level_drop, None
    elif rel == 'Levels/curve.json':
        return None                                   # B0: neutral "_about" kept (see RULES curve:_comment)
    elif rel.startswith('Levels/') or rel.startswith('Tuning/'):
        drop, rw = is_comment, tuning_rewrite(base)
    elif base.endswith('.xcstrings'):
        drop, rw = xcstrings_drop, None
    else:
        return None
    new, done = edit_json(text, drop, rw)
    if json.loads(new) != transform(json.loads(text), drop, rw):
        raise SystemExit('strip_provenance: %s: the text edit does not equal the parsed edit' % rel)
    return new, done


# ------------------------------------------------------------------------------------------------ scan
def area_of(rel, path):
    """Hit class area from the bundle-relative file and the JSON path."""
    base = os.path.basename(rel)
    key = path.split('/')[1].split(' ')[0].split('[')[0] if path.startswith('/') else ''
    if base.startswith('lab') and base.endswith('.json') and ('LabBoards' in rel or '/' not in rel):
        return 'labboard:' + (key or 'file')
    if rel.startswith('Levels/') and base.startswith('level_'):
        return 'level:' + ('capture' if key == 'capture' else '_comment' if key.startswith('_') else key or 'text')   # source / metrics: by name
    if rel.startswith('Levels/'):
        return 'curve:_comment' if key.startswith('_') else 'levels-aux:' + (key or 'text')
    if rel.startswith('Tuning/'):
        if key.startswith('_') or any(p.startswith('_') for p in path.split('/')):
            return 'tuning:_comment'
        return 'tuning:' + key
    if rel.startswith('Social/'):
        return 'social:blocklist' if ('block' in base or key.startswith('block')) else 'social:' + (key or 'text')
    if base.endswith('.xcstrings'):
        return 'xcstrings:comment' if path.endswith('/comment') else 'xcstrings:' + (key or 'text')
    if base.endswith('.strings'):
        return 'lproj:strings'
    if base == 'Info.plist':
        return 'binary:Info.plist'
    if base == 'CodeResources':
        return 'binary:CodeResources'
    if base.endswith('.tsv') or base.endswith('.txt'):
        return 'text:' + base
    return 'binary:' + base if '.' not in base or base.endswith(('.car', '.ttf', '.otf', '.wav', '.m4a', '.png')) else 'file:' + base


def classify(b):
    return [(name, m.start(), m.end()) for name, rx in CLASSES + INFO + BRAND for m in rx.finditer(b)]


def context(b, a, e, width=60):
    s, t = max(0, a - width), min(len(b), e + width)
    return b[s:t].decode('utf-8', 'replace').replace('\n', ' ').replace('\x00', ' ')


def scan_file(p, rel):
    b = open(p, 'rb').read()
    hits = []
    tree = text = None
    if rel.endswith(('.json', '.xcstrings')):
        try:
            text = b.decode('utf-8')
            tree = parse(text)
        except Exception:
            tree = None
    name_hits = [(c, m.group(0).decode()) for c, rx in CLASSES for m in rx.finditer(os.path.basename(rel).encode())]
    for c, tok in name_hits:
        hits.append(dict(file=rel, cls=c, area=area_of(rel, '') if not os.path.basename(rel).startswith('lab')
                         else 'labboard:filename', path='(file name)', token=tok, context=os.path.basename(rel)))
    for c, a, e in classify(b):
        path = ''
        if tree is not None:
            off = len(b[:a].decode('utf-8', 'replace'))
            path = path_at(tree, text, off)
        hits.append(dict(file=rel, cls=c, area=area_of(rel, path), path=path, token=b[a:e].decode('utf-8', 'replace'),
                         context=context(b, a, e)))
    accept = 0
    for m in ACCEPT_RE.finditer(b):
        allowed = [tok for (f, tok) in ACCEPT_ALLOW if f == rel and b[max(0, m.end() - len(tok)):m.end()] == tok]
        if allowed:
            hits.append(dict(file=rel, cls='accept-excluded', area='social:blocklist', path='', token=allowed[0].decode(),
                             context=ACCEPT_ALLOW[(rel, allowed[0])]))
        else:
            accept += 1
    return hits, accept + len(ACCEPT_RE.findall(os.path.basename(rel).encode()))


def walk(root):
    if os.path.isfile(root):
        yield root, os.path.basename(root)
        return
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            p = os.path.join(dp, f)
            yield p, os.path.relpath(p, root)


def scan(paths):
    hits, accept, files = [], 0, 0
    for root in paths:
        for p, rel in walk(root):
            files += 1
            rel2 = rel
            if os.path.isdir(root) and os.path.basename(root.rstrip('/')) in ('Levels', 'Tuning', 'Social', 'Sounds', 'Music',
                                                                              'Fonts', 'LabBoards'):
                rel2 = os.path.basename(root.rstrip('/')) + '/' + rel
            h, n = scan_file(p, rel2)
            hits += h
            accept += n
    return hits, accept, files


def summarize(hits):
    table = {}
    for h in hits:
        if h['cls'] in ('brand', 'sim-string'):
            key = ('G4c:' + h['cls'], h['area'])
        else:
            key = (h['cls'], h['area'])
        t = table.setdefault(key, dict(hits=0, files=set(), example=None))
        t['hits'] += 1
        t['files'].add(h['file'])
        t['example'] = t['example'] or '%s %s: %s' % (h['file'], h['path'], h['context'][:110])
    return table


def unallowed(hits):
    return [h for h in hits if h['cls'] in PROVENANCE]


def cmd_scan(argv):
    jp = argv[argv.index('--json') + 1] if '--json' in argv else None
    paths = [a for a in argv if not a.startswith('--') and a != jp]
    hits, accept, files = scan(paths)
    table = summarize(hits)
    bad = unallowed(hits)
    print('scan: %d files; literal acceptance regex research/|phone|v552|L0\\d\\d: %d hits; provenance hits no rule allows: %d'
          % (files, accept, len(bad)))
    for x in [h for h in hits if h['cls'] == 'accept-excluded']:
        print('  excluded from the acceptance regex (stated): %s "%s" — %s' % (x['file'], x['token'], x['context']))
    for (cls, area), t in sorted(table.items(), key=lambda kv: (-kv[1]['hits'], kv[0])):
        print('  %-16s %-26s %5d hits in %3d files   e.g. %s' % (cls, area, t['hits'], len(t['files']), t['example']))
    if jp:
        json.dump(dict(paths=paths, files=files, acceptance_regex_hits=accept, unallowed=len(bad),
                       classes=[dict(cls=c, area=a, hits=t['hits'], files=sorted(t['files']), example=t['example'])
                                for (c, a), t in sorted(table.items())], hits=hits), open(jp, 'w'), indent=1)
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ bundle mirror (lvtool)
def _ints(o):
    if isinstance(o, float) and o.is_integer():
        return int(o)
    if isinstance(o, dict):
        return {k: _ints(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_ints(v) for v in o]
    return o


def encode_level(l):
    """lvtool's level file (ContentBundle form .encoded): LevelJSON.encodeBundle (sorted, compact, nulls / layer 1 / empty
    obstacle lists elided, integral doubles without '.0') with the "_" comments first. VERIFIED byte for byte against the
    150 files of App/Resources/Levels on 2026-09-28 (check-bundle)."""
    out = {}
    for k, v in l.items():
        if k.startswith('_') or v is None:
            continue
        if k == 'arrows':
            v = [{ak: av for ak, av in a.items() if av is not None and not (ak == 'layer' and av == 1)} for a in v]
        elif k == 'obstacles':
            v = [{ok: ov for ok, ov in o.items() if ov is not None and not (ok in ('arrows', 'ends', 'reveals') and ov == [])}
                 for o in v]
        out[k] = v
    body = json.dumps(_ints(out), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    ins = ''.join(json.dumps(k, ensure_ascii=False) + ':' + json.dumps(v, ensure_ascii=False) + ','
                  for k, v in sorted((k, v) for k, v in l.items() if k.startswith('_')))
    return '{' + ins + body[1:] + '\n'


def bundle_files(doc, publish=False):
    def c(o):
        return json.dumps(o, sort_keys=True, separators=(',', ':')) + '\n'
    out = {}
    for l in doc['levels']:
        name = 'level_%04d.json' % l['level']
        out[name] = encode_level(l)
        if publish:
            out[name] = strip_file_text('Levels/' + name, out[name])[0]
    for name, key in (('sessions.json', 'sessions'), ('unlocks.json', 'unlocks'), ('tutorials.json', 'tutorials')):
        out[name] = c({'schema': 1, key: doc[key]})
    out['curve.json'] = c(doc['curve'])
    return out                                        # B0: curve.json is the same in both forms (neutral "_about")


def cmd_bundle(argv, check=False):
    pos = [a for a in argv if not a.startswith('--')]
    doc = json.load(open(pos[0]))
    files = bundle_files(doc, publish='--publish' in argv)
    folder = pos[1]
    if check:
        bad = []
        for name, text in sorted(files.items()):
            p = os.path.join(folder, name)
            if not os.path.exists(p) or open(p, 'rb').read() != text.encode('utf-8'):
                bad.append(name)
        extra = sorted(f for f in os.listdir(folder) if f not in files and f != '.gitkeep')
        print('check-bundle: %d files; %d differ %s; extra %s' % (len(files), len(bad), bad[:12], extra))
        return 1 if bad or extra else 0
    os.makedirs(folder, exist_ok=True)
    for name, text in files.items():
        with open(os.path.join(folder, name), 'w', encoding='utf-8') as f:
            f.write(text)
    print('bundle: %d files -> %s%s' % (len(files), folder, ' (publish form)' if '--publish' in argv else ''))
    return 0


# ------------------------------------------------------------------------------------------------ strip / publish
def strip_in_place(paths, rel_prefix):
    actions = []
    for root in paths:
        for p, rel in walk(root):
            if not rel.endswith(('.json', '.xcstrings')):
                continue
            text = open(p, encoding='utf-8').read()
            r = strip_file_text(rel_prefix + rel, text)
            if r is None:
                continue
            new, done = r
            if new != text:
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(new)
            actions += [(rel_prefix + rel, a, path) for a, path in done]
    return actions


def cmd_publish(argv):
    app = os.path.abspath(argv[argv.index('--app') + 1]) if '--app' in argv else APP
    out = os.path.abspath(argv[argv.index('--out') + 1])
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    log = []
    for src, how in SHIPPED:
        s = os.path.join(app, src)
        if not os.path.exists(s):
            continue
        if how == 'root':
            log.append(dict(file=src, action='exclude', path='*',
                            why='lab-only boards: exclude from the Release .app (project.yml, B0)'))
            continue
        dst = os.path.join(out, os.path.basename(src))
        if os.path.isdir(s):
            shutil.copytree(s, dst)
        else:
            shutil.copyfile(s, dst)
        if src.endswith('.xcstrings'):
            log += [dict(file=f, action='compiled-away', path=p) for f, _, p in strip_in_place([dst], '')]
        elif how == 'folder':
            log += [dict(file=f, action=a, path=p) for f, a, p in strip_in_place([dst], os.path.basename(src) + '/')]
    with open(os.path.join(out, 'PUBLISH-ACTIONS.json'), 'w') as f:
        json.dump(log, f, indent=0)
    by = {}
    for x in log:
        key = (x['action'], x['file'] if x['action'] == 'exclude' else x['file'].split('/')[0] if '/' in x['file'] else x['file'],
               re.sub(r'\[\d+\]', '[]', x['path'].rsplit('/', 1)[-1]) if x['action'] != 'compiled-away' else 'comment')
        by.setdefault(key, set()).add(x['file'])
    print('publish copy -> %s (actions in PUBLISH-ACTIONS.json):' % os.path.relpath(out, APP))
    for (a, area, key), files in sorted(by.items()):
        print('  %-14s %-34s %-12s in %3d file(s)' % (a, area, key, len(files)))
    return 0


def cmd_rules():
    print(__doc__.split('RULES')[1].split('JSON edits')[0])
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == 'scan':
        return cmd_scan(rest)
    if cmd == 'publish':
        return cmd_publish(rest)
    if cmd == 'strip-levels':
        acts = strip_in_place(rest, 'Levels/')
        print('strip-levels: %d edits in %s' % (len(acts), rest))
        return 0
    if cmd == 'strip-json':
        acts = []
        for p in rest:
            rel = 'Tuning/' + os.path.basename(p) if '/Tuning/' in os.path.abspath(p) else (
                'Levels/' + os.path.basename(p) if '/Levels/' in os.path.abspath(p) else os.path.basename(p))
            text = open(p, encoding='utf-8').read()
            r = strip_file_text(rel, text)
            if r and r[0] != text:
                open(p, 'w', encoding='utf-8').write(r[0])
                acts += r[1]
        print('strip-json: %d edits' % len(acts))
        return 0
    if cmd == 'bundle':
        return cmd_bundle(rest)
    if cmd == 'check-bundle':
        return cmd_bundle(rest, check=True)
    if cmd == 'rules':
        return cmd_rules()
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
