#!/usr/bin/env python3
"""VERIFY V2 capture driver (GAMEPROMPT §8.3 "Captures wait for a ready file", §9 step 1).
Adapted from apps/matchfactory/tools/capture/capture.py (e10a076): -mf. -> -pc., [MF] -> [PC], our slots and bundle id,
generic probe conditions (MF's trayLanded is gone), the blank-frame test of tools/flat_check.py instead of MF's
placeholder colour, and the boot-cap retry keyed on BOOT_CAP_MARK (design/REUSE.md).

    tools/capture/capture.py [--slot B] [--only id,id] [--langs en,tr] [--out build/compare/captures] [manifest.json]

For every manifest entry and language it:
  1. clears Documents/{capture-ready,probe}.json in the app container,
  2. launches through tools/run.sh (terminate -> install -> launch) with `-pc.capture 1 -pc.probeFile 1`, the entry's
     args and the language pair (-AppleLanguages + -AppleLocale, both set: the simulator inherits the Mac's en_TR,
     memory simulator-inherits-mac-region),
  3. waits until the entry's readiness holds (all given conditions):
       "screen": prefix of Documents/capture-ready.json "screen" (the shell's capture marker),
       "log":    substring of a `[PC]` console line (e.g. "[tutorial] show l1Tap"),
       "probe":  conditions on Documents/probe.json: {key: true} = truthy, {key: {"min": n}} = number >= n (or the
                 length of a list >= n), {key: value} = equal (e.g. {"settled": true, "lvl": 32, "phase": "play"}),
  4. sleeps "wait" s (entrances/popups finishing), screenshots with `simctl io … --mask=ignored`, converts to sRGB
     through the embedded profile (sips), and writes <out>/<id>-<lang>.png plus <id>-<lang>.json (args, readiness, the
     capture-ready marker, the probe, the [PC] log tail).
  "burst": [dt, …] takes extra frames at ready+wait+dt (or as fast as simctl allows) as <id>-<lang>@<k>.png (moments no freeze hook reaches).
Every frame must still be LOOKED at (memory screenshots-verify-content-not-count).

S1 (Wave 4, App Store screenshots) additions, all opt-in per entry (the V2 path is unchanged):
  "actions": [...] run after readiness and before "wait", in order; each is one of
       {"sleep": s}
       {"until": {probe conds}, "timeout": s}           poll Documents/probe.json (4 Hz) at 30 ms until the conds hold
       {"tap": [x, y]} | {"tapId": "accessibility id"}  a real simulator touch through AXe (XcodeBuildMCP's bundled axe;
                                                       $AXE overrides), in points
       {"tapArrow": {"id": n} | {"free": true, "near": [x, y], "avoid": [ids]} | {"wanted": true}}
                                                       taps an arrow's tap point from the probe (free = the session says
                                                       its ray is clear, so no bump / no heart lost; wanted = the arrow the
                                                       last clearUntil freed)
       {"swipe": [x0, y0, x1, y1, seconds]}              a real drag (scrolls a page)
       {"tapSeq": [ids], "gap": s}                        taps a planned sequence of arrows by id (each must be free in the
                                                       probe at its turn)
       {"clearUntil": {"want": [ids], "maxTaps": n}}    taps free arrows outside `want` (farthest from them first) until one
                                                       of `want` is free (e.g. an arrow whose exit runs through a pipe)
     a tap may carry "then": {"log": "…"} / {"probe": {…}} + "timeout": the step returns the moment that holds (the tap's
     own `[PC][perf] tap` line under -pc.logTaps 1), so the shot lands on the tap's first frames.
  probe conds also take {"max": n} (a number or a list length <= n).
  --store-dir DIR (with --store): an entry with "frame": "NN" also lands as DIR/<store locale>/NN.png (en → en-US, de → de-DE,
     fr → fr-FR, es → es-ES, sl → sl-SI; the other languages keep their code), the frame the S1 composer reads.
"""
import argparse, json, os, shutil, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import flat_check  # noqa: E402  (tools/flat_check.py)

SLOTS = {"A": "177520B6-4889-46C2-BDD9-155813D2B175", "B": "B80EDB24-6280-4C52-A63F-E8AADD245017"}   # = tools/slot.sh
BUNDLE = "com.manycode.arrowout"
LOG_TAG = "[PC]"
# The shell's log line when a first-screen-is-a-level launch overran its boot cap (MF: "boot work hit the 6.0 s cap").
# SHELL defines the real text; keep the two in sync.
BOOT_CAP_MARK = "boot work hit the"
FLAT_MAX = 0.97        # tools/capture-shot.sh: a blank frame is ~100 % one tone; a sparse white board ~92 %
LANG_ARGS = {"en": ["-AppleLanguages", "(en)", "-AppleLocale", "en_US"],
             "tr": ["-AppleLanguages", "(tr)", "-AppleLocale", "tr_TR"]}
# FIX-2 lane B (B3-r6 / B2-r3, Wave-4 S1 input): the other 11 shipped languages (SPEC.md ruling 37a), each with its locale
for _l, _loc in (("de", "de_DE"), ("fr", "fr_FR"), ("es", "es_ES"), ("it", "it_IT"), ("pt-BR", "pt_BR"), ("ja", "ja_JP"),
                 ("ko", "ko_KR"), ("zh-Hans", "zh_Hans_SG"), ("pl", "pl_PL"), ("sk", "sk_SK"), ("sl", "sl_SI")):
    LANG_ARGS[_l] = ["-AppleLanguages", f"({_l})", "-AppleLocale", _loc]
# --store (the App Store screenshots, Wave 4 S1): a RELEASE build only (the DEBUG FakeStore draws its "Test store" chip and
# Debug ships a debug dylib), a world as old as the shipped app will meet (B2: the capture clock 2026-09-25 is an 18-day-old
# world whose Country boards are tiny; the tests' world age 2027-02-05 = release Monday + ~19 weeks) and the leaderboard
# country of each storefront's language. Mainland China IS an App Store storefront, but this app is not offered there (PLAN
# T5 11:50: CHN excluded from its 174 territories; a game in China needs a publishing licence), so the zh-Hans screenshots
# show the board of a storefront that sells it in Simplified Chinese: Singapore.
STORE_NOW = "2027-02-05T12:00:00Z"
STORE_COUNTRY = {"en": "US", "tr": "TR", "de": "DE", "fr": "FR", "es": "ES", "it": "IT", "pt-BR": "BR", "ja": "JP", "ko": "KR",
                 "zh-Hans": "SG", "pl": "PL", "sk": "SK", "sl": "SI"}


STORE_LOC = {"en": "en-US", "de": "de-DE", "fr": "fr-FR", "es": "es-ES", "it": "it", "pt-BR": "pt-BR", "tr": "tr", "ja": "ja",
             "ko": "ko", "zh-Hans": "zh-Hans", "pl": "pl", "sk": "sk", "sl": "sl-SI"}


def axe_path():
    """AXe (a simulator HID client: real touches, no host mouse). XcodeBuildMCP bundles it; $AXE overrides."""
    import glob
    for c in [os.environ.get("AXE", "")] + sorted(glob.glob(os.path.expanduser(
            "~/.npm-cache/_npx/*/node_modules/xcodebuildmcp/bundled/axe"))):
        if c and os.access(c, os.X_OK):
            return c
    return None


def store_args(entry_args, lang):
    """The store-capture extras an entry does not set itself: the world age and the storefront's leaderboard country."""
    extra = []
    if "-pc.now" not in entry_args:
        extra += ["-pc.now", STORE_NOW]
    if "-pc.socialCountry" not in entry_args:
        extra += ["-pc.socialCountry", STORE_COUNTRY.get(lang, "US")]
    return extra


def release_app_problem(slot):
    """None when slot's Release product is a store-grade build; else why not (store captures refuse Debug products)."""
    udid = SLOTS[slot]
    app = os.path.join(ROOT, "build", f"dd-{slot}", "Build", "Products", "Release-iphonesimulator", "ArrowOut.app")
    if not os.path.isdir(app):
        return f"no Release build at {app} (CONFIG=Release tools/build.sh {slot})"
    if os.path.exists(os.path.join(app, "ArrowOut.debug.dylib")):
        return f"{app} carries ArrowOut.debug.dylib: not a Release build"
    with open(os.path.join(app, "ArrowOut"), "rb") as f:
        binary = f.read()
    if b"Test store: nothing is charged" in binary or b"PC-DEBUG-PLACEHOLDER" in binary:
        return f"{app} carries the DEBUG FakeStore chip / placeholder strings"
    return None
SRGB = "/System/Library/ColorSync/Profiles/sRGB Profile.icc"


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def container(udid):
    r = sh(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"])
    return r.stdout.strip() if r.returncode == 0 else None


def simlog(udid, slot):
    return os.path.expanduser(f"~/Library/Developer/CoreSimulator/Devices/{udid}/data/tmp/pc-run-{slot}.log")


def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def probe_ok(p, cond):
    if p is None:
        return False
    for key, want in cond.items():
        have = p.get(key)
        if want is True:
            if not have:
                return False
        elif isinstance(want, dict) and ("min" in want or "max" in want):
            n = len(have) if isinstance(have, list) else have
            if not isinstance(n, (int, float)):
                return False
            if "min" in want and n < want["min"]:
                return False
            if "max" in want and n > want["max"]:
                return False
        elif have != want:
            return False
    return True


def shoot(udid, out_png):
    raw = out_png + ".raw.png"
    sh(["xcrun", "simctl", "io", udid, "screenshot", "--type=png", "--mask=ignored", raw])
    if not os.path.exists(raw):
        return False
    sh(["sips", "-m", SRGB, raw, "--out", out_png])
    os.remove(raw)
    return os.path.exists(out_png)


def is_placeholder(png):
    """A blank frame (launch screen, an empty placeholder): one flat colour over > FLAT_MAX of the frame."""
    try:
        return flat_check.flat_fraction(png)[0] > FLAT_MAX
    except Exception:
        return False


def run_actions(actions, udid, data, logpath, trace):
    """S1: the entry's "actions" (see the module doc). Appends what happened to `trace`; False = a step failed."""
    probe_path = os.path.join(data, "Documents", "probe.json") if data else None

    def log_has(text, since):
        try:
            with open(logpath, errors="replace") as f:
                f.seek(since)
                return text in f.read()
        except FileNotFoundError:
            return False

    def log_size():
        try:
            return os.path.getsize(logpath)
        except OSError:
            return 0

    step_state = {}
    for step in actions:
        t0 = time.time()
        if "sleep" in step:
            time.sleep(step["sleep"])
            trace.append({"sleep": step["sleep"]})
            continue
        if "until" in step:
            ok = False
            while time.time() - t0 < step.get("timeout", 10):
                if probe_ok(read_json(probe_path), step["until"]):
                    ok = True
                    break
                time.sleep(0.03)
            trace.append({"until": step["until"], "ok": ok, "s": round(time.time() - t0, 2)})
            if not ok:
                return False
            continue
        axe = axe_path()
        if not axe:
            trace.append({"error": "AXe not found (set $AXE)"})
            return False
        if "tapSeq" in step:
            # a planned sequence of free arrows (build/p/S1 planner: the rules mirror tools/levels/pathlib_rules.py), by id;
            # each must be free in the probe when its turn comes (a bump would cost a heart and mark the arrow red)
            done = []
            for aid in step["tapSeq"]:
                got = None
                w0 = time.time()
                while time.time() - w0 < 4:
                    q = read_json(probe_path) or {}
                    got = next((a for a in q.get("arrows", []) if a["id"] == aid and a.get("free")), None)
                    if got:
                        break
                    time.sleep(0.05)
                if not got:
                    trace.append({"tapSeq": step["tapSeq"], "done": done, "error": f"arrow {aid} not free"})
                    return False
                subprocess.run([axe, "tap", "--udid", udid, "-x", "%.1f" % got["x"], "-y", "%.1f" % got["y"]],
                               capture_output=True, text=True)
                done.append(aid)
                time.sleep(step.get("gap", 0.15))
            trace.append({"tapSeq": done, "s": round(time.time() - t0, 2)})
            continue
        if "clearUntil" in step:
            # tap free arrows that are NOT wanted (farthest from the wanted ones first) until one wanted arrow is free
            want = step["clearUntil"]["want"]
            ok, taps = False, []
            for _ in range(step["clearUntil"].get("maxTaps", 20)):
                p = read_json(probe_path) or {}
                arrows = p.get("arrows", [])
                ready = [a["id"] for a in arrows if a["id"] in want and a.get("free")]
                if ready:
                    ok = True
                    step_state["wanted"] = ready[0]
                    break
                anchors = [a for a in arrows if a["id"] in want] or arrows
                cands = [a for a in arrows if a.get("free") and a["id"] not in want]
                if not cands:
                    break
                far = max(cands, key=lambda a: min((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2 for b in anchors))
                r = subprocess.run([axe, "tap", "--udid", udid, "-x", "%.1f" % far["x"], "-y", "%.1f" % far["y"]],
                                   capture_output=True, text=True)
                taps.append(far["id"])
                gone = time.time()
                while time.time() - gone < 3:           # the probe (4 Hz) drops the tapped arrow's free flag / the arrow
                    q = read_json(probe_path) or {}
                    if not any(a["id"] == far["id"] and a.get("free") for a in q.get("arrows", [])):
                        break
                    time.sleep(0.05)
            trace.append({"clearUntil": want, "tapped": taps, "ok": ok, "wanted": step_state.get("wanted"),
                          "s": round(time.time() - t0, 2)})
            if not ok:
                return False
            continue
        if "swipe" in step:
            x0, y0, x1, y1, dur = step["swipe"]
            r = subprocess.run([axe, "swipe", "--udid", udid, "--start-x", str(x0), "--start-y", str(y0), "--end-x", str(x1),
                                "--end-y", str(y1), "--duration", str(dur)], capture_output=True, text=True)
            trace.append({"swipe": step["swipe"], "rc": r.returncode, "s": round(time.time() - t0, 2)})
            if r.returncode != 0:
                return False
            continue
        cmd = [axe, "tap", "--udid", udid]
        if "tap" in step:
            cmd += ["-x", str(step["tap"][0]), "-y", str(step["tap"][1])]
        elif "tapId" in step:
            cmd += ["--id", step["tapId"], "--wait-timeout", "3"]
        elif "tapArrow" in step:
            want = step["tapArrow"]
            p = read_json(probe_path) or {}
            arrows = p.get("arrows", [])
            pick = None
            if want.get("wanted") and "wanted" in step_state:      # the arrow the last clearUntil freed
                pick = next((a for a in arrows if a["id"] == step_state["wanted"]), None)
            elif "id" in want:
                pick = next((a for a in arrows if a["id"] == want["id"]), None)
            else:
                cands = [a for a in arrows if (a.get("free") or not want.get("free")) and a["id"] not in want.get("avoid", [])]
                if "near" in want and cands:
                    nx, ny = want["near"]
                    cands.sort(key=lambda a: (a["x"] - nx) ** 2 + (a["y"] - ny) ** 2)
                pick = cands[0] if cands else None
            if pick is None:
                trace.append({"tapArrow": want, "error": "no such arrow in the probe"})
                return False
            cmd += ["-x", "%.1f" % pick["x"], "-y", "%.1f" % pick["y"]]
            trace.append({"arrow": pick})
        else:
            trace.append({"error": f"unknown action {step}"})
            return False
        mark = log_size()
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        then = step.get("then")
        if then:
            ok = False
            while time.time() - t0 < step.get("timeout", 10):
                hit = True
                if "log" in then:
                    hit = hit and log_has(then["log"], mark)
                if "probe" in then:
                    hit = hit and probe_ok(read_json(probe_path), then["probe"])
                if hit:
                    ok = True
                    break
                time.sleep(0.03)
            trace.append({"tap": cmd[4:], "then": then, "ok": ok, "s": round(time.time() - t0, 2)})
            if not ok:
                proc.kill()
                return False
        else:
            out = proc.communicate(timeout=30)[0]
            trace.append({"tap": cmd[4:], "rc": proc.returncode, "s": round(time.time() - t0, 2), "out": out.strip()[-120:]})
            if proc.returncode != 0:
                return False
    return True


def capture(entry, lang, slot, out_dir, timeout, store=False):
    udid = SLOTS[slot]
    cid = entry["id"]
    base = os.path.join(out_dir, f"{cid}-{lang}")
    data = container(udid)
    if data:
        for f in ("capture-ready.json", "probe.json"):
            try:
                os.remove(os.path.join(data, "Documents", f))
            except FileNotFoundError:
                pass
    # every capture starts from a wiped save (state carried between captures drifts: lives, coins, streaks);
    # -pc.level / -pc.lives / ... then set it up.
    reset = [] if entry.get("keepState") or "-pc.reset" in entry.get("args", []) else ["-pc.reset", "1"]
    args = ["-pc.capture", "1", "-pc.probeFile", "1"] + reset + entry.get("args", []) + LANG_ARGS[lang]
    if store:
        args += store_args(entry.get("args", []), lang)
    t0 = time.time()
    r = sh([os.path.join(ROOT, "tools", "run.sh"), slot] + args, env=dict(os.environ, CONFIG="Release") if store else None)
    if r.returncode != 0:
        return {"id": cid, "lang": lang, "ok": False, "error": "run.sh failed: " + r.stderr[-400:]}
    data = container(udid)
    ready = entry.get("ready", {"screen": ""})
    logpath = simlog(udid, slot)
    state = {}
    ok = False
    while time.time() - t0 < timeout:
        conds = []
        marker = read_json(os.path.join(data, "Documents", "capture-ready.json")) if data else None
        state["marker"] = marker
        if "screen" in ready:
            conds.append(marker is not None and str(marker.get("screen", "")).startswith(ready["screen"]))
        if "log" in ready:
            try:
                with open(logpath, errors="replace") as f:
                    conds.append(ready["log"] in f.read())
            except FileNotFoundError:
                conds.append(False)
        if "probe" in ready:
            p = read_json(os.path.join(data, "Documents", "probe.json")) if data else None
            state["probe"] = p
            conds.append(probe_ok(p, ready["probe"]))
        if all(conds):
            ok = True
            break
        time.sleep(0.25)
    t_ready = time.time() - t0
    trace = []
    acted = run_actions(entry["actions"], udid, data, logpath, trace) if ok and entry.get("actions") else True
    ok = ok and acted
    time.sleep(entry.get("wait", 0.6))
    shot_ok = shoot(udid, base + ".png")
    bursts = []
    tb = time.time()
    for k, dt in enumerate(entry.get("burst", [])):
        while time.time() - tb < dt:
            time.sleep(0.02)
        name = f"{base}@{k + 1}.png"
        if shoot(udid, name):
            bursts.append(os.path.basename(name))
    p = state.get("probe") or (read_json(os.path.join(data, "Documents", "probe.json")) if data else None)
    try:
        with open(logpath, errors="replace") as f:
            tagged = [l.rstrip() for l in f if LOG_TAG in l]
    except FileNotFoundError:
        tagged = []
    log_tail = tagged[-40:]
    boot_cap = any(BOOT_CAP_MARK in l for l in tagged)
    placeholder = shot_ok and entry.get("level") and is_placeholder(base + ".png")
    meta = {"id": cid, "lang": lang, "ok": ok and shot_ok, "ready": ok, "shot": shot_ok, "t_ready": round(t_ready, 2),
            "args": args, "ref": entry.get("ref"), "marker": state.get("marker"),
            "probe": p,
            "bursts": bursts, "bootCap": boot_cap, "placeholder": bool(placeholder), "actions": trace, "log": log_tail}
    if placeholder:
        meta["ok"] = False
    with open(base + ".json", "w") as f:
        json.dump(meta, f, indent=1)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", nargs="?", default=os.path.join(ROOT, "tools", "capture", "manifest.json"))
    ap.add_argument("--slot", default="B")
    ap.add_argument("--only", default="")
    ap.add_argument("--langs", default="")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "compare", "captures"))
    ap.add_argument("--timeout", type=float, default=60)
    ap.add_argument("--store", action="store_true",
                    help="App Store screenshots: the slot's RELEASE product only (refuses a Debug build), -pc.now %s and the "
                         "language's leaderboard country unless an entry sets them" % STORE_NOW)
    ap.add_argument("--store-dir", default="",
                    help="with --store: also write each entry that has a 'frame' to <dir>/<store locale>/<frame>.png")
    a = ap.parse_args()
    if a.store:
        why = release_app_problem(a.slot)
        if why:
            print(f"capture.py --store: {why}", file=sys.stderr)
            sys.exit(2)
    with open(a.manifest) as f:
        entries = json.load(f)["captures"]
    # the S1 store entries ("store-…") run only under --store, and --store runs only them (the V2 list is unchanged)
    entries = [e for e in entries if e["id"].startswith("store-") == bool(a.store)] if not a.only else entries
    only = [s for s in a.only.split(",") if s]
    if only:
        entries = [e for e in entries if e["id"] in only]
    os.makedirs(a.out, exist_ok=True)
    fails = 0
    for e in entries:
        langs = [l for l in (a.langs.split(",") if a.langs else e.get("langs", ["en", "tr"])) if l in e.get("langs", ["en", "tr"])]
        for lang in langs:
            for attempt in range(3):
                m = capture(e, lang, a.slot, a.out, e.get("timeout", a.timeout), store=a.store)
                # a level-first cold launch whose boot work overran SHELL's boot cap may keep a placeholder on screen (MF
                # G2/V3 defect). Record it and relaunch.
                capped = m.get("bootCap", False)
                if capped:
                    with open(os.path.join(a.out, "boot-cap-hits.txt"), "a") as f:
                        f.write(f"{time.strftime('%H:%M:%S')} {e['id']} {lang} attempt {attempt + 1}: boot work hit the boot cap"
                                f" ({'BLANK frame kept on screen' if m.get('placeholder') else 'level shown anyway'})\n")
                if m["ok"] and not (capped and e.get("level")):
                    break
            fails += 0 if m["ok"] else 1
            if m["ok"] and a.store and a.store_dir and e.get("frame"):
                dst = os.path.join(a.store_dir, STORE_LOC.get(lang, lang), f"{e['frame']}.png")
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(os.path.join(a.out, f"{e['id']}-{lang}.png"), dst)
            print(f"{'OK ' if m['ok'] else 'BAD'} {e['id']:<18} {lang}  ready {m.get('t_ready')} s  "
                  f"marker {(m.get('marker') or {}).get('screen')}  {m.get('error', '')}", flush=True)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
