#!/usr/bin/env python3
"""tools/harness_gate.py [--app DIR] [--selftest]: the debug harness stays out of the Release (store) build.

The harness (BoardLab, ShellLab, SoundBoard, SocialLab, AutoPlayer, the measurement runs GlitchRun / FrameWatch) is
compiled into Debug and the Measure configuration only (project.yml: Measure = Release's settings + PC_MEASURE). CI builds
Debug only, so a Release-only compile error — shipping code naming a harness type — would first show at archive time.
This check catches it from the sources (stdlib only, Linux):

  1. every harness FILE (a `<Name>Lab.swift` / `<Name>Lab+<Part>.swift`, or one of EXTRA_FILES) is wrapped whole in
     `#if DEBUG || PC_MEASURE` … `#endif` (only comments, blank lines and imports may sit outside it);
  2. a harness SYMBOL is every non-private top-level type declared in a harness file or inside a Debug / Measure-only
     region (see 3) of any other file; the members a harness file adds to a shipping type by extension; and the members
     of a shipping type declared inside such a region (`AppModel.autoplayer`, `WinDirector.startSynthetic`). A member
     name that ungated shipping code also declares (a protocol default such as `makeDebugScreen`) is not one;
  3. no Swift file outside the harness names a harness symbol, in code, unless the use sits inside a `#if` branch that only
     Debug or Measure compiles (`DEBUG`, `PC_MEASURE`, `DEBUG || PC_MEASURE`, or a `&&` with one of them). Comments and
     string literals do not count; string interpolations do.

Scanned: <app>/App and <app>/art/ui/code (the app target's sources). Tests/ and UITests/ build in Debug only.
Exit 0 = clean; 1 = findings (file:line: what). --selftest plants failing controls in a temp tree and checks each is caught.
"""
import argparse
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP_DEFAULT = os.path.dirname(HERE)
SOURCE_DIRS = ["App", os.path.join("art", "ui", "code")]
GATE = "DEBUG || PC_MEASURE"
LAB_FILE = re.compile(r"^[A-Za-z0-9]*Lab(\+[A-Za-z0-9]+)?\.swift$")
EXTRA_FILES = {"SoundBoard.swift", "AutoPlayer.swift", "GlitchRun.swift", "FrameWatch.swift"}
SAFE_ATOMS = {"DEBUG", "PC_MEASURE", "DEBUG || PC_MEASURE", "PC_MEASURE || DEBUG"}
TYPE_DECL = re.compile(r"^\s*((?:@[\w.]+(?:\([^)]*\))?\s+|(?:public|internal|private|fileprivate|open|final|nonisolated|"
                       r"indirect)\s+)*)(struct|class|enum|protocol|actor|typealias)\s+([A-Za-z_]\w*)")
EXT_DECL = re.compile(r"^\s*(?:@[\w.]+\s+)*(?:(?:public|internal|private|fileprivate)\s+)?extension\s+([A-Za-z_][\w.]*)")
MEMBER_DECL = re.compile(r"^\s*((?:@[\w.]+(?:\([^)]*\))?\s+|(?:public|internal|private|fileprivate|open)(?:\(set\))?\s+|"
                         r"(?:final|static|class|override|nonisolated|mutating|lazy|weak|unowned|dynamic|required|"
                         r"convenience)\s+)*)(func|var|let)\s+([A-Za-z_]\w*)")
PRIVATE = re.compile(r"\b(private|fileprivate)\b(?!\(set\))")
ANY_MEMBER = re.compile(r"\b(func|var|let|case)\s+([A-Za-z_]\w*)")
DIRECTIVE = re.compile(r"^\s*#(if|elseif|else|endif)\b(.*)$")


def is_harness_file(path):
    name = os.path.basename(path)
    return bool(LAB_FILE.match(name)) or name in EXTRA_FILES


def strip_code(text):
    """Comments and string-literal text → spaces (newlines kept, so line numbers hold); interpolations stay code."""
    out, i, n = [], 0, len(text)
    stack = []            # string contexts: ("str", hashes, multiline) / ("interp", paren depth)
    while i < n:
        c = text[i]
        top = stack[-1] if stack else None
        if top is None or top[0] == "interp":
            if text.startswith("//", i):
                j = text.find("\n", i)
                j = n if j < 0 else j
                out.append(" " * (j - i)); i = j; continue
            if text.startswith("/*", i):
                depth, j = 1, i + 2
                while j < n and depth:
                    if text.startswith("/*", j): depth += 1; j += 2
                    elif text.startswith("*/", j): depth -= 1; j += 2
                    else: j += 1
                out.append(re.sub(r"[^\n]", " ", text[i:j])); i = j; continue
            m = re.match(r'(#*)("""|")', text[i:i + 64])
            if m:
                stack.append(("str", len(m.group(1)), m.group(2) == '"""'))
                out.append(" " * len(m.group(0))); i += len(m.group(0)); continue
            if top is not None:
                if c == "(":
                    stack[-1] = ("interp", top[1] + 1)
                elif c == ")":
                    if top[1] == 0:
                        stack.pop(); out.append(" "); i += 1; continue
                    stack[-1] = ("interp", top[1] - 1)
            out.append(c); i += 1; continue
        # inside a string literal
        _, hashes, multi = top
        close = ('"""' if multi else '"') + "#" * hashes
        if text.startswith(close, i):
            stack.pop(); out.append(" " * len(close)); i += len(close); continue
        esc = "\\" + "#" * hashes
        if text.startswith(esc, i):
            k = i + len(esc)
            if text.startswith("(", k):                      # \( … ) (or \#( … ) in a raw string): code again
                stack.append(("interp", 0)); out.append(" " * (k + 1 - i)); i = k + 1; continue
            if k < n and text[k] != "\n":
                k += 1                                       # the escaped character
            out.append(" " * (k - i)); i = k; continue
        out.append("\n" if c == "\n" else " "); i += 1
    return "".join(out)


def _split_top(c, op):
    parts, depth, cur, i = [], 0, "", 0
    while i < len(c):
        if c[i] == "(": depth += 1
        elif c[i] == ")": depth -= 1
        if depth == 0 and c.startswith(op, i):
            parts.append(cur.strip()); cur = ""; i += len(op); continue
        cur += c[i]; i += 1
    return parts + [cur.strip()]


def _unparen(c):
    """`(A || B)` → `A || B` while the outer parentheses enclose the whole condition."""
    c = c.strip()
    while c.startswith("(") and c.endswith(")"):
        depth = 0
        for i, ch in enumerate(c):
            depth += (ch == "(") - (ch == ")")
            if depth == 0 and i < len(c) - 1:
                return c                                     # `(A) && (B)`: the first ( closes early
        c = c[1:-1].strip()
    return c


def cond_is_safe(cond):
    """True when only Debug or Measure compiles a branch under this #if/#elseif condition: DEBUG, PC_MEASURE, their `||`,
    or an `&&` with one of those as a conjunct. Anything else (`!DEBUG`, `DEBUG || os(iOS)`, …) is not safe."""
    c = _unparen(" ".join(cond.split()))
    if c in SAFE_ATOMS:
        return True
    ors = _split_top(c, "||")
    if len(ors) > 1:
        return all(_unparen(p) in {"DEBUG", "PC_MEASURE"} for p in ors)
    ands = _split_top(c, "&&")
    return len(ands) > 1 and any(cond_is_safe(p) for p in ands)


def lines_with_gates(code):
    """[(line number, code line, safe: bool, directive-or-None, #if depth)] for stripped code."""
    stack, rows = [], []   # one [this branch safe?, its condition] per open #if
    for k, line in enumerate(code.split("\n"), 1):
        m = DIRECTIVE.match(line)
        if m:
            kind, rest = m.group(1), m.group(2).strip()
            if kind == "if":
                stack.append([cond_is_safe(rest), rest])
            elif kind == "elseif" and stack:
                stack[-1] = [cond_is_safe(rest), rest]
            elif kind == "else" and stack:
                stack[-1] = [False, "!" + stack[-1][1]]
            elif kind == "endif" and stack:
                stack.pop()
            rows.append((k, line, any(s[0] for s in stack), kind, len(stack)))
            continue
        rows.append((k, line, any(s[0] for s in stack), None, len(stack)))
    return rows


def top_level_decls(code):
    """Declarations by brace depth, with their gate state:
    types    [(name, line, safe)]           non-private types at depth 0;
    members  [(owner, name, line, gated, private)]  func / var / let at depth 1 of a top-level type or extension body
             (`owner` = that type's or extension's name; `gated` = inside a gate that the owner's declaration is not in)."""
    types, members = [], []
    depth, owner, pending = 0, None, None      # owner / pending: (name, declared inside a gate?)
    for k, line, safe, directive, _ in lines_with_gates(code):
        if directive:
            continue
        if depth == 0:
            m = TYPE_DECL.match(line)
            e = EXT_DECL.match(line)
            if m:
                if not PRIVATE.search(m.group(1)):
                    types.append((m.group(3), k, safe))
                pending = (m.group(3), safe)
            elif e:
                pending = (e.group(1), safe)
        elif depth == 1 and owner:
            m = MEMBER_DECL.match(line)
            if m:
                members.append((owner[0], m.group(3), k, safe and not owner[1], bool(PRIVATE.search(m.group(1)))))
        for ch in line:
            if ch == "{":
                if depth == 0:
                    owner, pending = pending, None
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    owner = None
    return types, members


def file_gate_problem(code):
    """None when the whole file (but comments / imports) sits in one `#if DEBUG || PC_MEASURE` … `#endif`."""
    rows = [(k, l.strip(), d, depth) for k, l, _, d, depth in lines_with_gates(code) if l.strip()]
    body = [r for r in rows if not (r[3] == 0 and r[2] is None and r[1].startswith("import "))]
    if not body:
        return "empty file"
    k0, line0, d0, _ = body[0]
    if d0 != "if" or " ".join(line0[3:].split()) != GATE:
        return f"line {k0}: the file must open with `#if {GATE}` (found `{line0[:60]}`)"
    for idx, (k, line, d, depth) in enumerate(body[1:], 1):
        if depth == 0:                                       # the gate's own #endif
            if idx != len(body) - 1:
                return f"line {body[idx + 1][0]}: code after the gate's #endif (line {k})"
            return None
    return "the gate is not closed at the end of the file"


def swift_files(app):
    for sub in SOURCE_DIRS:
        root = os.path.join(app, sub)
        for d, dirs, fs in os.walk(root):
            dirs.sort()
            for f in sorted(fs):
                if f.endswith(".swift"):
                    yield os.path.join(d, f)


def check(app):
    files = {p: strip_code(open(p, encoding="utf-8").read()) for p in swift_files(app)}
    rel = lambda p: os.path.relpath(p, app)
    problems, symbols, ext_members, other_members = [], {}, {}, set()
    harness = [p for p in files if is_harness_file(p)]
    for p in harness:
        why = file_gate_problem(files[p])
        if why:
            problems.append(f"{rel(p)}: harness file not gated: {why}")
    decls = {p: top_level_decls(code) for p, code in files.items()}
    for p in harness:
        for name, _, _ in decls[p][0]:
            symbols.setdefault(name, rel(p))
    for p, code in files.items():
        types, members = decls[p]
        if p in harness:
            # members a harness file adds to a SHIPPING type by extension (a harness type's own are covered by its name)
            for owner, name, _, _, private in members:
                if not private and owner.split(".")[0] not in symbols:
                    ext_members.setdefault(name, f"{rel(p)} (extension {owner})")
            continue
        for name, _, safe in types:
            if safe:
                symbols.setdefault(name, f"{rel(p)} (gated region)")
        # members of shipping types declared only inside a gate (AppModel.autoplayer, WinDirector.startSynthetic, …)
        for owner, name, _, safe, _ in members:
            if safe:
                ext_members.setdefault(name, f"{rel(p)} ({owner}, gated member)")
        ungated = "\n".join(line for _, line, safe, d, _ in lines_with_gates(code) if not safe and not d)
        other_members.update(m.group(2) for m in ANY_MEMBER.finditer(ungated))
    for name in list(ext_members):
        if name in other_members:
            del ext_members[name]              # declared by ungated shipping code too (a protocol default, an overload)
    wanted = dict(symbols, **ext_members)
    if not wanted:
        return problems, 0
    pattern = re.compile(r"\b(" + "|".join(sorted(map(re.escape, wanted), key=len, reverse=True)) + r")\b")
    for p, code in files.items():
        if p in harness:
            continue
        for k, line, safe, directive, _ in lines_with_gates(code):
            if safe or directive:
                continue
            for m in pattern.finditer(line):
                name = m.group(1)
                problems.append(f"{rel(p)}:{k}: `{name}` (harness: {wanted[name]}) used outside `#if {GATE}`")
    return problems, len(wanted)


# MARK: - self-test

SELFTEST_FILES = {
    # a clean tree: gated labs, a gated region, gated call sites, mentions in comments and plain strings
    "App/Board/BoardLab.swift": "import SwiftUI\n// lab\n#if DEBUG || PC_MEASURE\nstruct BoardLab: View {}\n"
                                "final class LabDriver {}\nprivate struct Secret {}\nextension SocialModel {\n"
                                "    func publishP95() -> Double { 0 }\n    static func makeDebugScreen() -> Int? { 1 }\n}\n#endif\n",
    "App/Game/AutoPlayer.swift": "#if DEBUG || PC_MEASURE\n#if os(iOS)\n@MainActor final class AutoPlayer {}\n#endif\n#endif\n",
    "App/Shell/Router.swift": "enum Router {}\n#if DEBUG || PC_MEASURE\n@MainActor enum DebugTabLoop {}\n#endif\n",
    "App/Contracts/Contract.swift": "protocol P {}\nextension P {\n    static func makeDebugScreen() -> Int? { nil }\n}\n"
                                    "struct Secret {}\n",
    "App/AppModel.swift": "final class AppModel {\n    #if DEBUG || PC_MEASURE\n    var autoplayer: AutoPlayer?\n"
                          "    #else\n    let note = \"no AutoPlayer here\"   // AutoPlayer is Debug only\n    #endif\n"
                          "    #if DEBUG\n    let lab = BoardLab()\n    #endif\n    #if PC_MEASURE && os(iOS)\n"
                          "    let d = DebugTabLoop.self\n    #endif\n    /* LabDriver */ let s = \"LabDriver \\\\(x)\"\n"
                          "    let r = #\"AutoPlayer \\(y)\"#\n    let secret = Secret()\n    let n = P.makeDebugScreen()\n}\n",
}
SELFTEST_BAD = {
    # name: (path, content, expected substring of the finding)
    "ungated lab file": ("App/Shell/NewLab.swift", "import SwiftUI\nstruct NewLab {}\n", "harness file not gated"),
    "lab gated with DEBUG only": ("App/Shell/ShellLab+Extra.swift", "#if DEBUG\nstruct ExtraPage {}\n#endif\n",
                                  "must open with"),
    "gate closes early": ("App/Audio/SoundBoard.swift", "#if DEBUG || PC_MEASURE\nstruct SoundBoard {}\n#endif\nstruct Leak {}\n",
                          "after the gate"),
    "use outside any gate": ("App/Game/Use1.swift", "func f() { _ = LabDriver() }\n", "`LabDriver`"),
    "use in the #else branch": ("App/Game/Use2.swift", "#if DEBUG || PC_MEASURE\nlet a = 1\n#else\nlet b = AutoPlayer()\n#endif\n",
                                "`AutoPlayer`"),
    "use under #if !DEBUG": ("App/Game/Use3.swift", "#if !DEBUG\nlet b = BoardLab()\n#endif\n", "`BoardLab`"),
    "use under DEBUG || os(iOS)": ("App/Game/Use4.swift", "#if DEBUG || os(iOS)\nlet b = BoardLab()\n#endif\n", "`BoardLab`"),
    "use in a string interpolation": ("App/Game/Use5.swift", "let s = \"x \\(AutoPlayer.self)\"\n", "`AutoPlayer`"),
    "use of a gated-region type": ("App/Game/Use6.swift", "let t = DebugTabLoop.self\n", "`DebugTabLoop`"),
    "use of a lab extension member": ("App/Game/Use7.swift", "func g(m: SocialModel) -> Double { m.publishP95() }\n",
                                      "`publishP95`"),
    "use in art/ui/code": ("art/ui/code/Chrome.swift", "let l = LabDriver()\n", "`LabDriver`"),
    "use of a gated member": ("App/Game/Use8.swift", "func h(a: AppModel) { a.autoplayer?.start() }\n", "`autoplayer`"),
    "same-file use of a gated private member": ("App/Game/Flow.swift", "final class Flow {\n    #if DEBUG || PC_MEASURE\n"
                                                "    private func debugJump() {}\n    #endif\n"
                                                "    func frame() { debugJump() }\n}\n", "`debugJump`"),
}


def _write(root, files):
    for rel_path, content in files.items():
        p = os.path.join(root, rel_path)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(content)


COND_CASES = {"DEBUG": True, "PC_MEASURE": True, "DEBUG || PC_MEASURE": True, "(DEBUG || PC_MEASURE)": True,
              "DEBUG && os(iOS)": True, "(DEBUG || PC_MEASURE) && canImport(UIKit)": True, "!DEBUG": False,
              "DEBUG || os(iOS)": False, "os(iOS)": False, "(A) && (B)": False, "!(DEBUG || PC_MEASURE)": False}


def selftest():
    failures = [f"condition `{c}` read as {'safe' if not want else 'unsafe'}"
                for c, want in COND_CASES.items() if cond_is_safe(c) != want]
    with tempfile.TemporaryDirectory() as t:
        clean = os.path.join(t, "clean")
        _write(clean, SELFTEST_FILES)
        problems, n = check(clean)
        if problems:
            failures.append("clean control reported: " + "; ".join(problems))
        if n < 5:
            failures.append(f"clean control found only {n} harness symbols (expected BoardLab, LabDriver, AutoPlayer, "
                            f"DebugTabLoop, publishP95)")
        for name, (path, content, expect) in SELFTEST_BAD.items():
            root = os.path.join(t, re.sub(r"\W+", "_", name))
            _write(root, SELFTEST_FILES)
            _write(root, {path: content})
            problems, _ = check(root)
            hit = [p for p in problems if expect in p]
            print(f"  {'caught' if hit else 'MISSED'}  {name}: {hit[0] if hit else problems}")
            if not hit:
                failures.append(f"planted failure not caught: {name}")
            extra = [p for p in problems if not p.startswith(path)]
            if extra:
                failures.append(f"{name}: unexpected findings elsewhere: {extra}")
    if failures:
        print("harness_gate selftest FAILED:\n  " + "\n  ".join(failures))
        return 1
    print(f"harness_gate selftest: clean control passes, {len(SELFTEST_BAD)}/{len(SELFTEST_BAD)} planted failures caught")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--app", default=APP_DEFAULT, help="the app folder (default: this tool's app)")
    ap.add_argument("--selftest", action="store_true", help="run the planted-failure controls")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    problems, n = check(os.path.abspath(a.app))
    if problems:
        print(f"harness_gate: {len(problems)} problem(s) (the debug harness must stay out of the Release build):")
        for p in problems:
            print("  " + p)
        return 1
    harness = [os.path.relpath(p, a.app) for p in swift_files(os.path.abspath(a.app)) if is_harness_file(p)]
    print(f"harness_gate: OK — {len(harness)} harness files gated `#if {GATE}`, {n} harness symbols, none used outside the gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
