#!/usr/bin/env python3
"""Run the app's CaptureTests and pull the attached screenshots into shots/final/.

Why a UI test instead of `simctl launch -ShowScreen ...`: a bare simctl launch does not
reliably activate the scene, so SwiftUI never runs the `.task` blocks the debug routing
hangs off, and every capture comes back as the untouched first screen. XCUIApplication
foregrounds the app properly and can scroll and tap, which is what the shots need.

Usage: python3 scripts/capture_shots.py --slug strobelight [--test CaptureTests]
"""
import argparse
import json
import plistlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, **kw)


def newest_pro_sim():
    data = json.loads(sh("xcrun simctl list devices available -j").stdout)
    best = None
    for runtime, devices in data["devices"].items():
        if "iOS" not in runtime:
            continue
        ver = tuple(int(x) for x in re.findall(r"\d+", runtime.split("iOS-")[-1]))
        for d in devices:
            if "iPhone" in d["name"] and "Pro" in d["name"] and "Max" not in d["name"]:
                key = (ver, d["name"])
                if best is None or key > best[0]:
                    best = (key, d["udid"], d["name"])
    if not best:
        sys.exit("no iPhone Pro simulator available")
    return best[1], best[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--test", default="CaptureTests")
    ap.add_argument("--sim", help="simulator name substring (default: newest iPhone Pro). "
                                  "A universal app also needs an iPad set.")
    args = ap.parse_args()

    appdir = ROOT / "apps" / args.slug
    proj = next(appdir.glob("*.xcodeproj"), None)
    if proj is None:
        sys.exit(f"no xcodeproj in {appdir}")
    scheme = proj.stem

    if args.sim:
        data = json.loads(sh("xcrun simctl list devices available -j").stdout)
        match = [(d["udid"], d["name"]) for devs in data["devices"].values() for d in devs
                 if args.sim.lower() in d["name"].lower()]
        if not match:
            sys.exit(f"no simulator matching {args.sim!r}")
        udid, name = match[0]
    else:
        udid, name = newest_pro_sim()
    print(f"capture: {scheme}  on {name}")

    result = appdir / "shots" / "capture.xcresult"
    shutil.rmtree(result, ignore_errors=True)
    r = sh(["xcodebuild", "test",
            "-project", str(proj), "-scheme", scheme,
            "-destination", f"id={udid}",
            "-resultBundlePath", str(result),
            "-only-testing", f"{scheme}UITests/{args.test}"],
           cwd=appdir)
    if "** TEST SUCCEEDED **" not in r.stdout:
        print(r.stdout[-4000:])
        sys.exit("capture test failed")

    # The test writes the PNGs itself (see CaptureTests.grab). Going through the
    # .xcresult attachment API proved unreliable — `xcresulttool export attachments`
    # returned an empty manifest for a passing test — and a simulator process can write
    # to host paths perfectly well, so the file IS the interface.
    dest = appdir / "shots" / ("final-ipad" if args.sim and "ipad" in args.sim.lower()
                                       else "final")
    found = sorted(f.name for f in dest.glob("*.png")) if dest.exists() else []

    if not found:
        sys.exit("test passed but no attachments were exported")
    for f in sorted(found):
        print("  ", f)
    print(f"{len(found)} screenshots -> {dest}")


if __name__ == "__main__":
    main()
