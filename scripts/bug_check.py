#!/usr/bin/env python3
"""Interaktif bug-check — XCUITest harness'ini en yeni iPhone Pro simulatorunde kosar.

Kullanim (repo kokunden):  python3 scripts/bug_check.py --slug <slug> [--light-only]

Yaptiklari:
  1. app dizininde `xcodegen generate` (UI test target'ini projeye alir).
  2. En yeni iPhone Pro (Max degil) simulatorunu bulur, boot eder.
  3. `xcodebuild test` — once karanlik sonra aydinlik modda (--light-only ile yalniz
     aydinlik). Her testin gec/kal durumunu ayristirir.
  4. Kirik/yaniti olmayan buton = FAIL. Herhangi bir test kalirsa exit 1 (submit engellenir).

Faz 10 (kalite kapisi #7) bunu cagirir. Gereksinim: xcodegen, xcodebuild (Xcode).
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def newest_iphone_pro():
    data = json.loads(sh(["xcrun", "simctl", "list", "devices", "available", "-j"]).stdout)
    best = None
    for runtime, devs in data["devices"].items():
        if "iOS" not in runtime:
            continue
        for d in devs:
            n = d["name"]
            if "iPhone" in n and "Pro" in n and "Max" not in n:
                num = int((re.search(r"iPhone (\d+)", n) or [0, 0])[1] or 0) \
                    if re.search(r"iPhone (\d+)", n) else 0
                if best is None or num > best[0]:
                    best = (num, d["udid"], n)
    return best


def pick_sim(ident):
    """Resolve --sim: a UDID or an exact device name among available simulators."""
    data = json.loads(sh(["xcrun", "simctl", "list", "devices", "available", "-j"]).stdout)
    for runtime, devs in data["devices"].items():
        if "iOS" not in runtime:
            continue
        for d in devs:
            if d["udid"] == ident or d["name"] == ident:
                return (0, d["udid"], d["name"])
    return None


def scheme_name(app_dir):
    m = re.search(r"^name:\s*(.+)$", (app_dir / "project.yml").read_text(), re.M)
    return m.group(1).strip()


def bundle_id(slug):
    """.env'deki BUNDLE_PREFIX + slug -> bundle id (mic/kamera izni onceden vermek icin)."""
    prefix = "com.manycode"
    envf = ROOT / ".env"
    if envf.exists():
        m = re.search(r"^BUNDLE_PREFIX\s*=\s*([^\s#]+)", envf.read_text(), re.M)
        if m:
            prefix = m.group(1).strip().strip('"').strip("'")
    return f"{prefix}.{slug}"


def pregrant_permissions(sim_id, slug):
    """Mikrofon iznini ONCEDEN ver — canli-mic app'lerinin UITest'i, izin diyalogu
    testi bloklamadan gercek ses yolunu kosabilsin. En iyi caba: kurulu degilse/
    desteklenmiyorsa sessizce gecilir (harness zaten interruption monitor tasir)."""
    sh(["xcrun", "simctl", "privacy", sim_id, "grant", "microphone", bundle_id(slug)])


def run_suite(scheme, app_dir, sim_id, appearance, slug):
    sh(["xcrun", "simctl", "bootstatus", sim_id, "-b"])
    pregrant_permissions(sim_id, slug)
    sh(["xcrun", "simctl", "ui", sim_id, "appearance", appearance])
    p = sh(["xcodebuild", "test",
            "-project", str(app_dir / f"{scheme}.xcodeproj"),
            "-scheme", scheme,
            "-destination", f"platform=iOS Simulator,id={sim_id}",
            "-only-testing", f"{scheme}UITests"],
           cwd=str(app_dir))
    out = p.stdout + p.stderr
    passed = re.findall(r"Test Case '-\[[\w.]+ (\w+)\]' passed", out)
    failed = re.findall(r"Test Case '-\[[\w.]+ (\w+)\]' failed", out)
    ok = "** TEST SUCCEEDED **" in out
    # surface the first real failure line for debugging
    fail_lines = [l for l in out.splitlines()
                  if ".swift:" in l and (" error:" in l or "XCTAssert" in l)][:6]
    return ok, passed, failed, fail_lines, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--light-only", action="store_true")
    ap.add_argument("--sim", help="simulator UDID or exact name (default: newest iPhone Pro). "
                                  "Parallel sessions must each pass their own simulator.")
    args = ap.parse_args()

    app_dir = ROOT / "apps" / args.slug
    if not app_dir.exists():
        sys.exit(f"!! app dizini yok: {app_dir}")
    scheme = scheme_name(app_dir)

    print(f"bug-check: {scheme}  (xcodegen generate...)")
    g = sh(["xcodegen", "generate"], cwd=str(app_dir))
    if g.returncode != 0:
        sys.exit(f"!! xcodegen basarisiz:\n{g.stdout}\n{g.stderr}")

    sim = pick_sim(args.sim) if args.sim else newest_iphone_pro()
    if not sim:
        sys.exit("!! simulator bulunamadi" + (f": {args.sim}" if args.sim else " (iPhone Pro)"))
    _, sim_id, sim_name = sim
    print(f"simulator: {sim_name} ({sim_id[:8]})")

    modes = ["light"] if args.light_only else ["dark", "light"]
    all_ok = True
    for mode in modes:
        print(f"\n=== {mode.upper()} MODE ===")
        ok, passed, failed, fail_lines, out = run_suite(scheme, app_dir, sim_id, mode, args.slug)
        for t in passed:
            print(f"  PASS  {t}")
        for t in failed:
            print(f"  FAIL  {t}")
        for l in fail_lines:
            print(f"        {l.strip()[:160]}")
        if not ok or failed:
            all_ok = False
            if not passed and not failed:
                # build/launch failure — dump tail for diagnosis
                print("  !! test kosulamadi; xcodebuild ciktisi (son satirlar):")
                for l in out.splitlines()[-25:]:
                    print("   ", l[:160])

    sh(["xcrun", "simctl", "ui", sim_id, "appearance", "light"])
    print("\n" + ("OK — tum interaktif testler gecti." if all_ok
                  else "!! BUG CHECK FAILED — duzelt ve tekrar kos (submit YOK)."))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
