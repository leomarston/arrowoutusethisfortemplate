#!/usr/bin/env python3
"""build_name_data_v2.py — design/social/data_v2/social_names_v2.json, the v2 name resource (M5/M6/M7; social-intl §6.2).

What changes against v1 (data/social_names.json, which stays byte-identical for the reference / v552 models):
  * first-name lists: one per culture (the reference's 16 + NEW_CULTURES of socialsim/v2.py), most common first, from
    Wikidata (CC0): the first given name of every human with that citizenship and sex born 1950-2008, counted per name,
    each (country, sex) normalised to shares and averaged, so men and women and every source country weigh the same
    (tools/v2/wd_fetch.py caches the raw data in sources/wikidata/). 'en' keeps the SSA list (public domain, v1).
    Lists are NOT made disjoint across cultures any more (the shipped model draws names; uniqueness is the gid's job), so
    'Anna' is in the Slovak, Czech, Polish and German lists alike, where it is common.
  * native scripts: el ru uk bg he ar fa jp kr zh th hy ka kk carry [native script, Latin romanisation] pairs (the
    romanisation is the name's English label / Hepburn / pinyin on Wikidata, folded to ASCII); Latin cultures carry
    [spelling with diacritics, ASCII fold] as before. A Chinese given name of one character becomes a 2-character
    nickname (小X / 阿X / XX, by a fixed hash of the character) so it passes the 2-character rule for Han names.
  * blocklists: v1's lists + data_v2/*_add.txt (SL HR SR SK CS PL RU UK BG HU RO EL FI JA KO ZH AR FA HI + native-script
    stems), stored as key() (fold + lowercase), since names are matched on their key.
  * everything else (words, adjectives, nouns, caps, suffixes, initials) is v1's, and the invented handles are v1's minus
    the ones the v2 blocklists catch (social-intl §4 P1-4 examples) and every handle carrying an invented-handle root (below).
Deterministic: same inputs -> byte-identical JSON. Prints a report (list sizes, sources, blocklist collateral).
    python3 design/social/tools/v2/build_name_data_v2.py [--min 300] [--max 600]
"""
import os, sys, json, unicodedata, re
HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, TOOLS)
sys.path.insert(0, HERE)
from socialsim import data as D, core as K                       # noqa: E402
import wd_fetch as WF                                           # noqa: E402
import pubscreen                                                # noqa: E402
from socialsim import names as _Nm                              # noqa: E402
sha8 = pubscreen.sha8
# the published list (LDNOOBW, CC BY 4.0) screens the pools at build time; only the promotion rule (below) ships entries
PUB = pubscreen.Published(D.key, _Nm.tokens_of)

ROOT = os.path.normpath(os.path.join(TOOLS, '..'))
SRC = os.path.join(ROOT, 'sources', 'wikidata')
D2 = os.path.join(ROOT, 'data_v2')
OUT = os.path.join(D2, 'social_names_v2.json')
V1 = os.path.join(ROOT, 'data', 'social_names.json')
OLD16 = ['tr', 'de', 'fr', 'es', 'pt', 'it', 'nl', 'nordic', 'pl', 'easteu', 'in', 'sea', 'jp', 'kr', 'ar', 'en']
NEW = ['sk', 'sl', 'cs', 'hu', 'ro', 'el', 'ru', 'uk', 'bg', 'hr', 'sr', 'th', 'vi', 'id', 'ms', 'tl', 'zh', 'he',
       'ptpt', 'fi', 'fa', 'sq', 'lt', 'lv', 'et', 'ur', 'hy', 'ka', 'az', 'kk', 'uz', 'af']
ORDER = OLD16 + NEW
MIN_N = int(sys.argv[sys.argv.index('--min') + 1]) if '--min' in sys.argv else 300
MAX_N = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 600
MAX_LEN = 12

SCRIPT = {   # native script of the non-Latin cultures: unicode name prefix of every letter
    'el': ('GREEK',), 'ru': ('CYRILLIC',), 'uk': ('CYRILLIC',), 'bg': ('CYRILLIC',), 'kk': ('CYRILLIC',),
    'he': ('HEBREW',), 'ar': ('ARABIC',), 'fa': ('ARABIC',), 'jp': ('HIRAGANA', 'KATAKANA', 'CJK UNIFIED'),
    'kr': ('HANGUL',), 'zh': ('CJK UNIFIED',), 'th': ('THAI',), 'hy': ('ARMENIAN',), 'ka': ('GEORGIAN',)}


def lines(path):
    out = []
    for l in open(path, encoding='utf-8'):
        l = l.rstrip('\n')
        if l and not l.startswith('#'):
            out.append(l)
    return out


def script_ok(s, culture):
    want = SCRIPT[culture]
    for ch in s:
        if ch in 'ー':                      # the katakana long-vowel mark
            continue
        n = unicodedata.name(ch, '')
        if unicodedata.category(ch).startswith('M'):
            continue
        if not any(n.startswith(w) for w in want):
            return False
    return True


def latin_ok(s):
    return bool(re.fullmatch(r'[A-Za-z]+', s))


def is_latin_word(s):
    """Letters of the Latin script only (any diacritics), no spaces, digits, hyphens or apostrophes."""
    for ch in s:
        if unicodedata.category(ch).startswith('M'):
            continue
        n = unicodedata.name(ch, '')
        if not n.startswith('LATIN') or not ch.isalpha():
            return False
    return True


def cap(s):
    return s[:1].upper() + s[1:]


def romanise(s):
    """An English label / Hepburn / pinyin -> an ASCII nickname: fold, drop hyphens and apostrophes, capitalise
    ('Su-jin' -> 'Sujin', 'Kōji' -> 'Koji', 'Tíng' -> 'Ting')."""
    s = D.fold(s).replace('-', '').replace("'", '').replace('’', '')
    return cap(s.lower()) if s[:1].isupper() or s[:1].islower() else s


class Blocker:
    def __init__(self):
        self.sub = [D.key(x) for x in lines(os.path.join(ROOT, 'data', 'blocklist_substring.txt'))]
        self.tok = set(D.key(x) for x in lines(os.path.join(ROOT, 'data', 'blocklist_token.txt')))
        self.names = set(D.key(x) for x in lines(os.path.join(ROOT, 'data', 'block_names.txt')))
        self.sub_add = [D.key(x) for x in lines(os.path.join(D2, 'blocklist_substring_add.txt'))]
        self.tok_add = set(D.key(x) for x in lines(os.path.join(D2, 'blocklist_token_add.txt')))
        self.names_add = set(D.key(x) for x in lines(os.path.join(D2, 'block_names_add.txt')))
        self.relax = [D.key(x) for x in lines(os.path.join(D2, 'blocklist_relax_v2.txt'))]
        self.sub_v1_full = list(self.sub)
        self.sub = [x for x in self.sub if x not in self.relax]          # v2: these match whole tokens only
        self.tok_add = self.tok_add | set(self.relax)
        leet = str.maketrans({'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b', '@': 'a', '$': 's', '!': 'i'})
        self.leet = leet

    def invented_roots(self):
        """Built by rule: every 3-letter prefix shared by at least 3 Latin substring stems of the v2 additions (a stem
        family such as the conjugated forms of one root). A procedurally invented handle containing such a root is
        dropped from the pool (real first names are not screened with it: the roots are too short for them)."""
        fam = {}
        for b in self.sub_add:
            if b.isascii() and b.isalpha() and len(b) >= 4:
                fam.setdefault(b[:3], set()).add(b)
        return sorted(r for r, v in fam.items() if len(v) >= 3)

    def all_sub(self):
        return sorted(set(self.sub) | set(self.sub_add), key=lambda x: (self.sub + self.sub_add).index(x))

    def blocked(self, s, only_new=False, strict=False):
        """The stem that blocks s (None if clean): substrings anywhere, tokens as the whole name or one of its tokens
        (names.tokens_of), exactly like names.is_blocked with the v2 lists. strict = v1's full substring list too."""
        import socialsim.names as Nm0
        k = D.key(s).translate(self.leet)
        subs = self.sub_add if only_new else (self.sub_v1_full if strict else self.sub) + self.sub_add
        toks = self.tok_add | self.names_add if only_new else self.tok | self.tok_add | self.names | self.names_add
        for b in subs:
            if b in k:
                return b
        if k in toks:
            return k
        for t in Nm0.tokens_of(s):
            if t in toks or t.translate(self.leet) in toks:
                return t
        return None


def load_counts(culture):
    countries = WF.CULTURES[culture][0]
    dists = []
    persons = 0
    for iso in countries:
        for sex in 'mf':
            p = os.path.join(SRC, 'counts_%s_%s.json' % (iso, sex))
            if not os.path.exists(p):
                continue
            rows = json.load(open(p, encoding='utf-8'))['rows']
            tot = float(sum(c for _, c in rows)) or 1.0
            persons += int(tot)
            dists.append({q: c / tot for q, c in rows})
    score = {}
    for d in dists:
        for q, sh in d.items():
            score[q] = score.get(q, 0.0) + sh / len(dists)
    raw = {}
    for iso in countries:
        for sex in 'mf':
            p = os.path.join(SRC, 'counts_%s_%s.json' % (iso, sex))
            if os.path.exists(p):
                for q, c in json.load(open(p, encoding='utf-8'))['rows']:
                    raw[q] = raw.get(q, 0) + c
    return score, raw, persons, len(dists)


def load_labels(culture):
    p = os.path.join(SRC, 'labels_%s.json' % culture)
    if not os.path.exists(p):
        return None
    lab = {}
    for q, l, nl, hep, pin in json.load(open(p, encoding='utf-8'))['rows']:
        d = lab.setdefault(q, dict(l={}, nl={}, hep=set(), pin=set()))
        if l:
            d['l'][l[1]] = l[0]
        if nl:
            d['nl'][nl[1]] = nl[0]
        if hep:
            d['hep'].add(hep[0])
        if pin:
            d['pin'].add(pin[0])
    return lab


def zh_nickname(ch):
    """A one-character Chinese given name -> a 2-character nickname and its pinyin pattern (fixed by the character)."""
    k = K.h64(0x7A68, 'zh1', ord(ch)) % 10
    if k < 4:
        return '小' + ch, 'xiao'
    if k < 6:
        return '阿' + ch, 'a'
    return ch + ch, 'double'


def pairs_for(culture, lab, score):
    """[(native, latin, score, qid)] for the culture, before the blocklist."""
    countries, langs, script = WF.CULTURES[culture]
    out = []
    for q, sc in score.items():
        d = lab.get(q)
        if d is None:
            continue
        if script == 'latin':
            name = None
            for lg in langs + ['mul']:
                v = d['l'].get(lg)
                if v and is_latin_word(v):
                    name = v
                    break
            if name is None:
                v = d['l'].get('en')
                if v and is_latin_word(v):
                    name = v
            if name is None:
                continue
            name = unicodedata.normalize('NFC', name)
            if not name[:1].isupper():
                continue
            folded = D.fold(name)
            if not latin_ok(folded) or not (2 <= len(name) <= MAX_LEN):
                continue
            out.append((name, folded, sc, q))
        else:
            native = None
            cands = [d['l'].get(lg) for lg in langs] + [d['nl'].get(lg) for lg in langs] + list(d['nl'].values())
            for v in cands:
                if v and script_ok(v, culture) and ' ' not in v:
                    native = unicodedata.normalize('NFC', v)
                    break
            if native is None:
                continue
            lat = None
            pool = []
            if culture == 'jp':
                pool += sorted(d['hep'])
            if culture == 'zh':
                pool += sorted(d['pin'])
            pool += [d['l'].get('en'), d['l'].get('mul')]
            for v in pool:
                if v and is_latin_word(v.replace('-', '').replace("'", '')):
                    lat = romanise(v)
                    break
            if lat is None or not latin_ok(lat):
                continue
            if culture == 'zh' and len(native) == 1:
                native2, pat = zh_nickname(native)
                lat = {'xiao': 'Xiao' + lat.lower(), 'a': 'A' + lat.lower(), 'double': lat + lat.lower()}[pat]
                native = native2
            if len(native) < 2 or len(native) > MAX_LEN or len(lat) > MAX_LEN or len(lat) < 2:
                continue
            # the username rule (Names.swift validateUsername + social-intl P2-4): >= 2 characters only for Han, Hangul
            # and kana; every other script needs >= 3 (a 2-letter Hebrew name would be a name no player could type)
            if culture not in ('jp', 'kr', 'zh') and sum(1 for ch in native if not unicodedata.category(ch).startswith('M')) < 3:
                continue
            out.append((native, lat, sc, q))
    return out


def thai_pairs():
    TITLES_TH = {'นาย', 'นาง', 'นางสาว', 'พลเอก', 'พลตำรวจเอก', 'ดร.', 'หม่อมราชวงศ์', 'หม่อมหลวง', 'พระ', 'สมเด็จ',
                 'พันเอก', 'พลโท', 'พลตรี', 'พลอากาศเอก', 'พลเรือเอก', 'ร้อยตำรวจเอก', 'ศาสตราจารย์', 'รองศาสตราจารย์'}
    TITLES_EN = {'mr', 'mrs', 'ms', 'miss', 'dr', 'gen', 'general', 'prof', 'phra', 'mom', 'm.r.', 'm.l.', 'police', 'colonel'}
    score = {}
    raw_n = {}
    persons = 0
    for sex in 'mf':
        p = os.path.join(SRC, 'thai_persons_%s.json' % sex)
        if not os.path.exists(p):
            continue
        rows = json.load(open(p, encoding='utf-8'))['rows']
        cnt = {}
        for q, th, en in rows:
            tw = th.split()
            ew = en.split()
            if len(tw) < 2 or len(ew) < 2:
                continue
            if tw[0] in TITLES_TH or ew[0].lower().strip('.') in TITLES_EN:
                continue
            key = (unicodedata.normalize('NFC', tw[0]), ew[0])
            cnt[key] = cnt.get(key, 0) + 1
        tot = float(sum(cnt.values())) or 1.0
        persons += int(tot)
        for k2, c in cnt.items():
            score[k2] = score.get(k2, 0.0) + c / tot / 2.0
            raw_n[k2] = raw_n.get(k2, 0) + c
    out = []
    for (th, en), sc in score.items():
        lat = romanise(en)
        if not script_ok(th, 'th') or not latin_ok(lat) or not (2 <= len(th) <= MAX_LEN) or not (2 <= len(lat) <= MAX_LEN):
            continue
        if sum(1 for ch in th if not unicodedata.category(ch).startswith('M')) < 3:
            continue                                  # the username rule: >= 3 characters outside Han / Hangul / kana
        out.append((th, lat, sc, None if raw_n[(th, en)] >= 2 else 'single'))
    return out, persons


def viet_pairs():
    """Vietnamese: the LAST word of each person's own Vietnamese label (the name people are called by), men and women
    weighted equally; the ASCII form is the fold of the Vietnamese spelling (the diacritics carry the tones)."""
    score = {}
    persons = 0
    for sex in 'mf':
        p = os.path.join(SRC, 'viet_persons_%s.json' % sex)
        if not os.path.exists(p):
            continue
        cnt = {}
        for q, vi, en in json.load(open(p, encoding='utf-8'))['rows']:
            w = vi.split()
            if len(w) < 2:
                continue
            nm = unicodedata.normalize('NFC', w[-1])
            if not nm[:1].isupper() or not is_latin_word(nm):
                continue
            cnt[nm] = cnt.get(nm, 0) + 1
        tot = float(sum(cnt.values())) or 1.0
        persons += int(tot)
        for nm, c in cnt.items():
            score[nm] = score.get(nm, [0.0, 0])
            score[nm][0] += c / tot / 2.0
            score[nm][1] += c
    out = []
    for nm, (sc, c) in score.items():
        lat = D.fold(nm)
        if latin_ok(lat) and 2 <= len(nm) <= MAX_LEN:
            out.append((nm, lat, sc, None if c >= 2 else 'single'))
    return out, persons


def main():
    v1 = json.load(open(V1, encoding='utf-8'))
    B = Blocker()
    report = dict(cultures={}, short=[], collateral={})
    cultures = {}
    for cu in ORDER:
        if cu == 'en':
            toks = []
            seen = set()
            for t in lines(os.path.join(ROOT, 'data', 'given_en.txt')):
                t = t.strip()
                k = D.key(t)
                if not t or k in seen or len(D.fold(t)) < 2 or not D.fold(t).replace('-', '').isalpha() or B.blocked(t) or PUB.whole(t):
                    continue
                seen.add(k)
                toks.append([t, D.fold(t)])
            cultures[cu] = toks
            report['cultures'][cu] = dict(n=len(toks), source='SSA (v1 data/given_en.txt), public domain')
            continue
        if cu in ('easteu', 'sea'):
            cultures[cu] = v1['cultures'][cu]            # kept for index stability; no v2 row uses them
            report['cultures'][cu] = dict(n=len(cultures[cu]), source='v1 (unused by v2 rows)')
            continue
        if cu == 'th':
            prs, persons = thai_pairs()
            ndist = 2
            raw = {'single': 1}
        elif cu == 'vi':
            prs, persons = viet_pairs()
            ndist = 2
            raw = {'single': 1}
        else:
            lab = load_labels(cu)
            if lab is None:
                report['cultures'][cu] = dict(n=0, source='not fetched')
                report['short'].append(cu)
                cultures[cu] = []
                continue
            score, raw, persons, ndist = load_counts(cu)
            prs = pairs_for(cu, lab, score)
        # one entry per spelling: items that share a native form (Mohammed / Muhammad -> محمد) or an ASCII key add up
        grp = {}
        persons_of = {}
        for native, lat, sc, q in prs:
            kn = D.key(native)
            g = grp.get(kn)
            n_q = raw.get(q, 2) if q is not None else 2
            if g is None:
                grp[kn] = [native, lat, sc, n_q, sc]
            else:
                g[2] += sc
                g[3] += n_q
                if sc > g[4]:                             # the most common item names the entry
                    g[0], g[1], g[4] = native, lat, sc
        merged = sorted(grp.values(), key=lambda x: (-x[2], x[1], x[0]))
        seen = set()
        toks = []
        dropped = []
        pub_dropped = []
        singles = []
        for native, lat, sc, npers, _ in merged:
            k = D.key(lat)
            if k in seen:
                continue
            b = B.blocked(native) or B.blocked(lat)
            if b:
                dropped.append((native, b))
                continue
            if PUB.whole(native) or PUB.whole(lat):
                pub_dropped.append(native)
                continue
            if npers < 2:
                singles.append([native, lat])             # a single person: used only to fill a short list, last
                continue
            seen.add(k)
            toks.append([native, lat])
            if len(toks) >= MAX_N:
                break
        filled = 0
        for native, lat in singles:
            if len(toks) >= MIN_N:
                break
            if D.key(lat) in seen:
                continue
            seen.add(D.key(lat))
            toks.append([native, lat])
            filled += 1
        cultures[cu] = toks
        # REPORTS NEVER CARRY A BLOCKED NAME OR A STEM (T6 rule): only counts and sha1 prefixes of the dropped names
        report['cultures'][cu] = dict(n=len(toks), persons=persons, distributions=ndist, singlesFilled=filled,
                                      source='Wikidata CC0: ' + ('Thai persons\' own labels (first word)' if cu == 'th' else
                                                                 'Vietnamese persons\' own labels (last word)' if cu == 'vi' else
                                                                 'P735 first given name of humans with citizenship ' +
                                                                 '+'.join(WF.CULTURES[cu][0]) + ', born 1950-2008'),
                                      blockedDropped=len(dropped), blockedDroppedSha1=[sha8(nm) for nm, _ in dropped[:12]],
                                      publishedDropped=len(pub_dropped),
                                      top10=[t[0] for t in toks[:10]])
        if len(toks) < MIN_N:
            report['short'].append(cu)
    # ---- the rest from v1
    adjs, nouns = v1['adjectives'], v1['nouns']
    adj_noun = set(adjs) | set(nouns)
    mixed = {cu: [lat for nat, lat in toks if D.key(lat) not in adj_noun] for cu, toks in cultures.items()}
    tok_stems = [b for b in (B.tok | B.tok_add) if len(b) >= 3 and b.isalpha() and b.isascii()]
    roots = B.invented_roots()
    n_strict = n_edge = n_root = n_pub = 0
    inv = []
    for s in v1['invented']:
        k = D.key(s)
        if B.blocked(s, strict=True):
            n_strict += 1
        elif any(k.startswith(b) or k.endswith(b) for b in tok_stems):
            n_edge += 1
        elif any(r in k for r in roots):
            n_root += 1
        elif PUB.hit(s):
            n_pub += 1
        else:
            inv.append(s)
    report['invented'] = dict(v1=len(v1['invented']), v2=len(inv), removedByStem=n_strict, removedByTokenStemAtAnEdge=n_edge,
                              removedByRoot=n_root, removedByPublishedList=n_pub, roots=len(roots),
                              rootsSha1=sorted(sha8(r) for r in roots))
    # ---- collateral: how many given names of any culture each NEW substring stem hits (they must be token-only);
    #      the report keys a stem by its sha1 prefix and lists culture codes + counts, never a name or a stem
    coll = {}
    for cu, toks in cultures.items():
        for nat, lat in toks:
            for s in (nat, lat):
                kk = D.key(s)
                for b in B.sub_add:
                    if b in kk:
                        coll.setdefault(sha8(b), {}).setdefault(cu, set()).add(s)
    report['collateral'] = {h: {cu: len(v) for cu, v in sorted(d.items())} for h, d in sorted(coll.items())}
    report['publishedScreen'] = PUB.report()
    # ---- promotion (built by rule): a published entry that EQUALS one of our own generated tokens (an initials run, a
    #      suffix, an adjective / noun / word / caps token) and is not an ordinary English word joins the shipped TOKEN list,
    #      so the runtime blocks it (names.is_blocked); written to data_v2/blocklist_promoted_token.txt, never printed
    lettersI = v1['initialsLetters']
    gen = set(a + b for a in lettersI for b in lettersI) | set(a + b + c for a in lettersI for b in lettersI for c in lettersI)
    for pool in (v1['underscoreSuffixes'], v1['mixedSuffixes'], adjs, nouns, v1['words'], v1['caps']):
        gen |= set(pool)
    have_tok = B.tok | B.tok_add | B.names | B.names_add
    promoted = sorted(k for k in {D.key(x) for x in gen} if k in PUB.whole_set and not PUB.dictword(k)
                      and k not in have_tok and not any(b in k for b in B.all_sub()))
    with open(os.path.join(D2, 'blocklist_promoted_token.txt'), 'w', encoding='utf-8') as f:
        f.write('# GENERATED by tools/v2/build_name_data_v2.py (promotion rule, see SOURCES.md): published-list entries (LDNOOBW,\n'
                '# CC BY 4.0) that equal one of our generated tokens and are not ordinary English words. Whole tokens only.\n')
        for k in promoted:
            f.write(k + '\n')
    report['promoted'] = dict(count=len(promoted), sha1=[sha8(k) for k in promoted],
                              dictwordFalseFriends=len([k for k in {D.key(x) for x in gen} if k in PUB.whole_set and PUB.dictword(k)]))
    out = dict(
        version=2,
        cultureOrder=ORDER,
        nativeScript=sorted(SCRIPT),
        cultures={cu: cultures[cu] for cu in ORDER},
        adjectives=adjs, nouns=nouns, caps=v1['caps'], words=v1['words'], invented=inv,
        mixedSuffixes=v1['mixedSuffixes'], mixedTokens={cu: mixed[cu] for cu in ORDER},
        underscoreSuffixes=v1['underscoreSuffixes'], initialsLetters=v1['initialsLetters'],
        blockSubstring=B.all_sub(),
        blockToken=sorted(B.tok | B.tok_add | set(promoted)),
        blockNames=sorted(B.names | B.names_add),
    )
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write('\n')
    with open(os.path.join(D2, 'social_names_v2_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1, sort_keys=True)
    # stdout: counts only (never a stem, a dropped name or a collateral name)
    print(json.dumps(dict(sizes={cu: report['cultures'][cu]['n'] for cu in ORDER}, short=report['short'],
                          blockedDropped={cu: v.get('blockedDropped', 0) for cu, v in report['cultures'].items()
                                          if v.get('blockedDropped')},
                          collateralStems=len(report['collateral']),
                          collateralNames=sum(sum(v.values()) for v in report['collateral'].values()),
                          invented={k: v for k, v in report['invented'].items() if k != 'rootsSha1'},
                          publishedScreen={k: v for k, v in report['publishedScreen'].items() if k != 'files'},
                          promoted={k: v for k, v in report['promoted'].items() if k != 'sha1'}),
                     ensure_ascii=False, indent=0))
    print('wrote', OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
