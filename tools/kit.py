#!/usr/bin/env python3
"""tools/kit.py - the component kit: a catalog of every takeable piece of the template (docs/guides/KIT.md).

The code stays where it is (apps/<game>/App, Packages/*/Sources, the tools); `kit/` holds one folder per component with a
`component.json` that says which files it owns, what it uses (art slots, sounds, strings, tuning keys, skin colour tokens),
what it depends on and how to open it in a Debug build. This tool reads those folders.

    python3 tools/kit.py list [--category C]            the components (id, category, files, status)
    python3 tools/kit.py search <text>                   match id, title, summary, description, files, uses
    python3 tools/kit.py show <id>                       everything about one component, incl. transitive deps and totals
    python3 tools/kit.py deps <id>                       its dependency tree
    python3 tools/kit.py rdeps <id>                      what depends on it (what breaks if you remove it)
    python3 tools/kit.py export <id>... --out DIR|X.zip [--without ID]...
                                                         copy the files (+ transitive deps), the skin / art / sound / string /
                                                         tuning entries they need, a MANIFEST.md and a CHECKLIST.md
    python3 tools/kit.py add <id>... --game <slug> [--apply]
                                                         what apps/<slug> lacks of those components (dry run by default);
                                                         --apply copies the missing files and merges the missing entries
    python3 tools/kit.py scan <id>|--all [--write] [--prune]
                                                         what the sources of a component use (art, sounds, strings, tuning,
                                                         tokens) and which components they reference; --write adds the
                                                         missing entries to component.json (--prune also drops stale ones)
    python3 tools/kit.py catalog                         write kit/CATALOG.md and kit/catalog.html (generated)
    python3 tools/kit.py check [-v] [--strict]           (CI) schema, references, deps, OWNERSHIP, closure budgets
                                                         (`maxClosure` of stable components), fresh catalog
    python3 tools/kit.py check --selftest                plant failures and prove check catches each one

Ownership: every Swift file under apps/<game>/App, apps/<game>/Packages/*/Sources and apps/<game>/art/ui/code belongs to
exactly one component (or to "core", kit/core/component.json). `files` entries are repo paths or globs (`*`, `?`, `**`).
An explicit path beats a glob: a new Swift file dropped into a folder a component claims with a glob is owned
automatically, and a component may take one file out of another's glob by naming it. Two explicit claims, or no explicit
claim and two glob claims, fail.

Stdlib only. The Swift lexer and the strings loader are the app's own (apps/<game>/tools/skin/skinlib.py,
apps/<game>/tools/strings/build.py), so the kit reads the sources exactly as the skin and strings checks do.
"""
from __future__ import annotations

import argparse
import fnmatch
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import OrderedDict, defaultdict

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
KIT = os.path.join(REPO, "kit")
DEFAULT_GAME = "mazeout"
CATEGORIES = ["screens", "popups", "hud", "meta", "social-events", "economy", "audio", "fx", "board", "puzzle", "tooling"]
CATEGORY_TITLES = {
    "core": "Core", "screens": "Screens", "popups": "Popups", "hud": "HUD", "meta": "Meta (player, onboarding, prompts)",
    "social-events": "Social and events", "economy": "Economy and store", "audio": "Audio", "fx": "Effects",
    "board": "Boards (puzzle views)", "puzzle": "Puzzle modules (rules)", "tooling": "Tooling",
}
STATUSES = ["stable", "needs-work"]
USE_KINDS = ["art", "rigs", "sounds", "cues", "strings", "tuning", "skinTokens"]
REQUIRED = ["id", "title", "category", "summary", "description", "files", "depends", "status"]
OPTIONAL = ["tests", "related", "wires", "uses", "launchArgs", "gaps", "preview", "notes", "maxClosure"]
ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
# Never exported, whatever a component lists (CLAUDE.md "Secrets"); .gitignore'd paths are dropped too.
SECRET_PATTERNS = [".env", ".env.*", "keys/**", "**/keys/**", "machine.env", "**/machine.env", "*.p8", "*.p12", "*.cer",
                   "*.key", "*.mobileprovision", "**/*.p8", "**/*.p12", "**/*.cer", "**/*.key", "**/*.mobileprovision"]
GENERATED_SWIFT = ("SkinColors.generated.swift", "SkinData.generated.swift", "SkinScenes.generated.swift", "UIArt.swift",
                   "GameConfig.generated.swift", "SocialIntlTables.swift")
UI_PREFIXES = ["", "frames.", "text.", "colors.", "gradients.", "shapes.", "anchors."]


# ============================================================================================ small helpers

def rel(p):
    return os.path.relpath(p, REPO).replace(os.sep, "/")


def is_glob(p):
    return any(c in p for c in "*?[")


def glob_re(pattern):
    """Repo-path glob -> regex: `**` any depth (incl. none), `*` / `?` inside one segment."""
    i, out = 0, []
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append(r"(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(r".*")
            i += 2
        elif pattern[i] == "*":
            out.append(r"[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append(r"[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def natural(s):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=OrderedDict)


def json_paths(obj, prefix=""):
    """Every dotted path of a JSON object (intermediate ones too)."""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else k
            out.add(p)
            out |= json_paths(v, p)
    return out


def get_path(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def set_path(obj, dotted, value):
    parts = dotted.split(".")
    cur = obj
    for part in parts[:-1]:
        cur = cur.setdefault(part, OrderedDict())
    cur[parts[-1]] = value


def swift_name(dotted):
    parts = [p for p in dotted.split(".") if p]
    return parts[0] + "".join(p[:1].upper() + p[1:] for p in parts[1:])


# ============================================================================================ the repo's data

class Repo:
    """Everything the kit checks against, read once: the file list, the skin, the manifest, sounds, strings, tuning."""

    def __init__(self, root=REPO, game=DEFAULT_GAME, kit_dir=None):
        self.root = root
        self.game = game
        self.app_rel = f"apps/{game}"
        self.app = os.path.join(root, self.app_rel)
        self.kit = kit_dir or os.path.join(root, "kit")
        self._files = None
        self._lex = {}
        self._helpers = None

    # ---- files
    @property
    def files(self):
        """Repo-relative paths of every file on disk (not .git, not build output)."""
        if self._files is None:
            skip = {".git", "build", "DerivedData", "__pycache__", ".build", ".swiftpm", "node_modules"}
            out = []
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = [d for d in dirnames if d not in skip and not d.endswith(".xcodeproj")]
                for fn in filenames:
                    out.append(rel(os.path.join(dirpath, fn)) if self.root == REPO else
                               os.path.relpath(os.path.join(dirpath, fn), self.root).replace(os.sep, "/"))
            self._files = sorted(out)
        return self._files

    def add_files(self, paths):              # selftest: plant files without touching the disk
        self._files = sorted(set(self.files) | set(paths))

    def expand(self, pattern):
        if not is_glob(pattern):
            return [pattern] if pattern in self._fileset() or os.path.isdir(self.abs(pattern)) else []
        rx = glob_re(pattern)
        return [f for f in self.files if rx.match(f)]

    def _fileset(self):
        if not hasattr(self, "_fs") or self._fs_n != len(self.files):
            self._fs, self._fs_n = set(self.files), len(self.files)
        return self._fs

    def abs(self, p):
        return os.path.join(self.root, p)

    def ownership_roots(self):
        a = self.app_rel
        return [glob_re(f"{a}/App/**/*.swift"), glob_re(f"{a}/Packages/*/Sources/**/*.swift"),
                glob_re(f"{a}/art/ui/code/**/*.swift")]

    def owned_swift(self):
        roots = self.ownership_roots()
        return [f for f in self.files if f.endswith(".swift") and any(r.match(f) for r in roots)]

    # ---- the app's own helpers (lexer, strings loader)
    def helpers(self):
        if self._helpers is None:
            sys.path.insert(0, os.path.join(self.app, "tools", "skin"))
            sys.path.insert(0, os.path.join(self.app, "tools", "strings"))
            try:
                import skinlib  # noqa: E402
                import build as strings_build  # noqa: E402
            finally:
                sys.path.pop(0)
                sys.path.pop(0)
            self._helpers = (skinlib, strings_build)
        return self._helpers

    def lexed(self, path):
        if path not in self._lex:
            skinlib, _ = self.helpers()
            with open(self.abs(path), encoding="utf-8") as f:
                self._lex[path] = skinlib.swift_lex(f.read())
        return self._lex[path]

    # ---- data
    def _cached(self, name, fn):
        if not hasattr(self, "_c"):
            self._c = {}
        if name not in self._c:
            self._c[name] = fn()
        return self._c[name]

    @property
    def art(self):
        return self._cached("art", lambda: load_json(os.path.join(self.app, "skin", "art.json")))

    @property
    def manifest(self):
        return self._cached("manifest", lambda: {e["id"]: e for e in
                                                 load_json(os.path.join(self.app, "art", "MANIFEST.json"))["entries"]})

    @property
    def colors(self):
        return self._cached("colors", lambda: load_json(os.path.join(self.app, "skin", "colors.json")))

    @property
    def token_by_swift(self):
        return self._cached("tok", lambda: {swift_name(t): t for t in self.colors["tokens"]})

    @property
    def uiart_cases(self):
        return self._cached("uiart", lambda: {swift_name(s): s for s in self.art["slots"]})

    @property
    def rig_cases(self):
        return self._cached("rigs", lambda: {swift_name(s): s for s in self.art.get("rigs", {})})

    @property
    def sound_ids(self):
        def parse():
            p = os.path.join(self.app, "App", "Contracts", "AudioContract.swift")
            text = open(p, encoding="utf-8").read()
            m = re.search(r"enum SoundID\b[^{]*\{(.*?)var bus", text, re.S)
            ids = []
            for line in (m.group(1) if m else "").split("\n"):
                line = line.strip()
                if line.startswith("case "):
                    ids += [x.strip() for x in line[5:].split(",") if x.strip()]
            return ids
        return self._cached("sounds", parse)

    @property
    def tuning(self):
        def load():
            d = os.path.join(self.app, "App", "Resources", "Tuning")
            return OrderedDict((fn, load_json(os.path.join(d, fn))) for fn in sorted(os.listdir(d)) if fn.endswith(".json"))
        return self._cached("tuning", load)

    @property
    def tuning_paths(self):
        return self._cached("tpaths", lambda: {fn: json_paths(v) for fn, v in self.tuning.items()})

    @property
    def cues(self):
        return self.tuning.get("audio.json", {}).get("cues", {})

    @property
    def string_rows(self):
        """{key: row} of the shipped strings table (strings.tsv + requests/*.tsv), key = the English text / identifier."""
        def load():
            _, b = self.helpers()
            tsv = os.path.join(self.app, "App", "Resources", "Strings", "strings.tsv")
            req = os.path.join(self.app, "App", "Resources", "Strings", "requests")
            rows, _errors, _notes = b.load_all(tsv, req)
            return OrderedDict((r["en"], r) for r in rows)
        return self._cached("strings", load)

    @property
    def string_canon(self):
        def build():
            _, b = self.helpers()
            out = {}
            for k in self.string_rows:
                out.setdefault(canon_string(b, k), k)
            return out
        return self._cached("scanon", build)

    def slot_files(self, slot):
        mid = self.art["slots"].get(slot)
        f = (self.manifest.get(mid) or {}).get("file") if mid else None
        return [f"{self.app_rel}/{f}"] if f else []

    def rig_folder(self, slot):
        mid = self.art.get("rigs", {}).get(slot)
        f = (self.manifest.get(mid) or {}).get("file") if mid else None
        return f"{self.app_rel}/{f}" if f else None


def canon_string(b, s):
    return b.SPEC_RE.sub("\x00", re.sub(r"\{\w+\}", "\x00", s))


# ============================================================================================ components

class Component:
    def __init__(self, data, path):
        self.data = data
        self.path = path                       # repo-relative component.json
        self.id = data.get("id", "")

    def __getattr__(self, k):
        if k in ("data", "path", "id"):
            raise AttributeError(k)
        return self.data.get(k)

    @property
    def category(self):
        return self.data.get("category", "")

    def uses(self, kind):
        return list((self.data.get("uses") or {}).get(kind, []))

    @property
    def folder(self):
        return os.path.dirname(self.path)


def load_components(repo):
    comps, errors = OrderedDict(), []
    kit = repo.kit
    if not os.path.isdir(kit):
        return comps, [f"{rel(kit)}: missing"]
    for dirpath, dirnames, filenames in os.walk(kit):
        dirnames.sort()
        if "component.json" in filenames:
            p = os.path.join(dirpath, "component.json")
            rp = os.path.relpath(p, repo.root).replace(os.sep, "/")
            try:
                data = load_json(p)
            except (OSError, ValueError) as e:
                errors.append(f"{rp}: unreadable JSON ({e})")
                continue
            c = Component(data, rp)
            if c.id in comps:
                errors.append(f"{rp}: duplicate id {c.id!r} (also {comps[c.id].path})")
                continue
            comps[c.id] = c
    return comps, errors


def closure(comps, ids, without=()):
    """Transitive deps of `ids` (ids included), dependency order (deps first)."""
    seen, order = set(), []

    def visit(i, stack):
        if i in seen or i in without or i not in comps:
            return
        if i in stack:
            return
        stack.add(i)
        for d in comps[i].depends or []:
            visit(d, stack)
        stack.discard(i)
        seen.add(i)
        order.append(i)

    for i in ids:
        visit(i, set())
    return order


def reverse_deps(comps):
    r = defaultdict(set)
    for c in comps.values():
        for d in c.depends or []:
            r[d].add(c.id)
    return r


def own_files(repo, c):
    out = []
    for p in c.files or []:
        out += repo.expand(p)
    return sorted(set(out), key=natural)


def test_files(repo, c):
    out = []
    for p in c.tests or []:
        out += repo.expand(p)
    return sorted(set(out), key=natural)


def ownership(repo, comps):
    """{swift file: owner id}, problems (unowned / double-owned)."""
    explicit, globbed = defaultdict(list), defaultdict(list)
    for c in comps.values():
        for p in c.files or []:
            if is_glob(p):
                for f in repo.expand(p):
                    if f.endswith(".swift"):
                        globbed[f].append(c.id)
            elif p.endswith(".swift"):
                explicit[p].append(c.id)
    owners, problems = {}, []
    for f in repo.owned_swift():
        e, g = sorted(set(explicit.get(f, []))), sorted(set(globbed.get(f, [])))
        if len(e) > 1:
            problems.append(f"{f}: owned by {', '.join(e)} (two explicit claims)")
        elif len(e) == 1:
            owners[f] = e[0]
        elif len(g) > 1:
            problems.append(f"{f}: owned by {', '.join(g)} (two glob claims; name it explicitly in one component)")
        elif len(g) == 1:
            owners[f] = g[0]
        else:
            problems.append(f"{f}: unowned (add it to a component's `files`, or to kit/core/component.json)")
    return owners, problems


def effective_files(repo, comps, c, owners):
    """The files a component really owns: its explicit paths, its globs minus Swift files another component claims."""
    out = []
    for f in own_files(repo, c):
        if f.endswith(".swift") and f in owners and owners[f] != c.id:
            continue
        out.append(f)
    return out


def closure_files(repo, comps, owners, cid, with_core=False):
    """Every file of `cid` and its transitive dependencies (core's excluded unless `with_core`): what an export takes on top
    of a template-derived game (the `maxClosure` budget counts these)."""
    total = set()
    for i in closure(comps, [cid]):
        if i == "core" and not with_core:
            continue
        total |= set(effective_files(repo, comps, comps[i], owners))
    if not with_core and "core" in comps:
        total -= set(effective_files(repo, comps, comps["core"], owners))
    return total


# ============================================================================================ scanning the sources

# Top-level, non-private type declarations only (column 0): nested helper types (`Info`, `Kind`) would be noise.
DECL_RE = re.compile(r"^(?:@[A-Za-z]+(?:\([^)\n]*\))?\s+)*(?:(?:public|internal|package|final|indirect|nonisolated)\s+)*"
                     r"(?:struct|class|enum|protocol|actor|typealias)\s+([A-Z][A-Za-z0-9_]*)", re.M)
IDENT_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Z][A-Za-z0-9_]*")
DOTTED_RE = re.compile(r"^[a-z][A-Za-z0-9]*(?:\.[A-Za-z0-9]+)+$")


def scan_file(repo, path):
    """What one Swift file uses: art slots, rigs, sounds, cues, strings, tuning keys, token prefixes."""
    lx = repo.lexed(path)
    code = lx.code
    out = {k: set() for k in USE_KINDS}
    _, b = repo.helpers()
    # art + rigs: `.caseName` / `UIArt.caseName` / `ArtRig.caseName`, and slot ids spelled as strings
    for m in re.finditer(r"(?:\bUIArt|\bArtRig|(?<![A-Za-z0-9_)\]]))\.([a-z][A-Za-z0-9_]*)\b", code):
        name = m.group(1)
        if name in repo.uiart_cases and not code[max(0, m.start() - 6):m.start()].endswith("ArtRig"):
            out["art"].add(repo.uiart_cases[name])
        if name in repo.rig_cases and not code[max(0, m.start() - 5):m.start()].endswith("UIArt"):
            if code[max(0, m.start() - 6):m.start()].endswith("ArtRig") or "ArtRig" in code:
                out["rigs"].add(repo.rig_cases[name])
    sounds = set(repo.sound_ids)
    for m in re.finditer(r"(?:\bSoundID|(?<![A-Za-z0-9_)\]]))\.([a-z][A-Za-z0-9_]*)\b", code):
        if m.group(1) in sounds:
            out["sounds"].add(m.group(1))
    for m in re.finditer(r"\bSkin\.([a-z][A-Za-z0-9_]*)", code):
        tok = repo.token_by_swift.get(m.group(1))
        if tok:
            out["skinTokens"].add(".".join(tok.split(".")[:2]))
    for (_s, _e, content, interpolated) in lx.strings:
        if interpolated or not content:
            continue
        lit = content
        if lit in repo.art["slots"]:
            out["art"].add(lit)
        if lit in repo.cues:
            out["cues"].add(lit)
        key = lit.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
        ck = canon_string(b, key)
        if re.search(r"[A-Za-z]", key) and ck in repo.string_canon:
            out["strings"].add(repo.string_canon[ck])
        if DOTTED_RE.match(lit):
            for fn, paths in repo.tuning_paths.items():
                if fn == "ui-colors.json":
                    continue
                for pre in (UI_PREFIXES if fn == "ui.json" else [""]):
                    full = pre + lit
                    if full in paths:
                        parts = full.split(".")
                        out["tuning"].add(f"{fn}:{'.'.join(parts[:2]) if len(parts) > 1 else parts[0]}")
    return out


def symbol_index(repo, comps, owners):
    """{type name: component id} for names declared in exactly one component's Swift files."""
    by_name = defaultdict(set)
    for f, cid in owners.items():
        in_package = "/Packages/" in f
        for m in DECL_RE.finditer(repo.lexed(f).code):
            if in_package and not re.search(r"\b(?:public|open|package)\b", m.group(0)):
                continue                       # a package-internal type is invisible to the app
            by_name[m.group(1)].add(cid)
    return {n: next(iter(c)) for n, c in by_name.items() if len(c) == 1}


def referenced_components(repo, files, own_id, index):
    refs = defaultdict(set)
    for f in files:
        if not f.endswith(".swift"):
            continue
        for name in set(IDENT_RE.findall(repo.lexed(f).code)):
            cid = index.get(name)
            if cid and cid != own_id:
                refs[cid].add(name)
    return refs


def scan_component(repo, comps, c, owners, index=None):
    files = [f for f in effective_files(repo, comps, c, owners) if f.endswith(".swift")]
    uses = {k: set() for k in USE_KINDS}
    for f in files:
        if os.path.basename(f) in GENERATED_SWIFT:
            continue
        for k, v in scan_file(repo, f).items():
            uses[k] |= v
    refs = referenced_components(repo, files, c.id, index) if index is not None else {}
    return uses, refs


def hook_sites(repo, comps, owners, index, cid):
    """Where OTHER code names this component's types although it does not depend on it (core, and components that list
    it in `wires`): the registration lines to edit when the component is removed. -> {component: {file: [names]}}"""
    mine = {n for n, c in index.items() if c == cid}
    out = defaultdict(dict)
    if not mine:
        return out
    for f, owner in owners.items():
        if owner == cid or not f.endswith(".swift"):
            continue
        if owner != "core" and cid in closure(comps, [owner]):
            continue
        names = sorted(mine & set(IDENT_RE.findall(repo.lexed(f).code)))
        if names:
            out[owner][f] = names
    return out


# ============================================================================================ validation

def validate(repo, comps, load_errors=(), check_fresh=True, verbose=False, drift=True):
    """-> (errors, warnings). Everything `check` fails on."""
    errors, warnings = list(load_errors), []
    if "core" not in comps:
        errors.append("kit/core/component.json: missing (the files every game has)")
    # ---- schema
    for c in comps.values():
        where = c.path
        for k in REQUIRED:
            if k not in c.data:
                errors.append(f"{where}: missing `{k}`")
        for k in c.data:
            if k not in REQUIRED and k not in OPTIONAL:
                errors.append(f"{where}: unknown key `{k}`")
        if not ID_RE.match(c.id or ""):
            errors.append(f"{where}: id {c.id!r} is not kebab-case")
        cat = c.category
        if c.id == "core":
            if cat != "core" or rel_dir(repo, c) != "kit/core":
                errors.append(f"{where}: core lives at kit/core/component.json with category \"core\"")
        else:
            if cat not in CATEGORIES:
                errors.append(f"{where}: category {cat!r} not one of {', '.join(CATEGORIES)}")
            elif rel_dir(repo, c) != f"kit/{cat}/{c.id}":
                errors.append(f"{where}: must live at kit/{cat}/{c.id}/component.json")
        if c.status not in STATUSES:
            errors.append(f"{where}: status {c.status!r} not one of {', '.join(STATUSES)}")
        if c.status == "needs-work" and not c.gaps:
            errors.append(f"{where}: status needs-work but no `gaps` listed")
        for k in ("summary", "title", "description"):
            v = c.data.get(k)
            if k in c.data and (not isinstance(v, str) or not v.strip()):
                errors.append(f"{where}: `{k}` must be a non-empty string")
        if isinstance(c.summary, str) and "\n" in c.summary:
            errors.append(f"{where}: `summary` is one line")
        mc = c.data.get("maxClosure")
        if mc is not None and (isinstance(mc, bool) or not isinstance(mc, int) or mc < 1):
            errors.append(f"{where}: `maxClosure` must be a whole number ≥ 1 (files with its dependencies, excluding core)")
        for k in ("files", "depends", "wires", "tests", "related", "launchArgs", "gaps", "preview"):
            v = c.data.get(k)
            if v is not None and (not isinstance(v, list) or not all(isinstance(x, str) for x in v)):
                errors.append(f"{where}: `{k}` must be a list of strings")
        uses = c.data.get("uses") or {}
        if not isinstance(uses, dict):
            errors.append(f"{where}: `uses` must be an object")
            uses = {}
        for k, v in uses.items():
            if k not in USE_KINDS:
                errors.append(f"{where}: uses.{k} unknown (one of {', '.join(USE_KINDS)})")
            elif not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                errors.append(f"{where}: uses.{k} must be a list of strings")
        if not os.path.exists(os.path.join(repo.root, c.folder, "README.md")):
            errors.append(f"{c.folder}/README.md: missing (what it is + a usage snippet)")
        for a in c.launchArgs or []:
            if not a.startswith("-pc.") and not a.startswith("python3 ") and not a.startswith("sh "):
                errors.append(f"{where}: launchArgs entry {a!r} must start with -pc. (a Debug launch) or be a command "
                              f"(python3 ... / sh ...)")
    # ---- files
    for c in comps.values():
        for key in ("files", "tests", "related"):
            for p in c.data.get(key) or []:
                if p.startswith("/") or ".." in p.split("/"):
                    errors.append(f"{c.path}: {key} entry {p!r} must be a repo-relative path")
                elif not repo.expand(p):
                    errors.append(f"{c.path}: {key} entry {p!r} matches no file")
                elif secret(p):
                    errors.append(f"{c.path}: {key} entry {p!r} is a secret path (never part of a component)")
        for p in c.preview or []:
            ok_dir = p.startswith(f"{repo.app_rel}/art/") or p.startswith(c.folder + "/preview/")
            if not ok_dir:
                errors.append(f"{c.path}: preview {p!r} must be under {repo.app_rel}/art/ (our own renders) or "
                              f"{c.folder}/preview/")
            elif not os.path.isfile(repo.abs(p)):
                errors.append(f"{c.path}: preview {p!r} does not exist")
    # ---- uses
    slots, rigs = repo.art["slots"], repo.art.get("rigs", {})
    for c in comps.values():
        for s in c.uses("art"):
            if s not in slots:
                errors.append(f"{c.path}: art slot {s!r} not in skin/art.json")
        for s in c.uses("rigs"):
            if s not in rigs:
                errors.append(f"{c.path}: rig slot {s!r} not in skin/art.json rigs")
        for s in c.uses("sounds"):
            if s not in repo.sound_ids:
                errors.append(f"{c.path}: sound {s!r} is not a SoundID case")
            elif not os.path.isfile(os.path.join(repo.app, "App", "Resources", "Sounds", s + ".wav")):
                errors.append(f"{c.path}: sound {s!r} has no App/Resources/Sounds/{s}.wav")
        for s in c.uses("cues"):
            if s not in repo.cues:
                errors.append(f"{c.path}: cue {s!r} not in Tuning/audio.json cues")
        for s in c.uses("strings"):
            if s not in repo.string_rows:
                errors.append(f"{c.path}: string key {s!r} not in strings.tsv")
        for s in c.uses("tuning"):
            fn, _, path = s.partition(":")
            if fn not in repo.tuning:
                errors.append(f"{c.path}: tuning {s!r}: no App/Resources/Tuning/{fn}")
            elif path and path not in repo.tuning_paths[fn]:
                errors.append(f"{c.path}: tuning key {s!r} does not exist")
        toks = repo.colors["tokens"]
        for s in c.uses("skinTokens"):
            if not any(t == s or t.startswith(s + ".") for t in toks):
                errors.append(f"{c.path}: skin token prefix {s!r} matches no token in skin/colors.json")
    # ---- deps
    for c in comps.values():
        for d in c.depends or []:
            if d == c.id:
                errors.append(f"{c.path}: depends on itself")
            elif d not in comps:
                errors.append(f"{c.path}: depends on unknown component {d!r}")
        for w in c.wires or []:
            if w == c.id or w == "core":
                errors.append(f"{c.path}: wires {w!r} (only other components can be wired)")
            elif w not in comps:
                errors.append(f"{c.path}: wires unknown component {w!r}")
            elif w in (c.depends or []):
                errors.append(f"{c.path}: {w!r} is both a dependency and wired (pick one)")
        if c.id != "core" and "core" in comps and "core" not in closure(comps, [c.id]):
            errors.append(f"{c.path}: its dependency closure must reach \"core\"")
    if comps.get("core") and comps["core"].depends:
        errors.append(f"{comps['core'].path}: core depends on nothing")
    for cyc in cycles(comps):
        errors.append("dependency cycle: " + " -> ".join(cyc))
    # ---- ownership
    owners, problems = ownership(repo, comps)
    errors += [f"ownership: {p}" for p in problems]
    # ---- closure budgets: a stable component that declares `maxClosure` must stay within it
    for c in comps.values():
        mc = c.data.get("maxClosure")
        if c.id == "core" or c.status != "stable" or isinstance(mc, bool) or not isinstance(mc, int) or mc < 1:
            continue
        n = len(closure_files(repo, comps, owners, c.id))
        if n > mc:
            errors.append(f"{c.path}: its closure is {n} files (with its dependencies, excluding core) > maxClosure {mc}: a new "
                          f"dependency or file made it heavier (`tools/kit.py deps {c.id}`; cut the coupling, or raise the "
                          f"budget in component.json and say why)")
    # ---- drift (warnings): sources use things a component does not declare / reference undeclared components
    if drift and not any(e.startswith("ownership:") for e in errors):
        index = symbol_index(repo, comps, owners)
        for c in comps.values():
            if c.id == "core":
                continue
            uses, refs = scan_component(repo, comps, c, owners, index)
            for k in USE_KINDS:
                missing = sorted(uses[k] - set(c.uses(k)))
                if missing:
                    warnings.append(f"{c.id}: sources use {k} not declared: {', '.join(missing[:6])}"
                                    + (" ..." if len(missing) > 6 else "") + f"  (tools/kit.py scan {c.id} --write)")
            for w in c.wires or []:
                if w not in refs:
                    warnings.append(f"{c.id}: wires {w} but its sources never name {w}'s types (stale `wires` entry)")
            reach = set(closure(comps, [c.id])) | set(c.wires or [])
            for d, names in sorted(refs.items()):
                if d != "core" and d not in reach:
                    warnings.append(f"{c.id}: references {d} ({', '.join(sorted(names)[:3])}) outside its dependency "
                                    f"closure (a hook or a missing `depends`)")
    # ---- freshness
    if check_fresh:
        md, page = render_catalog(repo, comps)
        for name, text in (("CATALOG.md", md), ("catalog.html", page)):
            p = os.path.join(repo.kit, name)
            cur = open(p, encoding="utf-8").read() if os.path.exists(p) else None
            if cur != text:
                errors.append(f"kit/{name}: stale or missing (run python3 tools/kit.py catalog)")
    return errors, warnings


def rel_dir(repo, c):
    return c.folder


def cycles(comps):
    out, color = [], {}

    def dfs(i, stack):
        color[i] = 1
        stack.append(i)
        for d in comps[i].depends or []:
            if d not in comps:
                continue
            if color.get(d) == 1:
                out.append(stack[stack.index(d):] + [d])
            elif color.get(d) is None:
                dfs(d, stack)
        stack.pop()
        color[i] = 2

    for i in comps:
        if color.get(i) is None:
            dfs(i, [])
    return out


def secret(path):
    base = path.split("/")[-1]
    for pat in SECRET_PATTERNS:
        if "/" in pat:
            if glob_re(pat).match(path):
                return True
        elif fnmatch.fnmatch(base, pat):
            return True
    return "/keys/" in "/" + path


def git_ignored(root, paths):
    if not paths:
        return set()
    try:
        r = subprocess.run(["git", "-C", root, "check-ignore", "--no-index", "--stdin"], input="\n".join(paths),
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.strip() for line in r.stdout.splitlines() if line.strip()}


# ============================================================================================ catalog

def component_summary(repo, comps, owners, rdeps):
    rows = []
    for c in comps.values():
        own = effective_files(repo, comps, c, owners)
        cl = closure(comps, [c.id])
        total = set()
        for i in cl:
            total |= set(effective_files(repo, comps, comps[i], owners))
        core_files = set(effective_files(repo, comps, comps["core"], owners)) if "core" in comps else set()
        prev = list(c.preview or [])
        if not prev:
            for s in c.uses("art"):
                for f in repo.slot_files(s):
                    if f.endswith(".png") and os.path.isfile(repo.abs(f)) and f not in prev:
                        prev.append(f)
                if len(prev) >= 3:
                    break
        rows.append({
            "id": c.id, "title": c.title, "category": c.category, "summary": c.summary,
            "description": c.description, "status": c.status, "gaps": c.gaps or [],
            "files": len(own), "swift": sum(1 for f in own if f.endswith(".swift")),
            "totalFiles": len(total), "noCore": len(total - core_files) if c.id != "core" else len(own),
            "depends": list(c.depends or []), "wires": list(c.wires or []),
            "closure": [i for i in cl if i != c.id], "rdeps": sorted(rdeps.get(c.id, [])),
            "launchArgs": c.launchArgs or [], "tests": len(test_files(repo, c)),
            "uses": {k: len(c.uses(k)) for k in USE_KINDS},
            "preview": ["../" + p for p in prev[:3]],
            "fileList": own,
        })
    return rows


def render_catalog(repo, comps):
    owners, _ = ownership(repo, comps)
    rdeps = reverse_deps(comps)
    rows = component_summary(repo, comps, owners, rdeps)
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    # ---- markdown
    md = ["# Component kit catalog", "",
          "GENERATED by `python3 tools/kit.py catalog` from `kit/**/component.json`. Do not edit; edit a component.json and",
          "re-run. How to take a piece: `kit/README.md`, `docs/guides/KIT.md`. Browsable page: `kit/catalog.html`.", "",
          f"{len(rows)} components ({sum(1 for r in rows if r['status'] == 'stable')} stable, "
          f"{sum(1 for r in rows if r['status'] == 'needs-work')} needs-work).", "",
          "Files = the component's own files (Swift, data, tools); + deps = own + every transitive dependency's, "
          "core excluded (a template-derived game has core). Deps: `python3 tools/kit.py deps <id>`.", ""]
    for cat in ["core"] + CATEGORIES:
        items = sorted(by_cat.get(cat, []), key=lambda r: r["id"])
        if not items:
            continue
        md += [f"## {CATEGORY_TITLES[cat]}", "", "| id | title | summary | files | + deps | depends | status |",
               "|---|---|---|---|---|---|---|"]
        for r in items:
            st = r["status"] + (" ⚠" if r["status"] == "needs-work" else "")
            md.append(f"| `{r['id']}` | {esc_md(r['title'])} | {esc_md(r['summary'])} | {r['files']} | {r['noCore']} | "
                      f"{', '.join(d for d in r['depends'] if d != 'core') or '-'} | {st} |")
        md.append("")
    md_text = "\n".join(md).rstrip() + "\n"
    # ---- html
    data = [{k: v for k, v in r.items()} for r in sorted(rows, key=lambda r: (cat_order(r["category"]), r["id"]))]
    page = HTML_TEMPLATE.replace("/*DATA*/", json.dumps(data, ensure_ascii=False, separators=(",", ":"))
                                 .replace("</", "<\\/")) \
        .replace("/*CATS*/", json.dumps([[c, CATEGORY_TITLES[c]] for c in ["core"] + CATEGORIES], ensure_ascii=False))
    return md_text, page


def cat_order(c):
    return (["core"] + CATEGORIES).index(c) if c in (["core"] + CATEGORIES) else 99


def esc_md(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Component Kit</title>
<!-- GENERATED by python3 tools/kit.py catalog from kit/**/component.json. Do not edit. -->
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1b1f24;--mute:#5b6470;--line:#dde1e6;--acc:#1f6feb;--warn:#b35900;--ok:#1a7f37;--chip:#eef1f5}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1216;--card:#171b21;--ink:#e6e9ee;--mute:#98a2ae;--line:#2a3039;--acc:#58a6ff;--warn:#f0a44b;--ok:#3fb950;--chip:#212731}}
:root[data-theme="dark"]{--bg:#0f1216;--card:#171b21;--ink:#e6e9ee;--mute:#98a2ae;--line:#2a3039;--acc:#58a6ff;--warn:#f0a44b;--ok:#3fb950;--chip:#212731}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--bg);border-bottom:1px solid var(--line);padding:12px 16px}
h1{font-size:18px;margin:0 0 8px}
#q{width:100%;max-width:520px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font-size:15px}
.cats{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.cats button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:3px 10px;cursor:pointer;font-size:13px}
.cats button.on{background:var(--acc);border-color:var(--acc);color:#fff}
main{padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;min-width:0;cursor:pointer}
.card:hover{border-color:var(--acc)}
.card h2{font-size:15px;margin:0 0 2px}
.id{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--mute);font-size:12px}
.sum{margin:6px 0}
.meta{display:flex;flex-wrap:wrap;gap:4px;font-size:12px}
.chip{background:var(--chip);border-radius:6px;padding:1px 6px}
.st-stable{color:var(--ok)} .st-needs-work{color:var(--warn)}
.thumbs{display:flex;gap:6px;margin:8px 0 0;height:56px}
.thumbs img{height:56px;max-width:90px;object-fit:contain;background:var(--chip);border-radius:6px}
#detail{position:fixed;inset:0;background:rgba(0,0,0,.45);display:none;z-index:5;padding:16px;overflow:auto}
#detail .panel{background:var(--card);border-radius:12px;max-width:860px;margin:0 auto;padding:16px;border:1px solid var(--line)}
#detail pre{background:var(--chip);padding:8px;border-radius:6px;overflow-x:auto;white-space:pre-wrap;word-break:break-all}
#detail ul{padding-left:18px;margin:4px 0}
#detail .files{max-height:220px;overflow:auto;font-family:ui-monospace,Menlo,monospace;font-size:12px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
button.copy,button.close{border:1px solid var(--line);background:var(--chip);color:var(--ink);border-radius:6px;padding:4px 10px;cursor:pointer}
svg text{fill:var(--ink);font:11px ui-monospace,Menlo,monospace}
svg .edge{stroke:var(--mute);fill:none;stroke-width:1}
svg .node rect{fill:var(--chip);stroke:var(--line)}
svg .node.me rect{fill:var(--acc)} svg .node.me text{fill:#fff}
.graph{overflow-x:auto}
@media (max-width:600px){main{grid-template-columns:1fr;padding:12px}}
</style>
</head>
<body>
<header>
<h1>Component Kit</h1>
<input id="q" type="search" placeholder="Search components, files, strings, art slots..." autocomplete="off">
<div class="cats" id="cats"></div>
</header>
<main id="grid"></main>
<div id="detail" role="dialog" aria-modal="true"><div class="panel" id="panel"></div></div>
<script>
const DATA=/*DATA*/;
const CATS=/*CATS*/;
const byId=Object.fromEntries(DATA.map(c=>[c.id,c]));
let cat="all";
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function cats(){const el=document.getElementById("cats");const all=[["all","All"]].concat(CATS.filter(([c])=>DATA.some(d=>d.category===c)));
el.innerHTML=all.map(([c,t])=>`<button data-c="${c}" class="${c===cat?"on":""}">${esc(t)} ${c==="all"?DATA.length:DATA.filter(d=>d.category===c).length}</button>`).join("");
el.querySelectorAll("button").forEach(b=>b.onclick=()=>{cat=b.dataset.c;cats();render();});}
function hay(c){return [c.id,c.title,c.summary,c.description,c.category,c.fileList.join(" "),c.depends.join(" ")].join(" ").toLowerCase();}
function render(){const q=document.getElementById("q").value.trim().toLowerCase();
const items=DATA.filter(c=>(cat==="all"||c.category===cat)&&(!q||q.split(/\s+/).every(w=>hay(c).includes(w))));
document.getElementById("grid").innerHTML=items.map(c=>`<div class="card" data-id="${c.id}" tabindex="0">
<h2>${esc(c.title)}</h2><div class="id">${esc(c.id)} · ${esc(c.category)}</div><div class="sum">${esc(c.summary)}</div>
<div class="meta"><span class="chip st-${c.status}">${c.status}</span><span class="chip">${c.files} files</span><span class="chip">${c.noCore} with deps</span>${c.depends.filter(d=>d!=="core").map(d=>`<span class="chip">→ ${esc(d)}</span>`).join("")}</div>
${c.preview.length?`<div class="thumbs">${c.preview.map(p=>`<img loading="lazy" src="${esc(p)}" alt="">`).join("")}</div>`:""}</div>`).join("")||"<p>No component matches.</p>";
document.querySelectorAll(".card").forEach(el=>{el.onclick=()=>open(el.dataset.id);el.onkeydown=e=>{if(e.key==="Enter")open(el.dataset.id)};});}
function tree(id,depth,seen){const c=byId[id];if(!c)return "";const kids=c.depends.map(d=>seen.has(d)?"  ".repeat(depth+1)+d+" (above)\n":(seen.add(d),"  ".repeat(depth+1)+d+"\n"+tree(d,depth+1,seen))).join("");return kids;}
function graph(c){const nodes=[c.id].concat(c.closure.filter(i=>i!==c.id));const lvl={};const L=i=>{if(lvl[i]!==undefined)return lvl[i];const d=(byId[i]||{depends:[]}).depends;lvl[i]=0;lvl[i]=d.length?1+Math.max(...d.map(L)):0;return lvl[i];};
nodes.forEach(L);const cols={};nodes.forEach(n=>{(cols[lvl[n]]=cols[lvl[n]]||[]).push(n);});const maxL=Math.max(...nodes.map(n=>lvl[n]));const W=150,H=26,pos={};
Object.entries(cols).forEach(([l,ns])=>ns.sort().forEach((n,k)=>pos[n]=[(maxL-l)*W+4,k*(H+8)+4]));
const h=Math.max(...Object.values(cols).map(ns=>ns.length))*(H+8)+8,w=(maxL+1)*W;
let s=`<svg width="${w}" height="${h}" role="img" aria-label="dependency graph">`;
nodes.forEach(n=>(byId[n]||{depends:[]}).depends.forEach(d=>{if(!pos[d])return;const[a,b]=pos[n],[x,y]=pos[d];s+=`<path class="edge" d="M${a+W-14},${b+H/2} C${a+W},${b+H/2} ${x-10},${y+H/2} ${x},${y+H/2}"/>`;}));
nodes.forEach(n=>{const[x,y]=pos[n];s+=`<g class="node${n===c.id?" me":""}"><rect x="${x}" y="${y}" width="${W-18}" height="${H}" rx="5"/><text x="${x+6}" y="${y+17}">${esc(n.length>18?n.slice(0,17)+"…":n)}</text></g>`;});
return s+"</svg>";}
function open(id){const c=byId[id];const cmd=`python3 tools/kit.py export ${c.id} --out /tmp/${c.id}-kit`;
const u=Object.entries(c.uses).filter(([k,v])=>v).map(([k,v])=>`${k} ${v}`).join(" · ")||"none";
document.getElementById("panel").innerHTML=`<div class="row" style="justify-content:space-between"><h2 style="margin:0">${esc(c.title)} <span class="id">${esc(c.id)}</span></h2><button class="close" id="x">Close</button></div>
<p>${esc(c.description)}</p>
<div class="meta"><span class="chip st-${c.status}">${c.status}</span><span class="chip">${esc(c.category)}</span><span class="chip">${c.files} own files (${c.swift} Swift)</span><span class="chip">${c.noCore} with deps (excl. core)</span><span class="chip">${c.totalFiles} incl. core</span><span class="chip">${c.tests} test files</span></div>
${c.gaps.length?`<h3>Known gaps</h3><ul>${c.gaps.map(g=>`<li>${esc(g)}</li>`).join("")}</ul>`:""}
<h3>Take it</h3><div class="row"><pre style="flex:1;margin:0">${esc(cmd)}</pre><button class="copy" id="cp">Copy</button></div>
<p class="id">Details, deps tree and everything it uses: python3 tools/kit.py show ${esc(c.id)} · kit/${c.id==="core"?"core":esc(c.category)+"/"+esc(c.id)}/README.md</p>
${c.launchArgs.length?`<h3>Open it (Debug build)</h3><pre>${c.launchArgs.map(esc).join("\n")}</pre>`:""}
<h3>Uses</h3><p>${esc(u)}</p>
<h3>Depends on</h3>${c.closure.length?`<div class="graph">${graph(c)}</div><pre>${esc(c.id+"\n"+tree(c.id,0,new Set()))}</pre>`:"<p>nothing (the root)</p>"}
<h3>Used by</h3><p>${c.rdeps.length?c.rdeps.map(esc).join(", "):"nothing"}</p>
${c.wires.length?`<h3>Wires in</h3><p>${c.wires.map(esc).join(", ")} <span class="id">(named only to register / present them)</span></p>`:""}
${c.preview.length?`<div class="thumbs" style="height:96px">${c.preview.map(p=>`<img src="${esc(p)}" style="height:96px;max-width:160px" alt="">`).join("")}</div>`:""}
<h3>Files</h3><div class="files">${c.fileList.map(esc).join("<br>")}</div>`;
const d=document.getElementById("detail");d.style.display="block";
document.getElementById("x").onclick=()=>d.style.display="none";
document.getElementById("cp").onclick=()=>{navigator.clipboard&&navigator.clipboard.writeText(cmd);document.getElementById("cp").textContent="Copied";};}
document.getElementById("detail").onclick=e=>{if(e.target.id==="detail")e.target.style.display="none";};
document.addEventListener("keydown",e=>{if(e.key==="Escape")document.getElementById("detail").style.display="none";});
document.getElementById("q").oninput=render;
cats();render();
</script>
</body>
</html>
"""


# ============================================================================================ export / add

def gather(repo, comps, ids, without=()):
    owners, _ = ownership(repo, comps)
    order = closure(comps, ids, set(without))
    files, tests, uses = [], [], {k: set() for k in USE_KINDS}
    for i in order:
        c = comps[i]
        files += effective_files(repo, comps, c, owners)
        tests += test_files(repo, c)
        for k in USE_KINDS:
            uses[k] |= set(c.uses(k))
    # cues -> their sounds
    for cue in uses["cues"]:
        s = repo.cues.get(cue)
        if s:
            uses["sounds"].add(s)
    return order, sorted(set(files), key=natural), sorted(set(tests) - set(files), key=natural), uses


def asset_files(repo, uses):
    out = []
    for s in sorted(uses["art"]):
        out += [f for f in repo.slot_files(s) if os.path.exists(repo.abs(f))]
    for s in sorted(uses["rigs"]):
        folder = repo.rig_folder(s)
        if folder:
            out += [f for f in repo.files if f.startswith(folder + "/")]
    for s in sorted(uses["sounds"]):
        p = f"{repo.app_rel}/App/Resources/Sounds/{s}.wav"
        if os.path.exists(repo.abs(p)):
            out.append(p)
    return sorted(set(out), key=natural)


def tuning_subset(repo, uses):
    out = OrderedDict()
    for t in sorted(uses["tuning"]):
        fn, _, path = t.partition(":")
        if fn not in repo.tuning:
            continue
        dst = out.setdefault(fn, OrderedDict())
        if not path:
            out[fn] = repo.tuning[fn]
            continue
        v, ok = get_path(repo.tuning[fn], path)
        if ok:
            set_path(dst, path, v)
    return out


def ui_colour_refs(obj):
    refs = set()
    if isinstance(obj, dict):
        for v in obj.values():
            refs |= ui_colour_refs(v)
    elif isinstance(obj, list):
        for v in obj:
            refs |= ui_colour_refs(v)
    elif isinstance(obj, str) and obj.startswith("@"):
        refs.add(obj[1:])
    return refs


def colours_subset(repo, uses, tuning):
    col = repo.colors
    toks = OrderedDict((t, v) for t, v in col["tokens"].items()
                       if any(t == p or t.startswith(p + ".") for p in uses["skinTokens"]))
    ui_ids = ui_colour_refs(tuning.get("ui.json", {}))
    ui = OrderedDict((k, v) for k, v in col.get("ui", {}).items() if k in ui_ids)
    names = set(toks.values()) | set(ui.values())
    pal = OrderedDict((k, v) for k, v in col["palette"].items() if k in names)
    return OrderedDict([("about", "kit export: the subset of skin/colors.json these components draw"), ("palette", pal),
                        ("tokens", toks), ("ui", ui)])


def string_lines(repo, keys):
    """{relative table path: [header, rows...]} of the raw TSV lines whose key is in `keys`."""
    _, b = repo.helpers()
    base = os.path.join(repo.app, "App", "Resources", "Strings")
    out = OrderedDict()
    tables = [("strings.tsv", 0)] + [(f"l10n/{fn}", 0) for fn in sorted(os.listdir(os.path.join(base, "l10n")))
                                     if fn.endswith(".tsv")] + [("keys.tsv", 0)]
    for name, col in tables:
        p = os.path.join(base, name)
        if not os.path.exists(p):
            continue
        lines = open(p, encoding="utf-8").read().split("\n")
        keep = [lines[0]]
        for line in lines[1:]:
            if not line.strip() or line.startswith("#"):
                continue
            k = b.unescape(line.split("\t")[col])
            if k in keys:
                keep.append(line)
        if len(keep) > 1:
            out[name] = keep
    return out


def audio_subset(repo, uses):
    a = repo.tuning.get("audio.json", {})
    return OrderedDict([("cues", OrderedDict((k, v) for k, v in a.get("cues", {}).items() if k in uses["cues"])),
                        ("gain", OrderedDict((k, v) for k, v in a.get("gain", {}).items() if k in uses["sounds"]))])


def export(repo, comps, ids, out, without=(), quiet=False):
    for i in ids:
        if i not in comps:
            raise SystemExit(f"unknown component {i!r} (python3 tools/kit.py list)")
    order, files, tests, uses = gather(repo, comps, ids, without)
    assets = asset_files(repo, uses)
    kit_docs = []
    for i in order:
        folder = comps[i].folder
        kit_docs += [f"{folder}/component.json", f"{folder}/README.md"]
    wanted = sorted(set(files + tests + assets + kit_docs), key=natural)
    ignored = git_ignored(repo.root, wanted)
    skipped = [p for p in wanted if secret(p) or p in ignored]
    wanted = [p for p in wanted if p not in skipped and os.path.isfile(repo.abs(p))]
    tuning = tuning_subset(repo, uses)
    colours = colours_subset(repo, uses, tuning)
    strings = string_lines(repo, uses["strings"])
    art = OrderedDict([("about", "kit export: the skin/art.json slots these components draw (slot -> art/MANIFEST.json id)"),
                       ("slots", OrderedDict((s, repo.art["slots"][s]) for s in sorted(uses["art"]) if s in repo.art["slots"])),
                       ("rigs", OrderedDict((s, repo.art["rigs"][s]) for s in sorted(uses["rigs"])
                                            if s in repo.art.get("rigs", {})))])
    manifest_ids = set(art["slots"].values()) | set(art["rigs"].values())
    man = [repo.manifest[m] for m in sorted(manifest_ids) if m in repo.manifest]
    data = OrderedDict()
    data["data/skin/art.json"] = dumps(art)
    data["data/skin/colors.json"] = dumps(colours)
    data["data/art/MANIFEST.entries.json"] = dumps(man)
    for fn, sub in tuning.items():
        data[f"data/tuning/{fn}"] = dumps(sub)
    if uses["sounds"] or uses["cues"]:
        data["data/tuning/audio.cues.json"] = dumps(audio_subset(repo, uses))
    for name, lines in strings.items():
        data[f"data/strings/{name}"] = "\n".join(lines) + "\n"
    without_here = [w for w in without if w in comps]
    manifest_md = render_manifest(repo, comps, ids, order, files, tests, assets, uses, skipped, without_here)
    owners, _ = ownership(repo, comps)
    index = symbol_index(repo, comps, owners)
    hooks = {i: hook_sites(repo, comps, owners, index, i) for i in order if i != "core"}
    checklist = render_checklist(repo, comps, ids, order, uses, without_here, tuning, hooks, set(files))
    kitjson = dumps(OrderedDict([("components", ids), ("closure", order), ("without", without_here), ("game", repo.game),
                                 ("files", files), ("tests", tests), ("assets", assets),
                                 ("uses", OrderedDict((k, sorted(v)) for k, v in uses.items())), ("skipped", skipped)]))
    extra = OrderedDict([("MANIFEST.md", manifest_md), ("CHECKLIST.md", checklist), ("kit.json", kitjson)])
    extra.update(data)
    if out.endswith(".zip"):
        os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for p in wanted:
                z.write(repo.abs(p), "files/" + p)
            for name, text in extra.items():
                z.writestr(name, text)
    else:
        if os.path.exists(out) and os.listdir(out):
            raise SystemExit(f"{out}: exists and is not empty (pick a new folder)")
        for p in wanted:
            dst = os.path.join(out, "files", p)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(repo.abs(p), dst)
        for name, text in extra.items():
            dst = os.path.join(out, name)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(text)
    if not quiet:
        print(f"exported {', '.join(ids)} (+ {len(order) - len(ids)} deps: {', '.join(i for i in order if i not in ids)})")
        print(f"  {len(files)} files, {len(tests)} tests, {len(assets)} art/sound files, {len(data)} data subsets -> {out}")
        if skipped:
            print(f"  skipped (secret / git-ignored): {len(skipped)}")
        print(f"  read {out}{'/' if not out.endswith('.zip') else ':'}MANIFEST.md and CHECKLIST.md")
    return {"order": order, "files": files, "tests": tests, "assets": assets, "skipped": skipped, "data": list(data)}


def dumps(obj):
    return json.dumps(obj, indent=1, ensure_ascii=False) + "\n"


def render_manifest(repo, comps, ids, order, files, tests, assets, uses, skipped, without):
    L = [f"# Kit export: {', '.join(ids)}", "",
         f"Generated by `python3 tools/kit.py export {' '.join(ids)}` from the {repo.game} reference game "
         f"(`{repo.app_rel}`). Paths under `files/` are repo paths.", "",
         "## Components (dependency order: deps first)", "", "| id | title | category | status | summary |", "|---|---|---|---|---|"]
    for i in order:
        c = comps[i]
        L.append(f"| `{i}` | {esc_md(c.title)} | {c.category} | {c.status} | {esc_md(c.summary)} |")
    if without:
        L += ["", f"Left out on request (`--without`): {', '.join(without)} - the target must provide them (CHECKLIST.md)."]
    gaps = [(i, g) for i in order for g in (comps[i].gaps or [])]
    if gaps:
        L += ["", "## Known gaps", ""] + [f"- `{i}`: {g}" for i, g in gaps]
    L += ["", f"## Files ({len(files)})", ""] + [f"- `{f}`" for f in files]
    if tests:
        L += ["", f"## Tests ({len(tests)})", ""] + [f"- `{f}`" for f in tests]
    if assets:
        L += ["", f"## Art and sound files ({len(assets)})", "",
              "Our own renders and synthesised sounds (never an original game's). Slot ids are in `data/skin/art.json`.", ""] + \
             [f"- `{f}`" for f in assets]
    L += ["", "## Data subsets (`data/`)", "",
          "- `skin/art.json` - the art slots + rig slots used, `art/MANIFEST.entries.json` their manifest entries",
          "- `skin/colors.json` - the colour tokens (by prefix), the ui.json colour ids and the palette entries they name",
          "- `tuning/<file>.json` - only the tuning keys used (merge into `App/Resources/Tuning/<file>.json`)",
          "- `strings/` - the rows of strings.tsv, each l10n table and keys.tsv for the string keys used",
          "", "## What it uses", ""]
    for k in USE_KINDS:
        v = sorted(uses[k])
        if v:
            L.append(f"- **{k}** ({len(v)}): " + ", ".join(f"`{x}`" for x in v[:60]) + (" ..." if len(v) > 60 else ""))
    if skipped:
        L += ["", "## Skipped (secret or git-ignored, never exported)", ""] + [f"- `{f}`" for f in skipped]
    return "\n".join(L) + "\n"


def render_checklist(repo, comps, ids, order, uses, without, tuning, hooks=None, exported=()):
    L = [f"# Checklist: what the target project must provide for {', '.join(ids)}", "",
         "Tick each line in the target. Most template-derived games already have all of it: use "
         "`python3 tools/kit.py add <ids> --game <slug>` there instead, it reports only what is missing.", ""]
    if without:
        L += ["## Components left out (the target must already have them)", ""] + \
             [f"- [ ] `{w}` - {comps[w].summary}" for w in without] + [""]
    L += ["## Code", "",
          "- [ ] The Swift files under `files/` compiled into the app target (App/..., art/ui/code) or the Swift package "
          "(Packages/.../Sources: the target named by the folder).",
          "- [ ] `core`'s contracts: `AppModel` (services: popups, router, toasts, fx, audio, haptics, store, tuning), "
          "`PopupHost`/`PopupRequest`, `Router`/`Screen`, `Tokens`/`GameText`, `ArtStore`/`UIArt`, `PlayerStore`, `Log`, "
          "`LaunchArgs`." if "core" not in without and "core" in order else
          "- [ ] The target's own core (AppModel services, PopupHost, Router, Tokens/GameText, ArtStore/UIArt, PlayerStore).",
          ]
    wiring, came = [], 0
    for i in order:
        for owner, fs in sorted((hooks or {}).get(i, {}).items()):
            for f, names in sorted(fs.items()):
                if f in exported:
                    came += 1
                    continue
                wiring.append(f"- [ ] `{i}` is named by `{f}` ({owner}: {', '.join(names[:5])}), which is not in this "
                              "export: the target needs the equivalent line (or drop it if the target lacks that piece)")
        for n in comps[i].notes or []:
            wiring.append(f"- [ ] `{i}`: {n}")
    if wiring or came:
        L += ["", "## Wiring (where other code registers / presents these components)", "",
              f"{came} registration lines are in files of this export (kept as they are). "
              "`python3 tools/kit.py rdeps <id>` lists them all.", ""] + wiring
    L += ["", "## Data", ""]
    if uses["art"] or uses["rigs"]:
        L.append(f"- [ ] {len(uses['art'])} art slots + {len(uses['rigs'])} rig slots in `skin/art.json` "
                 "(`data/skin/art.json`), their files in art/ (`files/`), then `python3 tools/skin/art.py` (regenerates UIArt.swift).")
    if uses["skinTokens"]:
        L.append(f"- [ ] colour tokens under {', '.join(sorted(uses['skinTokens']))} in `skin/colors.json` "
                 "(`data/skin/colors.json`), then `python3 tools/skin/build.py` (regenerates SkinColors.generated.swift).")
    if tuning:
        L.append("- [ ] tuning keys merged into `App/Resources/Tuning/`: " + ", ".join(
            f"{fn} ({len([t for t in uses['tuning'] if t.startswith(fn + ':')])} keys)" for fn in tuning))
    if uses["strings"]:
        L.append(f"- [ ] {len(uses['strings'])} string rows in `App/Resources/Strings/strings.tsv` + every l10n table "
                 "(`data/strings/`), then `python3 tools/strings/build.py`.")
    if uses["sounds"] or uses["cues"]:
        L.append(f"- [ ] sounds {', '.join(sorted(uses['sounds']))} as `SoundID` cases + `App/Resources/Sounds/<id>.wav`; "
                 f"cues {', '.join(sorted(uses['cues'])) or '-'} in `Tuning/audio.json` (`data/tuning/audio.cues.json`).")
    L += ["", "## Verify", "",
          "- [ ] the target's content checks: skin `build.py --check`, `art.py --check`, strings `build.py --check`",
          "- [ ] a Debug build, then open each component with its launch arguments:"]
    for i in order:
        for a in comps[i].launchArgs or []:
            L.append(f"  - `{i}`: `{a}`")
    L += ["- [ ] the listed tests (`files/.../Tests`) pass in the target", ""]
    return "\n".join(L)


def add(repo, comps, ids, slug, apply=False, source_game=None):
    source_game = source_game or repo.game
    target_rel = f"apps/{slug}"
    target = repo.abs(target_rel)
    if not os.path.isdir(target):
        raise SystemExit(f"{target_rel}: no such game (python3 tools/game.py new {slug} ...)")
    if slug == source_game:
        raise SystemExit(f"{target_rel} is the source game itself: nothing to add")
    order, files, tests, uses = gather(repo, comps, ids)
    assets = asset_files(repo, uses)
    plan = []                                  # (action, detail, src, dst)
    src_prefix = repo.app_rel + "/"

    def map_path(p):
        return target_rel + "/" + p[len(src_prefix):] if p.startswith(src_prefix) else None

    ignored = git_ignored(repo.root, files + tests + assets)
    for p in files + tests + assets:
        if secret(p) or p in ignored:
            continue
        d = map_path(p)
        if d is None:
            plan.append(("shared", p, p, p))             # repo-level (tools/, docs): every game shares it
            continue
        if not os.path.exists(repo.abs(d)):
            plan.append(("copy", d, p, d))
        elif not same_file(repo.abs(p), repo.abs(d)):
            plan.append(("differs", d, p, d))           # never overwritten
        else:
            plan.append(("same", d, p, d))
    # data entries
    tgt = Repo(repo.root, slug)
    try:
        t_art = tgt.art
    except OSError:
        t_art = {"slots": {}, "rigs": {}}
    for s in sorted(uses["art"]):
        if s not in t_art.get("slots", {}):
            plan.append(("add-entry", f"skin/art.json slots.{s} = {repo.art['slots'][s]}", "art.slots", s))
    for s in sorted(uses["rigs"]):
        if s not in t_art.get("rigs", {}):
            plan.append(("add-entry", f"skin/art.json rigs.{s} = {repo.art['rigs'][s]}", "art.rigs", s))
    try:
        t_tokens = tgt.colors["tokens"]
    except OSError:
        t_tokens = {}
    for pre in sorted(uses["skinTokens"]):
        missing = [t for t in repo.colors["tokens"] if (t == pre or t.startswith(pre + ".")) and t not in t_tokens]
        if missing:
            plan.append(("add-entry", f"skin/colors.json tokens {pre}.* ({len(missing)} tokens)", "colors.tokens", pre))
    try:
        t_tuning = tgt.tuning
    except OSError:
        t_tuning = {}
    for t in sorted(uses["tuning"]):
        fn, _, path = t.partition(":")
        if fn not in t_tuning or (path and not get_path(t_tuning[fn], path)[1]):
            plan.append(("add-entry", f"Tuning/{fn} {path}", "tuning", t))
    try:
        t_rows = tgt.string_rows
    except (OSError, SystemExit):
        t_rows = {}
    miss_str = [s for s in sorted(uses["strings"]) if s not in t_rows]
    if miss_str:
        plan.append(("add-entry", f"strings.tsv + l10n: {len(miss_str)} rows", "strings", miss_str))
    t_cues = t_tuning.get("audio.json", {}).get("cues", {}) if t_tuning else {}
    for cue in sorted(uses["cues"]):
        if cue not in t_cues:
            plan.append(("add-entry", f"Tuning/audio.json cues.{cue}", "tuning", f"audio.json:cues.{cue}"))
    # report
    counts = defaultdict(int)
    for a, *_ in plan:
        counts[a] += 1
    print(f"add {', '.join(ids)} (closure: {', '.join(order)}) -> {target_rel}   "
          f"[{'APPLY' if apply else 'dry run: nothing written; pass --apply'}]")
    labels = {"copy": "COPY (missing in the target)", "differs": "DIFFERS (kept as is; merge by hand if wanted)",
              "same": "present, identical", "shared": "repo-level, shared by every game", "add-entry": "ADD data entry"}
    for a in ("copy", "add-entry", "differs"):
        items = [x for x in plan if x[0] == a]
        if items:
            print(f"\n{labels[a]}: {len(items)}")
            for _, detail, *_ in items:
                print(f"  {detail}")
    print(f"\n{counts['same']} files already present and identical, {counts['shared']} repo-level files shared.")
    if not any(a in ("copy", "add-entry") for a, *_ in plan):
        print("Nothing to add: the game already has every piece.")
        return plan
    if not apply:
        return plan
    pending = OrderedDict()
    for a, detail, src, dst in plan:
        if a == "copy":
            os.makedirs(os.path.dirname(repo.abs(dst)), exist_ok=True)
            shutil.copy2(repo.abs(src), repo.abs(dst))
    pending_entries = [x for x in plan if x[0] == "add-entry"]
    merged = apply_entries(repo, tgt, pending_entries, uses, pending)
    if pending:
        p = os.path.join(target, "kit-pending.json")
        with open(p, "w", encoding="utf-8") as f:
            f.write(dumps(pending))
        print(f"\nCould not merge {len(pending)} entries without reformatting their file: wrote {rel(p)}; merge by hand.")
    print(f"\nApplied: {counts['copy']} files copied, {merged} entries merged. Then, in {target_rel}: "
          "python3 tools/skin/build.py; python3 tools/skin/art.py; python3 tools/strings/build.py; "
          "python3 ../../tools/game.py doctor --game " + slug)
    return plan


def same_file(a, b):
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() == fb.read()
    except OSError:
        return False


def _json_rewrite(path, mutate, pending, label):
    """Mutate a JSON file only if it round-trips byte for byte through json.dumps (so we never reformat it)."""
    text = open(path, encoding="utf-8").read()
    obj = json.loads(text, object_pairs_hook=OrderedDict)
    for indent in (1, 2, 4, None):
        if json.dumps(obj, indent=indent, ensure_ascii=False) + "\n" == text:
            break
    else:
        return False
    mutate(obj)
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, indent=indent, ensure_ascii=False) + "\n")
    return True


def apply_entries(repo, tgt, entries, uses, pending):
    merged = 0
    for _a, detail, kind, key in entries:
        ok = False
        if kind in ("art.slots", "art.rigs"):
            sec = kind.split(".")[1]
            ok = _json_rewrite(os.path.join(tgt.app, "skin", "art.json"),
                               lambda o: o.setdefault(sec, OrderedDict()).__setitem__(key, repo.art[sec][key]), pending, detail)
        elif kind == "colors.tokens":
            def m(o, pre=key):
                for t, v in repo.colors["tokens"].items():
                    if (t == pre or t.startswith(pre + ".")) and t not in o["tokens"]:
                        o["tokens"][t] = v
                        if v not in o["palette"] and v in repo.colors["palette"]:
                            o["palette"][v] = repo.colors["palette"][v]
            ok = _json_rewrite(os.path.join(tgt.app, "skin", "colors.json"), m, pending, detail)
        elif kind == "tuning":
            fn, _, path = key.partition(":")
            v, found = get_path(repo.tuning[fn], path)
            p = os.path.join(tgt.app, "App", "Resources", "Tuning", fn)
            if found and os.path.exists(p):
                ok = _json_rewrite(p, lambda o: set_path(o, path, v), pending, detail)
        elif kind == "strings":
            _, b = repo.helpers()
            lines = string_lines(repo, set(key))
            base = os.path.join(tgt.app, "App", "Resources", "Strings")
            for name, rows in lines.items():
                p = os.path.join(base, name)
                if not os.path.exists(p):
                    continue
                text = open(p, encoding="utf-8").read()
                have = {b.unescape(x.split("\t")[0]) for x in text.split("\n")[1:] if x.strip() and not x.startswith("#")}
                add_rows = [x for x in rows[1:] if b.unescape(x.split("\t")[0]) not in have]
                if add_rows:
                    keys = ", ".join(b.unescape(x.split("\t")[0]) for x in add_rows)
                    with open(p, "a", encoding="utf-8") as f:
                        f.write(("" if text.endswith("\n") else "\n") + f"# kit add (tools/kit.py): {keys[:100]}\n"
                                + "\n".join(add_rows) + "\n")
            ok = True
        if ok:
            merged += 1
        else:
            entry = {"kind": kind, "key": key}
            if kind == "tuning":
                fn, _, path = key.partition(":")
                entry["file"] = f"App/Resources/Tuning/{fn}"
                entry["value"] = get_path(repo.tuning[fn], path)[0]
            elif kind in ("art.slots", "art.rigs"):
                entry["value"] = repo.art[kind.split(".")[1]][key]
            elif kind == "colors.tokens":
                entry["value"] = {t: v for t, v in repo.colors["tokens"].items() if t == key or t.startswith(key + ".")}
            pending[detail] = entry
    return merged


# ============================================================================================ scan command

def scan_cmd(repo, comps, ids, write=False, prune=False):
    owners, problems = ownership(repo, comps)
    index = symbol_index(repo, comps, owners)
    for i in ids:
        c = comps[i]
        uses, refs = scan_component(repo, comps, c, owners, index)
        print(f"== {i}")
        for k in USE_KINDS:
            have, found = set(c.uses(k)), uses[k]
            if found or have:
                extra = sorted(have - found)
                print(f"  {k}: {len(found)} in sources" + (f"; +{len(found - have)} undeclared" if found - have else "")
                      + (f"; {len(extra)} declared, not seen in sources (hand-added or stale)" if extra else ""))
        reach = set(closure(comps, [i]))
        for d, names in sorted(refs.items()):
            mark = "" if d in reach or d == "core" else "   (wired)" if d in (c.wires or []) else "   <- not in depends"
            print(f"  references {d}: {', '.join(sorted(names)[:5])}{mark}")
        if write:
            u = c.data.setdefault("uses", OrderedDict())
            for k in USE_KINDS:
                have = set(u.get(k, []))
                new = (uses[k] if prune else have | uses[k])
                if new:
                    u[k] = sorted(new, key=natural)
                elif k in u:
                    del u[k]
            with open(repo.abs(c.path), "w", encoding="utf-8") as f:
                f.write(dumps(c.data))
            print(f"  wrote {c.path}")


# ============================================================================================ show / deps

def show(repo, comps, i):
    c = comps[i]
    owners, _ = ownership(repo, comps)
    rd = reverse_deps(comps)
    own = effective_files(repo, comps, c, owners)
    cl = closure(comps, [i])
    total = set()
    for d in cl:
        total |= set(effective_files(repo, comps, comps[d], owners))
    print(f"{c.title}  [{c.id}]  {c.category} · {c.status}")
    print(f"  {c.summary}\n")
    print("  " + c.description.replace("\n", "\n  ") + "\n")
    if c.gaps:
        print("Known gaps:")
        for g in c.gaps:
            print(f"  - {g}")
    print(f"Files ({len(own)} own; {len(total)} with its {len(cl) - 1} transitive deps):")
    for f in own:
        print(f"  {f}")
    tests = test_files(repo, c)
    if tests:
        print(f"Tests ({len(tests)}):")
        for f in tests:
            print(f"  {f}")
    print("Uses:")
    for k in USE_KINDS:
        v = c.uses(k)
        if v:
            print(f"  {k} ({len(v)}): {', '.join(v)}")
    print(f"Depends on: {', '.join(c.depends or []) or '-'}")
    print(f"Transitive: {', '.join(x for x in cl if x != i) or '-'}")
    print(f"Used by: {', '.join(sorted(rd.get(i, []))) or '-'}")
    if c.wires:
        print(f"Wires in (names them only to register / present them): {', '.join(c.wires)}")
    hooks = hook_sites(repo, comps, owners, symbol_index(repo, comps, owners), i)
    if hooks:
        print("Wired in by (the lines to edit if you remove it):")
        for owner, fs in sorted(hooks.items()):
            for f, names in sorted(fs.items()):
                print(f"  {owner:18} {f}: {', '.join(names[:6])}")
    others = total - set(effective_files(repo, comps, comps["core"], owners)) if "core" in comps else total
    print(f"Totals: {len(own)} own files, {len(total)} with deps, {len(others)} with deps excluding core")
    if c.data.get("maxClosure") is not None:
        mc = c.data["maxClosure"]
        state = "enforced by check" if c.status == "stable" else "declared; enforced once the component is stable"
        print(f"Budget: maxClosure {mc} (uses {len(others)}; {state})")
    if c.launchArgs:
        print("Open it (Debug build, tools/run.sh):")
        for a in c.launchArgs:
            print(f"  {a}")
    if c.notes:
        print("Notes:")
        for n in c.notes:
            print(f"  - {n}")
    print(f"Take it: python3 tools/kit.py export {i} --out /tmp/{i}-kit   ·   {c.folder}/README.md")


def print_tree(comps, i, reverse=False):
    edges = reverse_deps(comps) if reverse else {k: set(v.depends or []) for k, v in comps.items()}
    seen = set()

    def walk(n, prefix, last):
        mark = "" if prefix == "" and last is None else ("└─ " if last else "├─ ")
        again = n in seen
        print(prefix + mark + n + (" (see above)" if again and edges.get(n) else ""))
        if again:
            return
        seen.add(n)
        kids = sorted(edges.get(n, []), key=lambda x: (x == "core", x))
        for k, kid in enumerate(kids):
            walk(kid, prefix + ("" if last is None else ("   " if last else "│  ")), k == len(kids) - 1)

    walk(i, "", None)


# ============================================================================================ selftest

def selftest():
    repo = Repo()
    comps, lerr = load_components(repo)
    base_err, _ = validate(repo, comps, lerr, check_fresh=False, drift=False)
    ok = True

    def expect(name, mutate, needle, extra_files=()):
        nonlocal ok
        r = Repo()
        cs, le = load_components(r)
        cs = OrderedDict((k, Component(json.loads(json.dumps(v.data), object_pairs_hook=OrderedDict), v.path))
                         for k, v in cs.items())
        if extra_files:
            r.add_files(extra_files)
        mutate(r, cs)
        errs, _ = validate(r, cs, le, check_fresh=False, drift=False)
        new = [e for e in errs if e not in base_err]
        hit = any(needle in e for e in new)
        print(f"  {'ok  ' if hit else 'FAIL'} {name}" + ("" if hit else f"  (wanted {needle!r}; got {new[:3]})"))
        ok &= hit

    anyc = next(i for i in comps if i != "core")
    a = repo.app_rel
    print("kit.py check --selftest (each planted failure must be caught):")
    expect("unowned Swift file", lambda r, cs: None, "unowned", [f"{a}/App/Shell/Planted/Unowned.swift"])
    expect("double explicit owner", lambda r, cs: cs[anyc].data["files"].append(
        next(f for f in cs["core"].data["files"] if f.endswith(".swift") and not is_glob(f))), "two explicit claims")
    expect("double glob owner", lambda r, cs: [cs[x].data["files"].append(f"{a}/App/Planted2/*.swift") for x in list(cs)[1:3]],
           "two glob claims", [f"{a}/App/Planted2/X.swift"])

    def explicit_beats_glob(r, cs):
        cs["core"].data["files"].append(f"{a}/App/Planted3/*.swift")
        cs[anyc].data["files"].append(f"{a}/App/Planted3/Mine.swift")
    r3 = Repo()
    cs3, _ = load_components(r3)
    r3.add_files([f"{a}/App/Planted3/Mine.swift", f"{a}/App/Planted3/Other.swift"])
    explicit_beats_glob(r3, cs3)
    own3, prob3 = ownership(r3, cs3)
    hit = own3.get(f"{a}/App/Planted3/Mine.swift") == anyc and own3.get(f"{a}/App/Planted3/Other.swift") == "core" \
        and not any("Planted3" in p for p in prob3)
    print(f"  {'ok  ' if hit else 'FAIL'} explicit path beats a glob; a new file in a globbed folder is owned")
    ok &= hit
    expect("missing file", lambda r, cs: cs[anyc].data["files"].append(f"{a}/App/Nope/Missing.swift"), "matches no file")
    expect("unknown art slot", lambda r, cs: cs[anyc].data.setdefault("uses", {}).setdefault("art", []).append("no.such.slot"),
           "art slot 'no.such.slot'")
    expect("unknown sound", lambda r, cs: cs[anyc].data.setdefault("uses", {}).setdefault("sounds", []).append("boing"),
           "sound 'boing'")
    expect("unknown string key", lambda r, cs: cs[anyc].data.setdefault("uses", {}).setdefault("strings", []).append(
        "No such string anywhere 123"), "string key")
    expect("unknown tuning key", lambda r, cs: cs[anyc].data.setdefault("uses", {}).setdefault("tuning", []).append(
        "ui.json:frames.noSuchThing"), "tuning key")
    expect("unknown token prefix", lambda r, cs: cs[anyc].data.setdefault("uses", {}).setdefault("skinTokens", []).append(
        "popups.noSuchPopup"), "skin token prefix")
    expect("unknown dependency", lambda r, cs: cs[anyc].data["depends"].append("no-such-component"), "unknown component")
    ids = [i for i in comps if i != "core"][:2]
    expect("dependency cycle", lambda r, cs: (cs[ids[0]].data["depends"].append(ids[1]),
                                              cs[ids[1]].data["depends"].append(ids[0])), "dependency cycle")
    expect("closure misses core", lambda r, cs: cs[anyc].data.__setitem__("depends", []), "must reach \"core\"")
    expect("bad category", lambda r, cs: cs[anyc].data.__setitem__("category", "widgets"), "category 'widgets'")
    expect("needs-work without gaps", lambda r, cs: (cs[anyc].data.__setitem__("status", "needs-work"),
                                                     cs[anyc].data.pop("gaps", None)), "no `gaps`")
    expect("unknown key", lambda r, cs: cs[anyc].data.__setitem__("colour", "red"), "unknown key `colour`")
    expect("secret listed", lambda r, cs: cs[anyc].data["files"].append(".env"), "secret path", [".env"])
    expect("unknown wire", lambda r, cs: cs[anyc].data.__setitem__("wires", ["no-such-component"]), "wires unknown")
    expect("preview outside art/", lambda r, cs: cs[anyc].data.__setitem__("preview", ["README.md"]), "preview")
    expect("bad maxClosure", lambda r, cs: cs[anyc].data.__setitem__("maxClosure", "small"), "`maxClosure` must be")
    heavy = next(i for i in comps if i != "core" and len(closure(comps, [i])) > 2)
    expect("closure over its budget", lambda r, cs: (cs[heavy].data.__setitem__("status", "stable"),
                                                     cs[heavy].data.pop("gaps", None),
                                                     cs[heavy].data.__setitem__("maxClosure", 1)), "> maxClosure 1")
    # stale catalog: a component changed after the catalog was written
    r2 = Repo()
    cs2, le2 = load_components(r2)
    cs2[anyc].data["summary"] = cs2[anyc].data["summary"] + " (changed)"
    errs2, _ = validate(r2, cs2, le2, check_fresh=True, drift=False)
    hit = any("CATALOG.md: stale" in e for e in errs2) and any("catalog.html: stale" in e for e in errs2)
    print(f"  {'ok  ' if hit else 'FAIL'} a changed component.json makes CATALOG.md / catalog.html stale")
    ok &= hit
    # secrets never exported
    tmp = tempfile.mkdtemp(prefix="kit-selftest-")
    try:
        hit = all(secret(p) for p in [".env", "keys/AuthKey.p8", "apps/x/keys/a.json", "machine.env", "a/b/c.p12"]) and \
            not any(secret(p) for p in ["apps/mazeout/App/Brand.swift", "tools/kit.py", "docs/keys.md"])
        print(f"  {'ok  ' if hit else 'FAIL'} secret paths (.env, keys/, machine.env, *.p8 ...) are never exported")
        ok &= hit
        ign = git_ignored(REPO, [".env", "machine.env", "apps/mazeout/App/Brand.swift"])
        hit = ".env" in ign and "apps/mazeout/App/Brand.swift" not in ign
        print(f"  {'ok  ' if hit else 'FAIL'} git-ignored paths are detected (git check-ignore)")
        ok &= hit
        # a real export round trip
        pick = next((i for i in ("pause-menu", anyc) if i in comps))
        res = export(repo, comps, [pick], os.path.join(tmp, "x"), quiet=True)
        hit = os.path.isfile(os.path.join(tmp, "x", "MANIFEST.md")) and os.path.isfile(os.path.join(tmp, "x", "CHECKLIST.md")) \
            and all(os.path.isfile(os.path.join(tmp, "x", "files", f)) for f in res["files"] if f not in res["skipped"]) \
            and not any(secret(f) for f in res["files"])
        print(f"  {'ok  ' if hit else 'FAIL'} export {pick}: every file, MANIFEST.md, CHECKLIST.md written")
        ok &= hit
        zp = os.path.join(tmp, "x.zip")
        export(repo, comps, [pick], zp, quiet=True)
        with zipfile.ZipFile(zp) as z:
            names = z.namelist()
        hit = "MANIFEST.md" in names and any(n.startswith("files/") for n in names)
        print(f"  {'ok  ' if hit else 'FAIL'} export to a .zip")
        ok &= hit
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


# ============================================================================================ main

def main(argv=None):
    ap = argparse.ArgumentParser(prog="kit.py", description="The component kit (docs/guides/KIT.md).")
    ap.add_argument("--game", default=DEFAULT_GAME, help="the source game (default: mazeout, the reference)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--category", choices=["core"] + CATEGORIES)
    p = sub.add_parser("search")
    p.add_argument("text", nargs="+")
    for n in ("show", "deps", "rdeps"):
        sub.add_parser(n).add_argument("id")
    p = sub.add_parser("export")
    p.add_argument("ids", nargs="+")
    p.add_argument("--out", required=True, help="a new folder, or a path ending in .zip")
    p.add_argument("--without", action="append", default=[], help="leave a dependency out (the target provides it)")
    p = sub.add_parser("add")
    p.add_argument("ids", nargs="+")
    p.add_argument("--game", dest="target", required=True, help="the game to add to (apps/<slug>)")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", help="the default: report only")
    g.add_argument("--apply", action="store_true", help="copy the missing files and merge the missing entries")
    p = sub.add_parser("scan")
    p.add_argument("id", nargs="?")
    p.add_argument("--all", action="store_true")
    p.add_argument("--write", action="store_true")
    p.add_argument("--prune", action="store_true")
    sub.add_parser("catalog")
    p = sub.add_parser("check")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument("--strict", action="store_true", help="warnings (undeclared uses, references outside deps) fail too")
    p.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "check" and a.selftest:
        return selftest()
    repo = Repo(game=a.game)
    comps, lerr = load_components(repo)
    if a.cmd != "check" and lerr:
        for e in lerr:
            print("error:", e, file=sys.stderr)

    def need(i):
        if i not in comps:
            close = [c for c in comps if i in c] or list(comps)[:10]
            raise SystemExit(f"unknown component {i!r}; did you mean: {', '.join(close[:8])}")
        return i

    if a.cmd == "list":
        owners, _ = ownership(repo, comps)
        rows = [c for c in comps.values() if not a.category or c.category == a.category]
        for c in sorted(rows, key=lambda c: (cat_order(c.category), c.id)):
            n = len(effective_files(repo, comps, c, owners))
            print(f"{c.id:24} {c.category:14} {n:4} files  {c.status:10}  {c.summary}")
        print(f"\n{len(rows)} components")
    elif a.cmd == "search":
        words = [w.lower() for w in a.text]
        hits = []
        for c in comps.values():
            hay = " ".join([c.id, c.title or "", c.summary or "", c.description or "", " ".join(c.files or []),
                            " ".join(" ".join(v) for v in (c.data.get("uses") or {}).values())]).lower()
            if all(w in hay for w in words):
                hits.append(c)
        for c in hits:
            print(f"{c.id:24} {c.category:14} {c.summary}")
        print(f"\n{len(hits)} match")
    elif a.cmd == "show":
        show(repo, comps, need(a.id))
    elif a.cmd == "deps":
        print_tree(comps, need(a.id))
    elif a.cmd == "rdeps":
        need(a.id)
        print_tree(comps, a.id, reverse=True)
        allr = set()
        stack = [a.id]
        rd = reverse_deps(comps)
        while stack:
            for x in rd.get(stack.pop(), []):
                if x not in allr:
                    allr.add(x)
                    stack.append(x)
        print(f"\nRemoving {a.id} breaks {len(allr)} component(s)" + (f": {', '.join(sorted(allr))}" if allr else "."))
        owners, _ = ownership(repo, comps)
        hooks = hook_sites(repo, comps, owners, symbol_index(repo, comps, owners), a.id)
        if hooks:
            print("...and these registration lines name it (delete / replace them):")
            for owner, fs in sorted(hooks.items()):
                for f, names in sorted(fs.items()):
                    print(f"  {owner:18} {f}: {', '.join(names[:6])}")
    elif a.cmd == "export":
        for i in a.ids:
            need(i)
        export(repo, comps, a.ids, a.out, without=a.without)
    elif a.cmd == "add":
        for i in a.ids:
            need(i)
        add(repo, comps, a.ids, a.target, apply=a.apply)
    elif a.cmd == "scan":
        ids = list(comps) if a.all else [need(a.id)] if a.id else []
        if not ids:
            raise SystemExit("scan <id> or scan --all")
        scan_cmd(repo, comps, ids, write=a.write, prune=a.prune)
    elif a.cmd == "catalog":
        md, page = render_catalog(repo, comps)
        for name, text in (("CATALOG.md", md), ("catalog.html", page)):
            with open(os.path.join(repo.kit, name), "w", encoding="utf-8") as f:
                f.write(text)
        print(f"wrote kit/CATALOG.md, kit/catalog.html ({len(comps)} components)")
    elif a.cmd == "check":
        errors, warnings = validate(repo, comps, lerr, verbose=a.verbose)
        owners, _ = ownership(repo, comps)
        for e in errors:
            print("FAIL", e)
        if warnings and (a.verbose or a.strict):
            for w in warnings:
                print("WARN", w)
        n_swift = len(repo.owned_swift())
        print(f"kit check: {len(comps)} components, {n_swift} Swift files owned, {len(errors)} errors, "
              f"{len(warnings)} warnings" + ("" if a.verbose or a.strict or not warnings else " (-v lists them)"))
        return 1 if errors or (a.strict and warnings) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
