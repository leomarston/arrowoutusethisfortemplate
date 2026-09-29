"""pubscreen.py — a SECOND, published profanity list used only to SCREEN the v2 name pools at build time and to audit the
names the world shows (tools/v2/build_name_data_v2.py, tools/name_audit.py --v2). The lists are never shipped; the only
derived content in social_names_v2.json is what the builder's promotion rule adds (entries equal to our own generated tokens).

Source: LDNOOBW "List of Dirty, Naughty, Obscene, and Otherwise Bad Words" (github.com/LDNOOBW/List-of-Dirty-Naughty-
Obscene-and-Otherwise-Bad-Words), CC BY 4.0, 24 language files fetched with curl at the commit in
design/social/sources/blocklists/ldnoobw/COMMIT (see design/social/SOURCES.md). The files are read, never printed: every
report of this module is a count or a sha1 prefix.

Rules (built by rule, no hand-picked entry):
  * an entry is used only when it is ONE word (no whitespace) and every character is a letter after key() (NFKD fold +
    lowercase); Latin entries need >= 3 letters, other scripts >= 2 characters;
  * whole(): the whole name, or one of its tokens (names.tokens_of: CamelCase / underscore / digit pieces), EQUALS an entry;
  * inside(): a Latin entry of >= 5 letters occurs anywhere in the name's key (used for procedurally generated handles
    and for the audit; real first names are screened with whole() only, since long entries occur inside real names);
  * dictword(): the entry is an ordinary English word (/usr/share/dict/words, the macOS Web2 list) — a false friend for an
    English-language game (a word that is mild in one language and plain English), reported apart and never promoted.
"""
import os, hashlib, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
FOLDER = os.path.normpath(os.path.join(HERE, '..', '..', 'sources', 'blocklists', 'ldnoobw'))
SKIP = {'LICENSE', 'COMMIT', 'FETCHED'}
DICT = '/usr/share/dict/words'


def sha8(s):
    return hashlib.sha1(s.encode('utf-8')).hexdigest()[:8]


def _is_latin(s):
    return all(unicodedata.name(ch, '').startswith('LATIN') for ch in s if ch.isalpha())


class Published:
    def __init__(self, key, tokens_of, folder=FOLDER):
        self.key = key
        self.tokens_of = tokens_of
        self.files = {}
        self.whole_set = set()
        self.inside_list = []
        self.present = os.path.isdir(folder)
        if not self.present:
            return
        inside = set()
        for name in sorted(os.listdir(folder)):
            if name in SKIP or name.startswith('.'):
                continue
            used = 0
            total = 0
            with open(os.path.join(folder, name), encoding='utf-8') as f:
                for line in f:
                    w = line.strip()
                    if not w:
                        continue
                    total += 1
                    if any(ch.isspace() for ch in w):
                        continue
                    k = key(w)
                    if not k or not all(ch.isalpha() or unicodedata.category(ch).startswith('M') for ch in k):
                        continue
                    latin = _is_latin(k)
                    if len(k) < (3 if latin else 2):
                        continue
                    self.whole_set.add(k)
                    used += 1
                    if latin and len(k) >= 5:
                        inside.add(k)
            self.files[name] = dict(entries=total, used=used)
        self.inside_list = sorted(inside)
        self.english = set()
        if os.path.exists(DICT):
            with open(DICT, encoding='utf-8', errors='ignore') as f:
                self.english = set(w.strip().lower() for w in f)

    def dictword(self, k):
        return k in self.english

    def whole_entry(self, s):
        """The entry (key) a name or one of its tokens equals, or None."""
        k = self.key(s)
        if k in self.whole_set:
            return k
        for t in self.tokens_of(s):
            if t in self.whole_set:
                return t
        return None

    def whole(self, s):
        if not self.whole_set:
            return False
        if self.key(s) in self.whole_set:
            return True
        return any(t in self.whole_set for t in self.tokens_of(s))

    def inside(self, s):
        k = self.key(s)
        return any(e in k for e in self.inside_list)

    def hit(self, s):
        """Screen for a generated handle: whole name / token equality, or a long entry anywhere."""
        return self.whole(s) or self.inside(s)

    def report(self):
        return dict(source='LDNOOBW (CC BY 4.0), build-time screen only, never shipped', present=self.present,
                    languages=len(self.files), entriesUsedWhole=len(self.whole_set), entriesUsedInside=len(self.inside_list),
                    files=self.files)
