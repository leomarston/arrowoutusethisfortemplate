#!/bin/sh
# tools/bench/measure_strip_check.sh <Release .app> <Measure .app> [<Debug .app>] [--json OUT]
# F3-A (SPEC.md ruling 52(a), 2026-09-29; triage A3-r2 + N-02). Proves on the BUILT binaries that:
#  H. the measurement harness (App/Shell/GlitchRun.swift, App/FX/FrameWatch.swift, Router's DebugTabLoop) and the debug
#     harness (BoardLab, ShellLab, SoundBoard, SocialLab, AutoPlayer; docs/ROADMAP.md phase 0) are in the Measure build
#     (Release's settings + PC_MEASURE, project.yml) and NOT in the Release (store) build;
#  P. the WP0 placeholders (PlaceholderBoard / PlaceholderLevel / BootPlaceholderView / LoadingPlaceholderView and their
#     boot-log / label / accessibility strings) are in neither Release nor Measure (Debug only).
# Each marker is a type name (Swift metadata + the symbol table: `strings` sees it) or a literal > 15 UTF-8 bytes (shorter
# Swift literals live inline in the code, invisible to `strings`). A marker only counts when its CONTROL finds it — the
# harness markers in the Measure binary, the placeholder markers in the Debug binary (when one is given) — so an absence
# is never the scanner's blindness. Every Mach-O file of the .app is scanned (a Debug build keeps its code in
# ArrowOut.debug.dylib). Exit 0 only when every check passes.
set -u
REL="${1:?usage: measure_strip_check.sh <Release .app> <Measure .app> [<Debug .app>] [--json OUT]}"
MEA="${2:?usage: measure_strip_check.sh <Release .app> <Measure .app> [<Debug .app>] [--json OUT]}"
shift 2
DBG=""; OUT=""
while [ $# -gt 0 ]; do
  case "$1" in
    --json) OUT="$2"; shift 2 ;;
    *) DBG="$1"; shift ;;
  esac
done
python3 - "$REL" "$MEA" "$DBG" "$OUT" <<'PY'
import json, os, re, sys, time
rel, mea, dbg, out = sys.argv[1], sys.argv[2], sys.argv[3] or None, sys.argv[4] or None
HARNESS = ["GlitchRun", "FrameWatch", "DebugTabLoop",
           "watch on (every presented frame > 20 ms is logged)",        # FrameWatch.start's log line
           "tabLoop: home is not up",                                   # DebugTabLoop's error line
           # the debug harness (labs + autoplayer, `#if DEBUG || PC_MEASURE`; tools/harness_gate.py checks the sources):
           # classes, whose type descriptors carry their names
           "BoardLabController", "SoundBoardModel", "SocScrollDriver", "HUDWriteMeter", "AutoPlayer"]
PLACEHOLDER = ["PlaceholderBoard", "PlaceholderLevel", "BootPlaceholderView", "LoadingPlaceholderView",
               "BoardEntry.makeBoard: default (placeholder board)", "GameEntry.makeLevel: default (placeholder level)",
               "ShellEntry.makeRoot: default (WP0 boot placeholder)", ": GAME not installed", "loading.placeholder",
               "boot.placeholder"]
PRINTABLE = re.compile(rb'[\x20-\x7e]{4,}')

def machos(app):
    for d, _, fs in os.walk(app):
        for f in fs:
            p = os.path.join(d, f)
            try:
                with open(p, 'rb') as h:
                    if h.read(4) in (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe'):
                        yield p
            except OSError:
                pass

def counts(app, markers):
    blob = b'\n'.join(b'\n'.join(PRINTABLE.findall(open(p, 'rb').read())) for p in machos(app))
    return {m: blob.count(m.encode()) for m in markers}, sorted(os.path.relpath(p, app) for p in machos(app))

report = {"when": time.strftime('%Y-%m-%d %H:%M:%S'), "release": rel, "measure": mea, "debug": dbg, "checks": []}
ok = True
def check(name, passed, detail):
    global ok
    ok = ok and passed
    report["checks"].append({"check": name, "pass": passed, **detail})
    print(f"  {'PASS' if passed else 'FAIL'}  {name}: {json.dumps(detail)[:400]}")

for app in [rel, mea] + ([dbg] if dbg else []):
    if not os.path.isdir(app):
        sys.exit(f"no app at {app}")
r_h, r_files = counts(rel, HARNESS); m_h, m_files = counts(mea, HARNESS)
r_p, _ = counts(rel, PLACEHOLDER); m_p, _ = counts(mea, PLACEHOLDER)
print(f"Release: {rel} (Mach-O: {', '.join(r_files)})\nMeasure: {mea} (Mach-O: {', '.join(m_files)})")
seen_h = [m for m in HARNESS if m_h[m] > 0]
check("H control: the harness markers are visible in the Measure binary", len(seen_h) == len(HARNESS),
      {"measure_counts": m_h})
check("H: no harness marker in the Release (store) binary", all(r_h[m] == 0 for m in seen_h) and bool(seen_h),
      {"release_counts": r_h})
if dbg:
    d_p, d_files = counts(dbg, PLACEHOLDER)
    print(f"Debug: {dbg} (Mach-O: {', '.join(d_files)})")
    seen_p = [m for m in PLACEHOLDER if d_p[m] > 0]
    check("P control: the placeholder markers are visible in the Debug binary", len(seen_p) == len(PLACEHOLDER),
          {"debug_counts": d_p})
else:
    seen_p = PLACEHOLDER
    report["checks"].append({"check": "P control", "pass": None, "note": "no Debug app given: absences are not controlled"})
    print("  ----  P control: no Debug app given (the absences below are not controlled)")
check("P: no WP0 placeholder marker in the Release binary", all(r_p[m] == 0 for m in seen_p), {"release_counts": r_p})
check("P: no WP0 placeholder marker in the Measure binary", all(m_p[m] == 0 for m in seen_p), {"measure_counts": m_p})
report["result"] = "PASS" if ok else "FAIL"
print(f"== RESULT: {report['result']}")
if out:
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(report, open(out, 'w'), indent=1)
sys.exit(0 if ok else 1)
PY
