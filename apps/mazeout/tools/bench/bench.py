#!/usr/bin/env python3
"""Host-side performance bench for Arrow Out (GAMEPROMPT §8.3 "Performance", SPEC-architecture §10, V3). Entry: tools/bench.sh.

Adapted from apps/matchfactory/tools/bench/bench.py (e10a076): the slot/simulator plumbing, host-load records, the debug-HUD
OCR, the lab / launch / level / soak runners and heapdiff. V3 (2026-09-26) changes:
  - every number is taken in RELEASE (SPEC-architecture §2.5 item 1): the app is build/dd-<slot>/Build/Products/
    $CONFIG-iphonesimulator/ArrowOut.app with CONFIG defaulting to Measure here, or $BENCH_APP (a frozen copy).
    F3-A (SPEC.md ruling 52(a), 2026-09-29): the Release (store) build no longer carries the frame watch / GlitchRun /
    the tab loop; the Measure configuration is Release's settings + PC_MEASURE (project.yml), so its numbers are the
    store build's: `CONFIG=Measure tools/build.sh <slot>`. A launch that asks for a measurement flag on an app without
    the frame watch EXITS (MEASURE_MARK below) instead of reporting "0 frames > 20 ms" from an app that cannot see them;
  - an IDLE GATE before every launch (1-min load < --load-max, default 4; free swap >= 400 MB; memory pressure normal;
    disk >= 3 GB), recorded with each result, and the host load sampled through every run;
  - memory from proc_pid_rusage (RUSAGE_INFO_V4: phys_footprint + the lifetime phys_footprint high-water mark; the process
    start time gives process-start -> mark timings) — no `footprint`/`vmmap` walk that could stall the app mid-soak;
  - the §9.3 log contract's additional marks (MARKS below): the frame watch (`-pc.frameWatch 1`: every frame > 20 ms on
    every screen + 10 s summaries), the board's hitch/first-effect marks, per-tap latency (`[PC][perf] tap`), the same-frame
    feedback line, warm-up parts, audio route latency, tutorials, unlocks, events, lab done, generated levels (L151+),
    popup present -> visible, level-start costs; `analyze()` turns a log into the §10.2 rows and `logstats` prints them;
  - the §10.2 budgets (BUDGET).

Subcommands (slot = A | B, that slot's simulator only; nothing else is touched):
  lab    <slot> <scenario> [--timeout S] [-- args]   BoardLab scenario (`-pc.go boardlab -pc.lab <scenario>`): waits for
                                                      Documents/lab-ready.json, archives it + lab-perf.json + the log +
                                                      footprint samples + the log analysis
  launch <slot> [--warm N] [--no-first] [--home N]   cold-launch timings: fresh install with NO arguments (the real first
                                                      run), fresh install with -pc.level 5, N warm launches (-pc.level 5),
                                                      --home N warm launches to home (-pc.level 40); -pc.frameWatch 1 on
                                                      every launch (measurement only)
  screens <slot> --targets go:<screen>,popup:<id>,... [--level N]
                                                      first-open cost of shell screens / popups (warm launches)
  level  <slot> <level> [--seconds S] [--autoplay] [--no-shots]
                                                      one level in the full game screen, sampled (idle or autoplayed)
  soak   <slot> [--stop 30] [--start 1] [--timeout S] [--interval S] [-- args]
                                                      fresh install, `-pc.reset 1 -pc.autoplay 1 -pc.autoplayStop N
                                                      -pc.hud debug` (+ args); samples footprint + load every interval;
                                                      ends at the autoplay's done line, a dead process or the timeout;
                                                      copies Documents/bench-*.json; then runs `report`
  report <soak dir>                                   per-attempt bench-L<nnn>.json + soak-summary.json (+ the analysis)
  logstats <log> [--json OUT]                         the §10.2 rows of any [PC] log (frames by phase, taps, level starts,
                                                      launch, warm-up, first effects, popups, generated levels)
  heapdiff <before> <after>                           `heap -s -q` outputs -> the classes that grew
Long runs: start `soak`/`lab soak` in the background and poll <dir>/status.json (soak) or the log.
Every result carries the host's load and swap: this Mac runs other agents' simulators, so a simulator number needs an idle
baseline, and the verdict is taken on the phone (D1).
"""
import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import statistics
import struct
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SLOTS = {"A": ("177520B6-4889-46C2-BDD9-155813D2B175", "Maze A"),      # = tools/slot.sh
         "B": ("B80EDB24-6280-4C52-A63F-E8AADD245017", "Maze B")}
BUNDLE = "com.manycode.arrowout"
APP_NAME = "ArrowOut"
BENCH = os.path.join(ROOT, "build", "bench")
OCR_SRC = os.path.join(ROOT, "tools", "bench", "hudocr.swift")
OCR_BIN = os.path.join(BENCH, ".tools", "hudocr")
LEVELS_DIR = os.path.join(ROOT, "App", "Resources", "Levels")
CONFIG = os.environ.get("CONFIG", "Measure")          # V3: Release settings (§2.5 item 1); F3-A: + PC_MEASURE (the hooks)
# F3-A: FrameWatch.start's log text (> 15 bytes, so a C string in the binary): present in Debug / Measure, absent from Release
MEASURE_MARK = b"watch on (every presented frame > 20 ms is logged)"
MEASURE_FLAGS = ("-pc.frameWatch", "-pc.glitchRun", "-pc.tabLoop")
APP_OVERRIDE = os.environ.get("BENCH_APP")             # a frozen .app (e.g. build/v3/app/ArrowOut.app)

# §10.2 budgets (SPEC-architecture; the device verdict is D1's, the simulator rows gate the WPs).
BUDGET = {
    "hitch_ms": 20.0,                    # every row: a frame > 20 ms is a dropped frame (60 Hz)
    "sim_fps_min": 59.5, "sim_p99_ms": 20.0,              # frames on the simulator (loaded Mac): avg + p99
    "device_p99_ms": 16.7,
    "touch_to_handler_p99_ms": 4.0, "handler_to_commit_p99_ms": 4.0,
    "tap_handler_solid_p99_ms": 2.0, "tap_handler_rainbow_p99_ms": 4.0,
    "sameframe_spread_ms": 1.0, "audio_route_ms": 16.7,
    "play_to_board_ms": 50.0,            # level start: Play -> first board frame (hard cut)
    "board_build_main_ms": 5.0,          # level start: board build, main thread
    "loading_visible_s": 0.5,            # first launch: the Loading screen on screen after launch
    "boot_warmup_s": 2.5, "boot_warmup_cap_s": 4.0,       # first launch: boot + warm-up (device; cap)
    "mem_play_mb": 160.0, "mem_peak_mb": 220.0, "mem_growth_mb": 10.0,
    "mem_board_mb": 40.0, "sprite_cache_mb": 48.0, "layers_peak": 1500,
    "social_page50_ms": 2.0, "hud_write_ms": 1.0, "autosave_main_ms": 1.0,
}

# ---- the app's log grammar (§9.3, App/Support/Log.swift ◆) ---------------------------------------------------------
# Every line "<systemUptime> [PC][<category>] <message>", errors "[PC][<category>][ERROR] <message>". The bench measures
# ONLY what these marks say; a producer that changes a mark's text changes this table in the same WP (§3.3).
LOGLINE = re.compile(r"^(\d+\.\d+) \[PC\]\[(\w+)\](\[ERROR\])? (.*)$")
MARKS = {                         # key: (category, regex on the message)
    # --- §9.3 confirmed
    "first_screen":  ("launch", r"^(\w+)(?:\(.*?\))? fully visible"),   # group 1 = screen name (home, level ...)
    "launch_done":   ("launch", r"^cold launch summary .*?total ([\d.]+) s"),
    "level_go":      ("router", r"^go level\(L(\d+)\)"),                  # Play tapped / autoplay starts a level
    "level_visible": ("router", r"^level\(L(\d+)\) visible"),
    "board_ready":   ("board", r"^ready L(\d+): (\d+) arrows"),           # layers built, first frame committed
    "play":          ("game", r"^play L(\d+)"),                            # the timer starts (first tap)
    "won":           ("win", r"^L(\d+) won: (\d+) s left, (\d) hearts"),
    "lost":          ("fail", r"^L(\d+) lost: (\w+)"),                     # timeUp | hearts | quit | killed
    "teardown":      ("game", r"^teardown L(\d+)"),
    "home_visible":  ("router", r"^home visible"),
    "go_home":       ("router", r"^go home"),
    "hitch":         ("board", r"^hitch ([\d.]+) ms (.*)$"),              # board PerfMonitor: any frame > 20 ms in play
    "autoplay_done": ("autoplay", r"^done: L(\d+)-L(\d+) won (\d+)/(\d+) bumps (\d+)"),
    # --- §9.3 "additional marks" (V3)
    "tap":           ("perf", r"^tap L(\d+) a(\S+) touch→handler ([\-\d.]+) handler→commit ([\-\d.]+) commit→vsync ([\-\d.]+)"
                              r"(?: \(handler ([\-\d.]+))?"),
    "sameframe":     ("sameframe", r"^L(\d+) a(\S+) "),             # fields parsed by name (their order varies)
    "warmup":        ("warmup", r"^(.+?) ([\d.]+) s\b"),
    "warmup_staged": ("warmup", r"^(.+?) (\d+) staged over ([\d.]+) s"),
    "audio_latency": ("audio", r"^latency io ([\d.]+) out ([\d.]+)"),
    "tutorial_show": ("tutorial", r"^show (\w+) L(\d+)"),
    "unlock_show":   ("unlock", r"^show (\w+) L(\d+)"),
    "event":         ("event", r"^(.+)$"),
    "lab_done":      ("lab", r"^(\S+) done"),
    "generated":     ("level", r"^generated L(\d+) in ([\d.]+) ms \((\w+), seeds (\d+), validate ([\d.]+) ms\)"),
    "loading_visible": ("launch", r"^loading visible"),
    "boot_started":  ("boot", r"^boot sequence started \(([\d.]+) s after launch\)"),
    "first_effect":  ("board", r"^first:(\S+) max ([\d.]+) ms over (\d+) frames"),
    "game_start":    ("game", r"^start L(\d+) attempt (\d+) stage (\d+)/(\d+):.*\(main ([\d.]+) ms\)"),
    "board_load":    ("board", r"^load L(\d+) main ([\d.]+) ms, to the end of the commit ([\d.]+) ms"),
    "frame_hitch":   ("frame", r"^hitch ([\d.]+) ms (.+?)(?: cpu ([\d.]+))?$"),   # -pc.frameWatch 1 (every screen; A3: + main-thread cpu ms)
    "frame_summary": ("frame", r"^summary (.+?): frames (\d+) over20 (\d+) max ([\d.]+)"),
    "popup_present": ("popup", r"^present (\S+)"),
    "popup_visible": ("popup", r"^visible (\S+) ([\d.]+) ms after present"),
    "stage_transition": ("board", r"^stage transition → L(\d+)"),
    "stage_done":    ("board", r"^stageTransitionDone"),
    "tabs_shop":     ("shop", r"^open \(tab\)"),
    "tabs_board":    ("leaderboard", r"^open tab"),
    "boardlab_seg":  ("boardlab", r"^soak (\S+) (max|fit) over20 (\d+) \(load (\d+), play (\d+)\) max ([\d.]+) ms"),
    # --- V3 restart (2026-09-27): the LOGO-IMPL celebration beats, FIX-A1's router cut probe, S1's frame probe
    "celebration_start": ("fx", r"^celebration (\w+) start"),
    "celebration_logo":  ("fx", r"^celebration logo built W\+([\d.]+) \((\d+) layers, ([\d.]+) ms\)"),
    "celebration_panel": ("fx", r"^celebration panel due W\+([\d.]+)"),
    "celebration_skip":  ("fx", r"^celebration skipped at W\+([\d.]+)"),
    "win_w":         ("win", r"^L(\d+) W: clear wave"),
    "cut":           ("perf", r"^cut (\S+) .*?total ([\d.]+)(?: footprint (\d+) MB)?"),
    "frame_probe":   ("perf", r"^(.+?) frames (\d+) max ([\d.]+) ms over20 (\d+)"),
    "prewarm_done":  ("warmup", r"^prewarm (\d+)/(\d+) items staged over ([\d.]+) s"),
}
_MARK_RE = {k: (c, re.compile(r)) for k, (c, r) in MARKS.items()}

# ---- the debug HUD (`-pc.hud debug`), read back from screenshots (§9.6) ----------------------------------------------
HUD_CROP = "0,95,260,60"
NUM = r"(\d+(?:\.\d+)?)"
HUD1 = re.compile(NUM + r"\.?\s*fps\s+p95\s+" + NUM + r"\.?\s+p99\s+" + NUM)
HUD2 = re.compile(r"(\d+)\s*MB\s+(\d+)\s*layers\s+(\d+)\s*movers")


def mark(key, cat, msg):
    c, rx = _MARK_RE[key]
    return rx.search(msg) if c == cat else None


def uptime():
    """The clock the app logs with (ProcessInfo.systemUptime = mach_absolute_time, shared with the simulator)."""
    return time.clock_gettime(time.CLOCK_UPTIME_RAW)


def sh(cmd, timeout=120, check=True):
    """Runs cmd. With check=False a timeout or failure returns "" (a stuck simctl under host load must never end a
    long run); with check=True both raise."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        if check:
            raise
        sys.stderr.write(f"bench: timeout after {timeout} s: {' '.join(cmd)[:160]}\n")
        return ""
    if check and r.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> {r.returncode}: {r.stderr.strip()[:400]}")
    return r.stdout


def stamp():
    return time.strftime("%Y%m%d-%H%M%S")


# ---- process memory without walking the target's VM (proc_pid_rusage, RUSAGE_INFO_V4) ------------------------------
_LIBC = ctypes.CDLL("/usr/lib/libSystem.B.dylib")


class _Timebase(ctypes.Structure):
    _fields_ = [("numer", ctypes.c_uint32), ("denom", ctypes.c_uint32)]


_TB = _Timebase()
_LIBC.mach_timebase_info(ctypes.byref(_TB))


def rusage(pid):
    """{mb, peakMB, startUptime} of pid from proc_pid_rusage(RUSAGE_INFO_V4): ri_phys_footprint (offset 72),
    ri_lifetime_max_phys_footprint (240) and ri_proc_start_abstime (80, mach ticks -> the app's uptime clock). Checked
    against `footprint -p` (identical bytes). None when the process is gone."""
    if not pid:
        return None
    buf = ctypes.create_string_buffer(512)
    if _LIBC.proc_pid_rusage(ctypes.c_int(pid), ctypes.c_int(4), buf) != 0:
        return None
    phys = struct.unpack_from("<Q", buf, 72)[0]
    peak = struct.unpack_from("<Q", buf, 240)[0]
    start = struct.unpack_from("<Q", buf, 80)[0]
    return {"mb": round(phys / 1048576, 1), "peakMB": round(peak / 1048576, 1),
            "startUptime": start * _TB.numer / _TB.denom / 1e9}


def footprint(pid):
    """(phys_footprint MB, phys_footprint high-water MB) of the simulator app process, or (None, None)."""
    r = rusage(pid)
    return (r["mb"], r["peakMB"]) if r else (None, None)


# ---- host state + the idle gate ---------------------------------------------------------------------------------------

def swap_free_mb():
    try:
        m = re.search(r"free = ([\d.]+)M", sh(["sysctl", "vm.swapusage"]))
        return float(m.group(1)) if m else None
    except Exception:
        return None


def pressure_level():
    """kern.memorystatus_vm_pressure_level: 1 normal, 2 warn, 4 critical."""
    try:
        return int(sh(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip())
    except Exception:
        return None


def disk_free_gb():
    st = os.statvfs("/")
    return round(st.f_bavail * st.f_frsize / 1e9, 1)


def host_state(full=True):
    d = {"load": [round(x, 2) for x in os.getloadavg()], "wall": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    if not full:
        return d
    d["swapFreeMB"] = swap_free_mb()
    d["pressure"] = pressure_level()
    try:
        m = re.search(r"(\d+)%", sh(["memory_pressure", "-Q"], timeout=20))
        d["memFreePct"] = int(m.group(1)) if m else None
    except Exception:
        d["memFreePct"] = None
    try:
        d["diskFreeGB"] = disk_free_gb()
    except Exception:
        pass
    try:
        # the other slot's app renders on the same GPU: record whether it is running and its CPU
        ps = sh(["ps", "-Ao", "pcpu,command"], check=False)
        d["simApps"] = {name: [float(l.split()[0]) for l in ps.splitlines()
                               if udid in l and f"{APP_NAME}.app/{APP_NAME}" in l]
                        for name, (udid, _) in SLOTS.items()}
        d["xcodebuilds"] = sum(1 for l in ps.splitlines() if "/usr/bin/xcodebuild" in l)
        d["swiftFrontends"] = sum(1 for l in ps.splitlines() if "swift-frontend" in l)
    except Exception:
        d["simApps"] = None
    try:
        d["booted"] = re.findall(r"^\s+(.+?) \([0-9A-F-]{36}\) \(Booted\)",
                                 sh(["xcrun", "simctl", "list", "devices", "booted"]), re.M)
    except Exception:
        d["booted"] = None
    return d


def mem_free_pct():
    try:
        m = re.search(r"(\d+)%", sh(["memory_pressure", "-Q"], timeout=20))
        return int(m.group(1)) if m else None
    except Exception:
        return None


def wait_idle(load_max, max_wait=900, step=20, who="bench"):
    """SPEC.md §6 + V3: start a timed run only on an idle machine: 1-min load < load_max, free swap >= 400 MB, memory
    pressure not critical, disk >= 3 GB. Waits in `step` s up to max_wait s; returns the gate record (ok False = timed
    out, the run goes ahead and says so).
    V3 restart (2026-09-27): the kernel pressure level (kern.memorystatus_vm_pressure_level 1 normal / 2 warn / 4
    critical) sits at 2 on this Mac whenever a simulator is booted, even at 40-65 % free memory; the 09-26 gate demanded
    1, never passed, waited max_wait before EVERY launch and then ran at whatever load came (build/v3/runs-0926). The gate
    now follows SPEC.md §6 ("pressure is critical" = wait) and records the level and `memory_pressure -Q`'s free %."""
    t0 = time.time()
    while True:
        l1 = os.getloadavg()[0]
        sw = swap_free_mb()
        pr = pressure_level()
        dk = disk_free_gb()
        ok = l1 < load_max and (sw is None or sw >= 400) and (pr is None or pr < 4) and dk >= 3
        if ok or time.time() - t0 >= max_wait:
            g = {"ok": ok, "waitedS": round(time.time() - t0), "load1": round(l1, 2), "loadMax": load_max,
                 "swapFreeMB": sw, "pressure": pr, "memFreePct": mem_free_pct(), "diskFreeGB": dk}
            if not ok:
                sys.stderr.write(f"{who}: machine not idle after {g['waitedS']} s ({g}); running anyway, recorded\n")
            return g
        time.sleep(step)


# ---- the slot -----------------------------------------------------------------------------------------------------------

class Slot:
    def __init__(self, s):
        if s not in SLOTS:
            sys.exit(f"slot must be A or B, not {s}")
        self.slot, (self.udid, self.name) = s, SLOTS[s]
        self.app = APP_OVERRIDE or os.path.join(ROOT, "build", f"dd-{s}", "Build", "Products",
                                                f"{CONFIG}-iphonesimulator", f"{APP_NAME}.app")
        self.simlog = os.path.expanduser(f"~/Library/Developer/CoreSimulator/Devices/{self.udid}/data/tmp/pc-run-{s}.log")
        self.log = os.path.join(ROOT, "build", f"run-{s}.log")

    def booted(self):
        return f"{self.udid}) (Booted)" in sh(["xcrun", "simctl", "list", "devices"])

    def boot(self):
        if not self.booted():
            sh(["xcrun", "simctl", "boot", self.udid], check=False)
            sh(["xcrun", "simctl", "bootstatus", self.udid, "-b"], timeout=240)
        c = os.path.expanduser(f"~/Library/Developer/CoreSimulator/Devices/{self.udid}/data/Library/Caches/"
                               "com.apple.nsurlsessiond")
        if os.path.isdir(c):
            try:
                os.chmod(c, 0)                     # = tools/slot.sh sim_boot: no background asset downloads
            except OSError:
                pass

    def terminate(self):
        sh(["xcrun", "simctl", "terminate", self.udid, BUNDLE], check=False)

    def install(self):
        if not os.path.isdir(self.app):
            sys.exit(f"{self.app} missing: run CONFIG={CONFIG} tools/build.sh {self.slot} (or set BENCH_APP)")
        sh(["xcrun", "simctl", "install", self.udid, self.app], timeout=180)

    def uninstall(self):
        sh(["xcrun", "simctl", "uninstall", self.udid, BUNDLE], check=False)

    def has_measure_hooks(self):
        """F3-A: True when the app's binary carries the frame watch (Debug / Measure), False for a Release (store) build."""
        if not hasattr(self, "_hooks"):
            b = os.path.join(self.app, APP_NAME)
            self._hooks = os.path.exists(b) and MEASURE_MARK in open(b, "rb").read()
        return self._hooks

    def launch(self, args):
        """Launches with the console log in the simulator's own tmp (the sandbox-safe path tools/run.sh uses)."""
        asked = [f for f in MEASURE_FLAGS if f in args]
        if asked and not self.has_measure_hooks():
            sys.exit(f"{self.app}: {', '.join(asked)} asked, but this app has no measurement hooks (a Release/store build, "
                     f"SPEC.md ruling 52(a)); build CONFIG=Measure tools/build.sh {self.slot} (or pass --no-watch)")
        os.makedirs(os.path.dirname(self.simlog), exist_ok=True)
        open(self.simlog, "w").close()
        os.makedirs(os.path.dirname(self.log), exist_ok=True)
        if os.path.islink(self.log) or os.path.exists(self.log):
            os.remove(self.log)
        os.symlink(self.simlog, self.log)
        t0 = uptime()
        out = sh(["xcrun", "simctl", "launch", "--terminate-running-process", f"--stdout={self.simlog}",
                  f"--stderr={self.simlog}", self.udid, BUNDLE] + list(args))
        m = re.search(r":\s*(\d+)", out)
        return (int(m.group(1)) if m else None), t0

    def documents(self):
        try:
            return os.path.join(sh(["xcrun", "simctl", "get_app_container", self.udid, BUNDLE, "data"]).strip(),
                                "Documents")
        except Exception:
            return None

    def screenshot(self, path):
        sh(["xcrun", "simctl", "io", self.udid, "screenshot", "--type=png", path], timeout=30, check=False)
        return os.path.exists(path)

    def read_log(self):
        try:
            with open(self.simlog, errors="replace") as f:
                return f.read()
        except FileNotFoundError:
            return ""


def consume_prompt(slot):
    """V3 restart: the iOS notification alert is asked ONCE per install over Loading and Loading waits for the answer
    (G2, SPEC.md §5 item 5); nothing on the simulator answers it, so a measured launch that follows an install where it
    was suppressed (autoplay/uitest) would sit on Loading (the 09-26 firstfx runs failed this way; the 09-27 r1 lab waited
    551 s). The flag is saved BEFORE asking, so one unmeasured launch that reaches the ask and is terminated consumes it.
    Returns what the log said."""
    slot.terminate()
    slot.launch(["-pc.go", "home", "-pc.seed", "1"])
    said = wait_for(lambda: next((w for w in ("prompt shown", "prompt suppressed", "cold launch summary")
                                  if w in slot.read_log()), None), 25) or "timeout"
    time.sleep(0.5)
    slot.terminate()
    time.sleep(1.0)
    return said


def alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def ocr_bin():
    if not os.path.exists(OCR_BIN) or os.path.getmtime(OCR_BIN) < os.path.getmtime(OCR_SRC):
        os.makedirs(os.path.dirname(OCR_BIN), exist_ok=True)
        sh(["swiftc", "-O", "-o", OCR_BIN, OCR_SRC], timeout=200)
    return OCR_BIN


def read_hud(png):
    out = sh([ocr_bin(), "--crop", HUD_CROP, png], timeout=30, check=False).strip().splitlines()
    if not out:
        return None
    try:
        lines = json.loads(out[0]).get("lines", [])
    except ValueError:
        return None
    text = " | ".join(lines)
    d = {"text": text}
    try:
        m = HUD1.search(text)
        if m:
            d.update(fps=float(m.group(1)), p95=float(m.group(2)), p99=float(m.group(3)))
        m = HUD2.search(text)
        if m:
            d.update(appMB=int(m.group(1)), layers=int(m.group(2)), movers=int(m.group(3)))
    except ValueError:
        return None
    return d if "fps" in d else None


def wait_for(pred, timeout, step=0.5):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(step)
    return None


def crash_reports(since_wall):
    d = os.path.expanduser("~/Library/Logs/DiagnosticReports")
    out = []
    for f in os.listdir(d) if os.path.isdir(d) else []:
        p = os.path.join(d, f)
        if f.startswith(APP_NAME) and os.path.getmtime(p) >= since_wall:
            out.append(p)
    return out


def git_head():
    try:
        return sh(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"]).strip()
    except Exception:
        return None


_SHA = {}


def build_info(slot):
    exe = os.path.join(slot.app, APP_NAME)
    if exe not in _SHA and os.path.exists(exe):
        h = hashlib.sha256()
        with open(exe, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        _SHA[exe] = h.hexdigest()[:16]
    return {"config": "BENCH_APP" if APP_OVERRIDE else CONFIG, "app": os.path.relpath(slot.app, ROOT),
            "binarySha256": _SHA.get(exe), "gitHead": git_head(),
            "binaryMtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(exe)))
            if os.path.exists(exe) else None,
            "simulator": f"{slot.name} {slot.udid}", "machine": sh(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()}


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, sort_keys=False, default=str)
    return path


def parse_log(text):
    ev = []
    for line in text.splitlines():
        m = LOGLINE.match(line)
        if m:
            ev.append((float(m.group(1)), m.group(2), bool(m.group(3)), m.group(4)))
    return ev


def log_has(slot, key):
    return any(mark(key, c, m) for _, c, _, m in parse_log(slot.read_log()))


def pct(vals, p):
    v = sorted(vals)
    if not v:
        return None
    return v[min(len(v) - 1, int(round((len(v) - 1) * p)))]


def stat(vals):
    vals = [x for x in vals if x is not None]
    if not vals:
        return None
    return {"n": len(vals), "min": round(min(vals), 2), "median": round(statistics.median(vals), 2),
            "p99": round(pct(vals, 0.99), 2), "mean": round(statistics.mean(vals), 2), "max": round(max(vals), 2)}


# ---------------------------------------------------------------------------------------------------------- analysis

def analyze(text):
    """The §10.2 rows of one [PC] log: frames by phase (frame watch + board monitor), taps (latency, same-frame), level
    starts, launch, warm-up, first effects, popups, generated levels, lab segments, errors. Pure log parsing."""
    ev = parse_log(text)
    A = {"lines": len(ev)}
    if not ev:
        return A
    t_first = ev[0][0]

    # ---- phase markers: every frame-watch hitch is attributed to the latest marker before it
    markers = [(t_first, "boot", "")]
    for t, c, e, m in ev:
        if mark("loading_visible", c, m):
            markers.append((t, "loading", ""))
        elif (x := mark("level_go", c, m)):
            markers.append((t, "levelStart", "L" + x.group(1)))
        elif (x := mark("play", c, m)):
            markers.append((t, "play", "L" + x.group(1)))
        elif (x := mark("stage_transition", c, m)):
            markers.append((t, "stageTransition", "L" + x.group(1)))
        elif (x := mark("won", c, m)):
            markers.append((t, "win", "L" + x.group(1)))
        elif (x := mark("lost", c, m)):
            markers.append((t, "fail", "L" + x.group(1)))
        elif mark("go_home", c, m) or mark("home_visible", c, m):
            if not markers or markers[-1][1] not in ("homeArrival",):
                markers.append((t, "homeArrival", ""))
        elif mark("tabs_shop", c, m) or mark("tabs_board", c, m):
            if markers and markers[-1][1] == "homeArrival":
                markers.append((t, "homeTabs", ""))
        elif (x := mark("popup_present", c, m)):
            markers.append((t, "popup", x.group(1)))
        elif (x := mark("celebration_start", c, m)):
            markers.append((t, "celebration", x.group(1)))
    markers.sort(key=lambda r: r[0])

    def phase_at(t):
        cur = markers[0]
        prev_non_popup = markers[0]
        for mk in markers:
            if mk[0] > t:
                break
            cur = mk
            if mk[1] != "popup":
                prev_non_popup = mk
        ph, det = cur[1], cur[2]
        if ph == "popup":
            # a hitch within 0.6 s of a present belongs to that popup's presentation; later, to the screen underneath
            if t - cur[0] <= 0.6:
                return "popup:" + det, det
            ph, det = prev_non_popup[1], prev_non_popup[2]
            cur = prev_non_popup
        if ph == "homeArrival" and t - cur[0] > 3.0:
            return "homeIdle", det
        if ph == "homeTabs" and t - cur[0] > 1.0:
            return "homeIdle", det
        if ph == "win" and t - cur[0] > 6.0:
            return "winIdle", det
        if ph == "celebration" and t - cur[0] > 4.6:
            return "winIdle", det
        return ph, det

    hitches = []
    for t, c, e, m in ev:
        x = mark("frame_hitch", c, m)
        if x:
            ph, det = phase_at(t)
            hitches.append({"t": t, "ms": float(x.group(1)), "screen": x.group(2), "phase": ph, "at": det, "src": "frame"})
    board_hitches = []
    for t, c, e, m in ev:
        x = mark("hitch", c, m)
        if x:
            board_hitches.append({"t": t, "ms": float(x.group(1)), "ctx": x.group(2), "phase": phase_at(t)[0]})
    summaries = {}
    frames_total = over_total = 0
    max_total = 0.0
    for t, c, e, m in ev:
        x = mark("frame_summary", c, m)
        if x:
            scr = re.sub(r"L\d+", "Ln", x.group(1))
            s = summaries.setdefault(scr, {"frames": 0, "over20": 0, "max": 0.0})
            s["frames"] += int(x.group(2))
            s["over20"] += int(x.group(3))
            s["max"] = max(s["max"], float(x.group(4)))
            frames_total += int(x.group(2))
            over_total += int(x.group(3))
            max_total = max(max_total, float(x.group(4)))
    by_phase = {}
    for h in hitches:
        b = by_phase.setdefault(h["phase"], [])
        b.append(h["ms"])
    A["frames"] = {
        "watch": bool(summaries) or any(mark("frame_hitch", c, m) for _, c, _, m in ev),
        "total": frames_total, "over20": over_total, "maxMs": max_total, "byScreen": summaries,
        "hitchesByPhase": {k: {"n": len(v), "max": round(max(v), 1), "median": round(statistics.median(v), 1)}
                           for k, v in sorted(by_phase.items(), key=lambda kv: -len(kv[1]))},
        "hitches": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items()} for h in hitches],
        "board": {"n": len(board_hitches), "maxMs": max([h["ms"] for h in board_hitches] or [0]),
                  "list": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in h.items()} for h in board_hitches]},
    }

    # ---- taps: latency + the same-frame line
    taps = []
    for t, c, e, m in ev:
        x = mark("tap", c, m)
        if x:
            taps.append({"t": t, "L": int(x.group(1)), "a": x.group(2), "touchToHandler": float(x.group(3)),
                         "handlerToCommit": float(x.group(4)), "commitToVsync": float(x.group(5)),
                         "handler": float(x.group(6)) if x.group(6) else None})
    real = [tp for tp in taps if tp["a"] != "-"]           # "a-" = a tap on nothing (an empty cell)
    sf = []

    def field(msg, rx):
        y = re.search(rx, msg)
        return float(y.group(1)) if y else None

    for t, c, e, m in ev:
        x = mark("sameframe", c, m)
        if x:
            sf.append({"t": t, "L": int(x.group(1)), "commit": field(m, r"\bcommit ([\-\d.]+)"),
                       "vsync": field(m, r"\bvsync \+([\-\d.]+) ms"), "build": field(m, r"\bbuild ([\d.]+) ms"),
                       "spread": field(m, r"\bspread ([\d.]+) ms"),
                       "ok": re.search(r"\bspread [\d.]+ ms OK\b", m) is not None})
    A["taps"] = {
        "n": len(real), "nEmpty": len(taps) - len(real),
        "touchToHandlerMs": stat([tp["touchToHandler"] for tp in real if tp["touchToHandler"] >= 0]),
        "handlerToCommitMs": stat([tp["handlerToCommit"] for tp in real]),
        "commitToVsyncMs": stat([tp["commitToVsync"] for tp in real]),
        "handlerMs": stat([tp["handler"] for tp in real if tp["handler"] is not None]),
        "over4msHandlerToCommit": [{"t": round(tp["t"], 3), "L": tp["L"], "a": tp["a"], "ms": tp["handlerToCommit"]}
                                   for tp in real if tp["handlerToCommit"] > 4.0][:40],
        "sameframe": {"n": len(sf), "ok": sum(1 for s in sf if s["ok"]), "spreadMs": stat([s["spread"] for s in sf]),
                      "buildMs": stat([s["build"] for s in sf]), "commitMs": stat([s["commit"] for s in sf])},
        "list": taps,
    }

    # ---- level starts (Play -> first board frame, board build, frames in [go, first tap])
    starts = []
    go = None
    for i, (t, c, e, m) in enumerate(ev):
        if (x := mark("level_go", c, m)):
            go = {"L": int(x.group(1)), "tGo": t}
            starts.append(go)
        elif go is not None:
            if (x := mark("level_visible", c, m)) and int(x.group(1)) == go["L"] and "tVisible" not in go:
                go["tVisible"] = t
            elif (x := mark("game_start", c, m)) and int(x.group(1)) == go["L"] and "startMainMs" not in go:
                go["startMainMs"] = float(x.group(5))
            elif (x := mark("board_load", c, m)) and int(x.group(1)) == go["L"] and "boardMainMs" not in go:
                go["boardMainMs"] = float(x.group(2))
                go["boardCommitMs"] = float(x.group(3))
            elif (x := mark("board_ready", c, m)) and int(x.group(1)) == go["L"] and "arrows" not in go:
                go["arrows"] = int(x.group(2))
            elif (x := mark("play", c, m)) and int(x.group(1)) == go["L"] and "tPlay" not in go:
                go["tPlay"] = t
    for s in starts:
        t_end = s.get("tPlay") or ((s.get("tVisible") or s["tGo"]) + 1.5)
        s["goToVisibleMs"] = round((s["tVisible"] - s["tGo"]) * 1000, 1) if s.get("tVisible") else None
        w = [h["ms"] for h in hitches if s["tGo"] <= h["t"] <= t_end]
        s["framesOver20"] = len(w)
        s["maxFrameMs"] = max(w) if w else None
        # V3 restart: a level started from Loading (first launch) logs `go level` while Loading is still staging its
        # warm-up; count apart the frames drawn on the level screen itself (frame-watch screen "level(...)")
        wl = [h["ms"] for h in hitches if s["tGo"] <= h["t"] <= t_end and h["screen"].startswith("level")]
        s["levelFramesOver20"] = len(wl)
        s["levelMaxFrameMs"] = max(wl) if wl else None
        s["windowS"] = round(t_end - s["tGo"], 3)
    A["levelStarts"] = {
        "n": len(starts),
        "goToVisibleMs": stat([s["goToVisibleMs"] for s in starts]),
        "boardMainMs": stat([s.get("boardMainMs") for s in starts]),
        "startMainMs": stat([s.get("startMainMs") for s in starts]),
        "withFramesOver20": sum(1 for s in starts if s["framesOver20"]),
        "withLevelFramesOver20": sum(1 for s in starts if s["levelFramesOver20"]),
        "levelFramesOver20": sum(s["levelFramesOver20"] for s in starts),
        "list": [{k: (round(v, 3) if isinstance(v, float) else v) for k, v in s.items()} for s in starts],
    }

    # ---- launch, warm-up, audio
    L = {}
    boot_after = None
    for t, c, e, m in ev:
        if (x := mark("boot_started", c, m)) and boot_after is None:
            boot_after = (t, float(x.group(1)))
        if mark("loading_visible", c, m) and "tLoadingVisible" not in L:
            L["tLoadingVisible"] = t
        if (x := mark("launch_done", c, m)) and "coldLaunchTotalS" not in L:
            L["coldLaunchTotalS"] = float(x.group(1))
            L["tLaunchDone"] = t
            L["summary"] = m
        if (x := mark("first_screen", c, m)) and "firstScreen" not in L:
            L["firstScreen"] = x.group(1)
            L["tFirstScreen"] = t
    if boot_after:
        L["processStartUptime"] = round(boot_after[0] - boot_after[1], 3)     # the app's own "after launch" clock
    A["launch"] = L
    A["warmup"] = [{"part": x.group(1), "s": float(x.group(2))} for t, c, e, m in ev
                   if (x := mark("warmup", c, m)) and not mark("warmup_staged", c, m)] + \
                  [{"part": x.group(1) + " (staged)", "items": int(x.group(2)), "s": float(x.group(3))} for t, c, e, m in ev
                   if (x := mark("warmup_staged", c, m))]
    au = [(float(x.group(1)), float(x.group(2))) for t, c, e, m in ev if (x := mark("audio_latency", c, m))]
    A["audio"] = {"ioMs": au[0][0], "outMs": au[0][1], "routeMs": round(au[0][0] + au[0][1], 2)} if au else None

    # ---- first effects, popups, tutorials, unlocks, events, generated levels, lab
    A["firstEffects"] = {x.group(1): float(x.group(2)) for t, c, e, m in ev if (x := mark("first_effect", c, m))}
    pv = {}
    for t, c, e, m in ev:
        if (x := mark("popup_visible", c, m)):
            pv.setdefault(x.group(1), []).append(float(x.group(2)))
    A["popups"] = {k: {"n": len(v), "first": v[0], "max": max(v), "median": round(statistics.median(v), 1)}
                   for k, v in pv.items()}
    A["tutorials"] = [f"{x.group(1)}@L{x.group(2)}" for t, c, e, m in ev if (x := mark("tutorial_show", c, m))]
    A["unlocks"] = [f"{x.group(1)}@L{x.group(2)}" for t, c, e, m in ev if (x := mark("unlock_show", c, m))]
    A["events"] = [m for t, c, e, m in ev if c == "event" and "no event counted" not in m][:60]
    gen = [{"L": int(x.group(1)), "totalMs": float(x.group(2)), "route": x.group(3), "seeds": int(x.group(4)),
            "validateMs": float(x.group(5)), "t": t} for t, c, e, m in ev if (x := mark("generated", c, m))]
    for g in gen:                       # was it ready before its level started? (one level ahead)
        s = next((s for s in starts if s["L"] == g["L"]), None)
        g["readyBeforeGoS"] = round(s["tGo"] - g["t"], 3) if s else None
    A["generated"] = {"n": len(gen), "totalMs": stat([g["totalMs"] for g in gen]), "list": gen,
                      "notReadyAtGo": [g["L"] for g in gen if g["readyBeforeGoS"] is not None and g["readyBeforeGoS"] < 0]}
    A["lab"] = {"done": [x.group(1) for t, c, e, m in ev if (x := mark("lab_done", c, m))],
                "segments": [{"board": x.group(1), "zoom": x.group(2), "over20": int(x.group(3)), "load": int(x.group(4)),
                              "play": int(x.group(5)), "maxMs": float(x.group(6)), "t": t}
                             for t, c, e, m in ev if (x := mark("boardlab_seg", c, m))]}
    # ---- celebrations (LOGO-IMPL, LOGO-SPEC: W = the clear wave's first frame; the panel is due at W+4.034): every frame
    # > 20 ms (frame watch or board monitor) from W to the panel + 0.3 s, split into the logo part [W, panel) and the
    # panel's own presentation [panel, panel + 0.3 s]
    cels = []
    last_won = None
    for t, c, e, m in ev:
        if (x := mark("won", c, m)):
            last_won = int(x.group(1))
        elif (x := mark("celebration_start", c, m)):
            cels.append({"L": last_won, "tier": x.group(1), "tW": t, "tPanel": None, "logoAtS": None, "logoMs": None,
                         "skippedAtS": None})
        elif cels and cels[-1]["tPanel"] is None:
            if (x := mark("celebration_panel", c, m)):
                cels[-1]["tPanel"] = t
                cels[-1]["panelAtS"] = float(x.group(1))
            elif (x := mark("celebration_logo", c, m)):
                cels[-1]["logoAtS"], cels[-1]["logoMs"] = float(x.group(1)), float(x.group(3))
            elif (x := mark("celebration_skip", c, m)):
                cels[-1]["skippedAtS"] = float(x.group(1))
    all_h = [(h["t"], h["ms"], "frame") for h in hitches] + [(h["t"], h["ms"], "board") for h in board_hitches]
    for cl in cels:
        W, P = cl["tW"], cl["tPanel"]
        end = (P + 0.3) if P else W + 4.4
        hs = sorted((t, ms, src) for t, ms, src in all_h if W - 0.02 <= t <= end)
        cl["hitches"] = [{"atW": round(t - W, 3), "ms": round(ms, 1), "src": src,
                          "part": "logo" if (P is None or t < P) else "panel"} for t, ms, src in hs]
        cl["logoOver20"] = sum(1 for h in cl["hitches"] if h["part"] == "logo" and h["src"] == "frame")
        cl["panelOver20"] = sum(1 for h in cl["hitches"] if h["part"] == "panel" and h["src"] == "frame")
        cl["tW"] = round(W, 3)
        cl["tPanel"] = round(P, 3) if P else None
    A["celebrations"] = {"n": len(cels), "logoClean": sum(1 for cl in cels if cl["logoOver20"] == 0),
                         "panelClean": sum(1 for cl in cels if cl["panelOver20"] == 0),
                         "logoMs": stat([cl["logoMs"] for cl in cels]),
                         "panelAtS": stat([cl.get("panelAtS") for cl in cels]), "list": cels}
    # ---- FIX-A1's router cut probe (`[PC][perf] cut <name> … total <ms>`) and S1's frame probes
    cuts = {}
    for t, c, e, m in ev:
        if (x := mark("cut", c, m)):
            cuts.setdefault(x.group(1), []).append(float(x.group(2)))
    A["cuts"] = {k: stat(v) for k, v in cuts.items()}
    A["frameProbes"] = [{"label": x.group(1), "frames": int(x.group(2)), "maxMs": float(x.group(3)), "over20": int(x.group(4)),
                         "t": t} for t, c, e, m in ev if (x := mark("frame_probe", c, m))]
    ad = [x for t, c, e, m in ev if (x := mark("autoplay_done", c, m))]
    A["autoplay"] ={"from": int(ad[-1].group(1)), "to": int(ad[-1].group(2)), "won": int(ad[-1].group(3)),
                     "of": int(ad[-1].group(4)), "bumps": int(ad[-1].group(5))} if ad else None
    A["wins"] = [int(x.group(1)) for t, c, e, m in ev if (x := mark("won", c, m))]
    A["losses"] = [(int(x.group(1)), x.group(2)) for t, c, e, m in ev if (x := mark("lost", c, m))]
    A["errors"] = [f"{c}: {m}"[:200] for t, c, e, m in ev if e][:60]
    A["spanS"] = round(ev[-1][0] - t_first, 1)
    return A


def print_analysis(A, title=""):
    f = A.get("frames", {})
    print(f"== {title} ({A.get('lines')} lines, {A.get('spanS')} s)")
    if f.get("watch"):
        print(f"frames (watch): {f['total']} presented, {f['over20']} > 20 ms, max {f['maxMs']} ms")
        for k, v in f["hitchesByPhase"].items():
            print(f"   {k:22s} {v['n']:4d}  max {v['max']:7.1f}  median {v['median']:6.1f}")
    print(f"frames (board monitor): {f.get('board', {}).get('n')} hitch lines, max {f.get('board', {}).get('maxMs')}")
    t = A.get("taps", {})
    if t.get("n"):
        print(f"taps {t['n']}: handler→commit {t['handlerToCommitMs']}  handler {t['handlerMs']}  "
              f"commit→vsync {t['commitToVsyncMs']}  same-frame OK {t['sameframe']['ok']}/{t['sameframe']['n']}")
    s = A.get("levelStarts", {})
    if s.get("n"):
        print(f"level starts {s['n']}: go→visible {s['goToVisibleMs']}  board main {s['boardMainMs']}  "
              f"with frames > 20 ms: {s['withFramesOver20']}")
    if A.get("launch"):
        print(f"launch: {json.dumps({k: v for k, v in A['launch'].items() if k != 'summary'})}")
    if A.get("generated", {}).get("n"):
        g = A["generated"]
        print(f"generated {g['n']}: total {g['totalMs']} not ready at go: {g['notReadyAtGo']}")
    if A.get("firstEffects"):
        print(f"first effects: {A['firstEffects']}")
    if A.get("popups"):
        print("popups present→visible: " + ", ".join(f"{k} first {v['first']} max {v['max']}" for k, v in A["popups"].items()))
    if A.get("celebrations", {}).get("n"):
        c = A["celebrations"]
        print(f"celebrations {c['n']}: logo part clean {c['logoClean']}/{c['n']}, panel presentation clean "
              f"{c['panelClean']}/{c['n']}, logo build {c['logoMs']}")
    if A.get("cuts"):
        print("router cuts total ms: " + ", ".join(f"{k} {v}" for k, v in A["cuts"].items()))
    if A.get("autoplay"):
        print(f"autoplay: {A['autoplay']}")
    if A.get("errors"):
        print(f"errors: {len(A['errors'])}: {A['errors'][:3]}")


# ---------------------------------------------------------------------------------------------------------------- lab

def cmd_lab(a, extra):
    slot = Slot(a.slot)
    slot.boot()
    slot.terminate()
    if a.fresh:                                  # first-use effects after an install (§10.3 item 6, R3)
        slot.uninstall()
    slot.install()
    docs = slot.documents()
    if docs:
        for f in ("lab-ready.json", "lab-perf.json"):
            try:
                os.remove(os.path.join(docs, f))
            except FileNotFoundError:
                pass
    gate = wait_idle(a.load_max, a.idle_wait, who="bench lab")
    h0 = host_state()
    args = ["-pc.go", "boardlab", "-pc.lab", a.scenario, "-pc.seed", str(a.seed)] + extra
    if "-pc.autoplay" not in args:
        # V3 restart: `-pc.autoplay 1` suppresses the one-shot notification alert that would otherwise hold Loading after
        # an install (NotificationPrompt.askIfNeeded; see consume_prompt); on a BoardLab screen the bot has nothing to act
        # on (AutoPlayer.step acts on popups, home and level screens only), and a fresh install stays a first launch.
        args += ["-pc.autoplay", "1"]
    pid, t0 = slot.launch(args)
    samples = []
    ready = None
    end = time.time() + a.timeout
    while time.time() < end:
        fp, peak = footprint(pid) if pid else (None, None)
        samples.append({"t": round(uptime() - t0, 2), "mb": fp, "peakMB": peak, "load1": round(os.getloadavg()[0], 2)})
        docs = docs or slot.documents()
        p = os.path.join(docs, "lab-ready.json") if docs else None
        if p and os.path.exists(p):
            try:
                ready = json.load(open(p))
                if ready.get("uptime", 0) >= t0:
                    break
                ready = None
            except Exception:
                ready = None
        if pid and not alive(pid):
            break
        time.sleep(a.interval)
    h1 = host_state()
    log = slot.read_log()
    name = a.name or f"lab-{a.scenario.replace(':', '_')}-{stamp()}"
    outdir = os.path.abspath(a.out) if a.out else BENCH
    res = {"kind": "boardlab", "scenario": a.scenario, "args": args, "build": build_info(slot), "idleGate": gate,
           "hostBefore": h0, "hostAfter": h1, "ok": ready is not None, "result": ready, "footprint": samples,
           "load1": stat([s["load1"] for s in samples]),
           "footprintMB": stat([s["mb"] for s in samples]), "footprintPeakMB": max([s["peakMB"] or 0 for s in samples] or [0]),
           "analysis": analyze(log)}
    res["analysis"]["taps"].pop("list", None)
    p = os.path.join(docs, "lab-perf.json") if docs else None
    if p and os.path.exists(p) and os.path.getmtime(p) >= time.time() - a.timeout - 30:
        try:
            res["perf"] = json.load(open(p))
        except Exception:
            pass
    out = write_json(os.path.join(outdir, name + ".json"), res)
    with open(out.replace(".json", ".log"), "w") as f:
        f.write(log)
    slot.terminate()
    perf = (ready or {}).get("perf") or res.get("perf") or {}
    print(json.dumps({"out": os.path.relpath(out, ROOT), "ok": res["ok"],
                      "total_over20": (ready or {}).get("total_over20"), "worst_ms": (ready or {}).get("worst_ms"),
                      "perf": {k: perf.get(k) for k in ("frames", "fps", "p99_ms", "over20", "footprint_peak_mb",
                                                        "tap_handler_ms_p99", "handler_to_commit_ms_p99")}
                      if isinstance(perf, dict) else perf,
                      "maxFootprintMB": res["footprintMB"], "peakMB": res["footprintPeakMB"],
                      "load": [h0["load"], h1["load"]], "idleGate": gate}, indent=1))


# ------------------------------------------------------------------------------------------------------------- launch

def launch_once(slot, label, args, uninstall, a):
    slot.terminate()
    if uninstall:
        slot.uninstall()
    slot.install()
    time.sleep(1.0)
    gate = wait_idle(a.load_max, a.idle_wait, who="bench launch")
    h = host_state(full=False)
    pid, t0 = slot.launch(args)
    ru = rusage(pid)
    ok = wait_for(lambda: log_has(slot, "launch_done") and log_has(slot, "first_screen"), 40)
    time.sleep(a.settle)                         # the first screen's first seconds (home arrival, the first board)
    text = slot.read_log()
    A = analyze(text)
    A["taps"].pop("list", None)
    r = {"label": label, "args": args, "uninstalled": uninstall, "pid": pid, "idleGate": gate, "hostLoad": h["load"],
         "ok": bool(ok)}
    start = ru["startUptime"] if ru else None
    r["processStartUptime"] = start
    r["hostLaunchUptime"] = t0
    Lm = A.get("launch", {})
    ref = start or Lm.get("processStartUptime") or t0
    for k, key in (("loadingVisibleS", "tLoadingVisible"), ("launchDoneS", "tLaunchDone"), ("firstScreenS", "tFirstScreen")):
        r[k] = round(Lm[key] - ref, 3) if Lm.get(key) else None
    r["coldLaunchTotalS"] = Lm.get("coldLaunchTotalS")
    r["firstScreen"] = Lm.get("firstScreen")
    r["warmup"] = A.get("warmup")
    fr = A.get("frames", {})
    r["framesOver20"] = [{"ms": x["ms"], "screen": x["screen"], "phase": x["phase"], "afterStartS": round(x["t"] - ref, 3)}
                         for x in fr.get("hitches", [])]
    r["framesByScreen"] = fr.get("byScreen")
    r["levelStarts"] = A.get("levelStarts", {}).get("list")
    r["audio"] = A.get("audio")
    r["errors"] = A.get("errors")
    fp = rusage(pid)
    r["footprintMB"], r["peakMB"] = (fp["mb"], fp["peakMB"]) if fp else (None, None)
    r["pass"] = {"loadingVisible": r["loadingVisibleS"] is not None and r["loadingVisibleS"] <= BUDGET["loading_visible_s"],
                 "bootWarmup": r["coldLaunchTotalS"] is not None and r["coldLaunchTotalS"] <= BUDGET["boot_warmup_s"],
                 "bootWarmupCap": r["coldLaunchTotalS"] is not None and r["coldLaunchTotalS"] <= BUDGET["boot_warmup_cap_s"],
                 "noFrameOver20": not r["framesOver20"]}
    print(f"{label}: loading visible {r['loadingVisibleS']} s, launch done {r['launchDoneS']} s (cold summary "
          f"{r['coldLaunchTotalS']} s), {r['firstScreen']} visible {r['firstScreenS']} s after process start; "
          f"{len(r['framesOver20'])} frames > 20 ms (max {max([x['ms'] for x in r['framesOver20']] or [0])}); "
          f"{r['footprintMB']} MB (peak {r['peakMB']}), load {h['load'][0]}")
    return r, text


def cmd_launch(a, extra):
    slot = Slot(a.slot)
    slot.boot()
    runs, logs = [], []
    watch = [] if a.no_watch else ["-pc.frameWatch", "1"]
    base = watch + extra
    if not a.no_first:
        # V3 restart: the real first run asks the one-shot notification alert over Loading and Loading waits for the
        # answer (nothing answers it on the simulator: this run measures Loading + warm-up; its first screen is D1b's).
        # The next two fresh installs suppress the alert with the autoplay flag (the bot taps at most once in the
        # window, rate 30 s) so the first launch after install reaches the FTUE board / L5 as it does after an answer.
        r, l = launch_once(slot, "first launch after install, no arguments (the real first run; held by the alert)",
                           base, True, a)
        runs.append(r); logs.append(l)
        sup = ["-pc.autoplay", "1", "-pc.autoplayRate", "30"]
        r, l = launch_once(slot, "first launch after install, alert suppressed (FTUE board)", sup + base, True, a)
        runs.append(r); logs.append(l)
        r, l = launch_once(slot, "first launch after install, alert suppressed (-pc.level 5)", ["-pc.level", "5"] + sup + base,
                           True, a)
        runs.append(r); logs.append(l)
        consume_prompt(slot)                         # the warm launches below must not meet the one-shot alert
    for i in range(a.warm):
        r, l = launch_once(slot, f"warm launch #{i + 1} (-pc.level 5)", ["-pc.level", "5"] + base, False, a)
        runs.append(r); logs.append(l)
    for i in range(a.home):
        r, l = launch_once(slot, f"warm launch to home #{i + 1} (-pc.level 40)", ["-pc.level", "40"] + base, False, a)
        runs.append(r); logs.append(l)
    slot.terminate()
    name = a.name or f"launch-{stamp()}"
    outdir = os.path.abspath(a.out) if a.out else BENCH
    out = write_json(os.path.join(outdir, name + ".json"),
                     {"kind": "launch", "build": build_info(slot), "host": host_state(), "budget": {
                         k: BUDGET[k] for k in ("loading_visible_s", "boot_warmup_s", "boot_warmup_cap_s", "hitch_ms")},
                      "clock": "process start (proc_pid_rusage ri_proc_start_abstime, the app's uptime clock) -> the "
                               "app's own log marks; `simctl launch` overhead is excluded",
                      "runs": runs})
    with open(out.replace(".json", ".log"), "w") as f:
        f.write("\n\n==== next run ====\n".join(logs))
    print(os.path.relpath(out, ROOT))


# ------------------------------------------------------------------------------------------------------------- screens

def screen_args(tgt, level, popup_delay):
    """A `screens` target -> launch arguments. Grammar (V3 restart): parts joined by '+', each `go:<screen>`,
    `popup:<id>[:variant]`, `level:<N>`, `args:<a>=<v>` (one extra `-pc.a v`). A popup without `go:` opens over home;
    with `popup_delay` > 0 it is presented that many seconds AFTER the first screen (S1's `-pc.popupDelay`: a warm first
    presentation in the running process, like a tap, measured apart from the first screen's arrival). Old forms
    `go:<screen>` / `popup:<id>` are unchanged."""
    go, popup, lvl, more = None, None, level, []
    for part in tgt.split("+"):
        kind, _, what = part.partition(":")
        if kind == "go":
            go = what
        elif kind == "popup":
            popup = what
        elif kind == "level":
            lvl = int(what)
        elif kind == "args":
            k, _, v = what.partition("=")
            more += ["-pc." + k, v]
    args = ["-pc.level", str(lvl), "-pc.seed", "1", "-pc.lives", "5", "-pc.frameWatch", "1"]   # lives: a level never refuses
    args += ["-pc.go", go or "home"]
    if popup:
        args += ["-pc.popup", popup]
        if popup_delay > 0:
            args += ["-pc.popupDelay", str(popup_delay)]
    return args + more


def cmd_screens(a, extra):
    """First-open cost of shell screens and popups (§10.2 "frames in the shell"): one warm launch (a fresh PROCESS) per
    target (grammar: `screen_args`), -pc.frameWatch 1; every frame > 20 ms from the first screen's `fully visible` mark to
    +settle s, split into the first screen's arrival (before the popup's present) and the popup's first presentation
    (present -> +1.0 s), and each popup's present -> visible."""
    slot = Slot(a.slot)
    slot.boot()
    slot.terminate()
    slot.install()
    prompt = consume_prompt(slot)
    print(f"notification prompt before the targets: {prompt}")
    rows, logs = [], []
    for tgt in [x for x in a.targets.split(",") if x.strip()]:
        args = screen_args(tgt, a.level, a.popup_delay) + extra
        has_popup = "-pc.popup" in args
        settle = max(a.settle, a.popup_delay + 3.0) if has_popup else a.settle
        slot.terminate()
        time.sleep(1.0)
        gate = wait_idle(a.load_max, a.idle_wait, who="bench screens")
        pid, t0 = slot.launch(args)
        ok = wait_for(lambda: log_has(slot, "first_screen"), 40)
        time.sleep(settle)
        text = slot.read_log()
        A = analyze(text)
        t_vis = A.get("launch", {}).get("tFirstScreen")
        ev = parse_log(text)
        # the requested popup's present: by id (custom pages log "custom"), else the first present at the delay
        want = args[args.index("-pc.popup") + 1].split(":")[0] if has_popup else None
        pres = [(t, x.group(1)) for t, c, e, m in ev if (x := mark("popup_present", c, m)) and (not t_vis or t >= t_vis - 0.05)]
        t_present = next((t for t, pid_ in pres if pid_ == want), None) if want else None
        if want and t_present is None:
            t_present = next((t for t, _ in pres if t_vis and t >= t_vis + a.popup_delay - 0.3), None)
        other_pages = [pid_ for t, pid_ in pres if t_present is None or abs(t - t_present) > 0.01]
        after = [h for h in A["frames"]["hitches"] if t_vis and h["t"] >= t_vis - 0.05]
        arrival = [h for h in after if t_present is None or h["t"] < t_present - 0.02]
        present = [h for h in after if t_present is not None and t_present - 0.02 <= h["t"] <= t_present + 1.0]
        fp = rusage(pid)
        r = {"target": tgt, "args": args, "idleGate": gate, "ok": bool(ok), "firstScreen": A.get("launch", {}).get("firstScreen"),
             "framesOver20AfterVisible": [{"ms": h["ms"], "screen": h["screen"], "phase": h["phase"],
                                           "afterVisibleS": round(h["t"] - t_vis, 3)} for h in after],
             "arrivalOver20": [round(h["ms"], 1) for h in arrival],
             "presentAfterVisibleS": round(t_present - t_vis, 3) if (t_present and t_vis) else None,
             "presentOver20": [round(h["ms"], 1) for h in present], "otherPresents": other_pages,
             "popups": A.get("popups"), "byScreen": A["frames"]["byScreen"], "frameProbes": A.get("frameProbes"),
             "cuts": A.get("cuts"),
             "footprintMB": fp["mb"] if fp else None, "peakMB": fp["peakMB"] if fp else None,
             "load1End": round(os.getloadavg()[0], 2), "errors": A.get("errors")}
        rows.append(r)
        logs.append(text)
        print(f"{tgt}: {r['firstScreen']} visible; arrival {r['arrivalOver20']} · present {r['presentOver20']} "
              f"(> 20 ms frames); popups {r['popups']}; peak {r['peakMB']} MB; load {gate['load1']}")
    slot.terminate()
    name = a.name or f"screens-{stamp()}"
    outdir = os.path.abspath(a.out) if a.out else BENCH
    out = write_json(os.path.join(outdir, name + ".json"), {"kind": "screens", "build": build_info(slot),
                                                             "level": a.level, "rows": rows})
    with open(out.replace(".json", ".log"), "w") as f:
        f.write("\n\n==== next run ====\n".join(logs))
    print(os.path.relpath(out, ROOT))


# --------------------------------------------------------------------------------------------------------------- level

def cmd_level(a, extra):
    """One real level in the full game screen, sampled like the soak: idle (no input) by default, or autoplayed."""
    slot = Slot(a.slot)
    slot.boot()
    slot.terminate()
    slot.install()
    args = ["-pc.level", str(a.level), "-pc.go", "level", "-pc.tutorials", "skip", "-pc.seed", "1", "-pc.lives", "5"]
    if not a.no_hud:
        args += ["-pc.hud", "debug"]
    if a.autoplay:
        args += ["-pc.autoplay", "1", "-pc.autoplayStop", str(a.level)]
    args += extra
    prompt = None if a.autoplay else consume_prompt(slot)       # autoplay suppresses the alert itself
    gate = wait_idle(a.load_max, a.idle_wait, who="bench level")
    h0 = host_state()
    pid, t0 = slot.launch(args)
    wait_for(lambda: log_has(slot, "board_ready"), 40)
    t_ready = uptime()
    samples = []
    tmp = os.path.join(BENCH, ".tmp")
    os.makedirs(tmp, exist_ok=True)
    while uptime() - t_ready < a.seconds and pid and alive(pid):
        t = uptime()
        fp, peak = footprint(pid)
        hud = None
        if not a.no_shots:
            png = os.path.join(tmp, f"level-{a.slot}.png")
            hud = read_hud(png) if slot.screenshot(png) else None
        samples.append({"el": round(t - t0, 1), "sinceReady": round(t - t_ready, 1), "mb": fp, "peakMB": peak,
                        "load1": round(os.getloadavg()[0], 2), "hud": hud})
        time.sleep(max(0.0, a.interval - (uptime() - t)))
    log = slot.read_log()
    A = analyze(log)
    steady = [x["hud"] for x in samples if x["hud"] and x["sinceReady"] >= 10]
    res = {"kind": "level", "level": a.level, "autoplay": a.autoplay, "args": args, "build": build_info(slot),
           "idleGate": gate, "promptConsumed": prompt, "hostBefore": h0, "hostAfter": host_state(), "samples": samples,
           "load1": stat([s["load1"] for s in samples]),
           "steady": {"windows": len(steady), "fps": stat([h["fps"] for h in steady]),
                      "p95ms": stat([h["p95"] for h in steady]), "p99ms": stat([h["p99"] for h in steady]),
                      "layers": stat([h.get("layers") for h in steady])},
           "analysis": A}
    name = a.name or f"level-L{a.level:03d}{'-auto' if a.autoplay else '-idle'}-{stamp()}"
    outdir = os.path.abspath(a.out) if a.out else BENCH
    out = write_json(os.path.join(outdir, name + ".json"), res)
    with open(out.replace(".json", ".log"), "w") as f:
        f.write(log)
    slot.terminate()
    print_analysis(A, name)
    print(json.dumps({"out": os.path.relpath(out, ROOT), "steady": res["steady"], "load1": res["load1"],
                      "idleGate": gate}, indent=1))


# ---------------------------------------------------------------------------------------------------------------- soak

def cmd_soak(a, extra):
    slot = Slot(a.slot)
    if a.shot_every > 0:
        ocr_bin()
    if a.attach:
        # resume sampling a soak whose sampler died (the app kept playing): same dir, same pid, same log
        d = os.path.abspath(a.attach)
        meta = json.load(open(os.path.join(d, "meta.json")))
        pid, t0 = meta["pid"], meta["t0"]
        meta.setdefault("resumed", []).append({"at": uptime(), "wall": time.strftime("%H:%M:%S")})
        wall0 = time.time() - (uptime() - t0)
        shots = os.path.join(d, "shots")
    else:
        slot.boot()
        d = os.path.abspath(a.out) if a.out else os.path.join(BENCH, f"soak-{stamp()}")
        shots = os.path.join(d, "shots")
        os.makedirs(shots, exist_ok=True)
        slot.terminate()
        slot.uninstall()
        slot.install()
        args = ["-pc.reset", "1", "-pc.seed", str(a.seed), "-pc.autoplay", "1", "-pc.autoplayStop", str(a.stop),
                "-pc.hud", "debug"] + extra
        if a.start > 1 and "-pc.state" not in args:
            # V3 restart: a run that starts past the FTUE (e.g. L151) meets the home queue's one-time Claw first-open
            # PAGE (a router screen, EventsDirector, ruling 33 keeps it on for real play) and the AutoPlayer has no rule
            # to leave an event screen (it acts on popups, home and levels only): the 09-27 r1 gen run sat on it for its
            # whole timeout. Start from a state where that intro was seen (the page's first open is measured by
            # `screens` go:event:claw). Reported to GAME.
            import base64
            st = {"level": a.start, "homeSeen": True, "flags": {"seen": ["clawIntro"]}}
            args += ["-pc.state", base64.b64encode(json.dumps(st).encode()).decode()]
        gate = wait_idle(a.load_max, a.idle_wait, who="bench soak")
        meta = {"kind": "soak", "args": args, "build": build_info(slot), "idleGate": gate, "hostStart": host_state(),
                "interval": a.interval, "shotEvery": a.shot_every, "stop": a.stop, "start": a.start}
        wall0 = time.time()
        pid, t0 = slot.launch(args)
        meta.update(pid=pid, t0=t0)
    write_json(os.path.join(d, "meta.json"), meta)
    status = {"state": "running", "pid": pid}
    samples_path = os.path.join(d, "samples.jsonl")
    shot_every = max(1, int(round(a.shot_every / a.interval))) if a.shot_every > 0 else 0
    heap_at = [int(x) for x in a.heap_at.split(",") if x.strip()] if a.heap_at else []
    heaps_done = set()
    keep_every = max(1, int(round(a.keep_shot / a.interval)))
    n = len(open(samples_path).read().splitlines()) if os.path.exists(samples_path) else 0
    sf = open(samples_path, "a")
    end_reason = "timeout"
    done_at = None
    while time.time() - wall0 < a.timeout:
        n += 1
        t = uptime()
        s = {"t": round(t, 3), "el": round(t - t0, 1), "load1": round(os.getloadavg()[0], 2)}
        if not alive(pid):
            end_reason = "process exited"
            break
        s["mb"], s["peakMB"] = footprint(pid)
        png = os.path.join(shots, f"s{n:05d}.png")
        if shot_every and n % shot_every == 0 and slot.screenshot(png):
            hud = read_hud(png)
            if hud:
                s["hud"] = hud
            if n % keep_every != 0 and os.path.exists(png):
                os.remove(png)
            else:
                s["png"] = os.path.relpath(png, d)
        if n % 12 == 0:
            s["host"] = host_state()
        sf.write(json.dumps(s) + "\n")
        sf.flush()
        ev = parse_log(slot.read_log())
        wins = [int(m.group(1)) for _, c, _, msg in ev for m in [mark("won", c, msg)] if m]
        for lv in heap_at:
            if lv in heaps_done:
                continue
            t_win = next((tt for tt, c, _, msg in ev if (mw := mark("won", c, msg)) and int(mw.group(1)) == lv), None)
            if t_win is not None and any(tt > t_win and mark("home_visible", c, msg) for tt, c, _, msg in ev):
                heaps_done.add(lv)
                time.sleep(3.0)                                    # let the home arrival settle
                s2 = {"t": round(uptime(), 3), "snapshot": f"afterL{lv}"}
                s2["mb"], s2["peakMB"] = footprint(pid)
                for name, cmd in (("footprint", ["footprint", "-p", str(pid)]),
                                  ("vmmap", ["vmmap", "--summary", str(pid)]),
                                  ("heap", ["heap", "-s", "-q", str(pid)])):
                    t1 = uptime()
                    out = sh(cmd, timeout=180, check=False)
                    with open(os.path.join(d, f"{name}-afterL{lv:03d}.txt"), "w") as f:
                        f.write(out)
                    s2[name + "S"] = round(uptime() - t1, 1)
                sf.write(json.dumps(s2) + "\n")
                sf.flush()
        if done_at is None and any(mark("autoplay_done", c, msg) for _, c, _, msg in ev):
            done_at = time.time()
        if done_at is not None and time.time() - done_at >= a.tail:
            end_reason = "autoplay done"
            break
        status.update(state="running", el=s["el"], lastWin=wins[-1] if wins else 0, mb=s.get("mb"),
                      fps=(s.get("hud") or {}).get("fps"), load1=s["load1"])
        write_json(os.path.join(d, "status.json"), status)
        time.sleep(max(0.0, a.interval - (uptime() - t)))
    sf.close()
    log = slot.read_log()
    with open(os.path.join(d, "run.log"), "w") as f:
        f.write(log)
    docs = slot.documents()
    if docs and os.path.isdir(docs):                      # -pc.bench 1: the app's own per-level JSON
        os.makedirs(os.path.join(d, "app-bench"), exist_ok=True)
        for f in os.listdir(docs):
            if f.startswith("bench-L") and f.endswith(".json"):
                shutil.copy(os.path.join(docs, f), os.path.join(d, "app-bench", f))
    crashes = crash_reports(wall0 - 5)
    for c in crashes:
        shutil.copy(c, d)
    status.update(state="finished", endReason=end_reason, alive=alive(pid) if pid else False,
                  crashReports=[os.path.basename(c) for c in crashes], wallSeconds=round(time.time() - wall0, 1))
    write_json(os.path.join(d, "status.json"), status)
    meta["hostEnd"] = host_state()
    meta["end"] = status
    write_json(os.path.join(d, "meta.json"), meta)
    slot.terminate()
    report(d)


# -------------------------------------------------------------------------------------------------------------- report

def level_files():
    """{level: {"arrows", "timer_s", "hearts", "tag"}} from App/Resources/Levels/level_NNNN.json."""
    out = {}
    if not os.path.isdir(LEVELS_DIR):
        return out
    for f in sorted(os.listdir(LEVELS_DIR)):
        if not (f.startswith("level_") and f.endswith(".json")):
            continue
        try:
            j = json.load(open(os.path.join(LEVELS_DIR, f)))
        except Exception:
            continue
        for lv in (j if isinstance(j, list) else j.get("levels", [j]) if isinstance(j, dict) else []):
            if isinstance(lv, dict) and isinstance(lv.get("level"), int) and isinstance(lv.get("arrows"), list):
                out[lv["level"]] = {"arrows": len(lv["arrows"]), "timer_s": lv.get("timer_s"),
                                    "hearts": lv.get("hearts"), "tag": lv.get("tag")}
    return out


def report(d):
    meta = json.load(open(os.path.join(d, "meta.json")))
    allrows = [json.loads(l) for l in open(os.path.join(d, "samples.jsonl")) if l.strip()]
    samples = [r for r in allrows if "snapshot" not in r]
    snapshots = [r for r in allrows if "snapshot" in r]
    text = open(os.path.join(d, "run.log"), errors="replace").read()
    ev = parse_log(text)
    levels = level_files()
    A = analyze(text)

    # ---- attempts (one per level entry) and home segments, from MARKS only
    attempts, homes = [], []
    cur, home, pending_go = None, None, None
    for t, cat, err, msg in ev:
        m = mark("level_go", cat, msg)
        if m:
            pending_go = (int(m.group(1)), t)
            if home is not None:
                home["end"] = t
                homes.append(home)
                home = None
            continue
        m = mark("level_visible", cat, msg) or mark("board_ready", cat, msg)
        if m and (cur is None or cur["level"] != int(m.group(1)) or cur.get("tEnd")) and "(stage" not in msg:
            if cur is not None:
                attempts.append(cur)
            lv = int(m.group(1))
            cur = {"level": lv, "tGo": pending_go[1] if pending_go and pending_go[0] == lv else None,
                   "tVisible": t, "hitches": [], "errors": []}
            pending_go = None
        if cur is None:
            if mark("home_visible", cat, msg) and home is None:
                home = {"start": t, "afterLevel": attempts[-1]["level"] if attempts else None}
            continue
        if (m := mark("board_ready", cat, msg)) and int(m.group(1)) == cur["level"]:
            cur.setdefault("tBoardReady", t)
            cur["arrows"] = int(m.group(2))
        elif (m := mark("play", cat, msg)) and int(m.group(1)) == cur["level"]:
            cur.setdefault("tPlay", t)
        elif mark("hitch", cat, msg) or mark("frame_hitch", cat, msg):
            cur["hitches"].append(f"[{cat}] {msg}")
        elif (m := mark("won", cat, msg)) and int(m.group(1)) == cur["level"]:
            cur.update(outcome="won", tEnd=t, timeLeftS=int(m.group(2)), heartsLeft=int(m.group(3)))
        elif (m := mark("lost", cat, msg)) and int(m.group(1)) == cur["level"]:
            cur.update(outcome="lost", tEnd=t, lossReason=m.group(2))
        elif (m := mark("teardown", cat, msg)) and int(m.group(1)) == cur["level"] and cat == "game":
            cur["tTeardown"] = t
            attempts.append(cur)
            cur = None
        if err and cur is not None:
            cur["errors"].append(f"{cat}: {msg}")
        if cur is not None and mark("home_visible", cat, msg) and home is None:
            home = {"start": t, "afterLevel": cur["level"]}
    if cur is not None:
        attempts.append(cur)
    if home is not None:
        home["end"] = samples[-1]["t"] if samples else home["start"]
        homes.append(home)

    def window(t0, t1):
        return [s for s in samples if t0 is not None and t1 is not None and t0 <= s["t"] <= t1]

    app_bench = {}
    bdir = os.path.join(d, "app-bench")
    if os.path.isdir(bdir):
        for f in sorted(os.listdir(bdir)):
            try:
                j = json.load(open(os.path.join(bdir, f)))
                app_bench.setdefault(j.get("level"), []).append(j)
            except Exception:
                pass

    out_levels = []
    for at in attempts:
        lf = levels.get(at["level"], {})
        t_vis = at.get("tVisible")
        t_end = at.get("tTeardown") or at.get("tEnd") or (samples[-1]["t"] if samples else None)
        ss = window(t_vis, t_end)
        steady = [s["hud"] for s in ss if s.get("hud") and s["t"] >= t_vis + 12
                  and (at.get("tEnd") is None or s["t"] <= at["tEnd"])]
        all_hud = [s["hud"] for s in ss if s.get("hud")]
        go = round((t_vis - at["tGo"]) * 1000, 1) if t_vis and at.get("tGo") else None
        ab = (app_bench.get(at["level"]) or [None])[0]
        b = {
            "level": at["level"], "outcome": at.get("outcome", "unfinished"), "timeLeftS": at.get("timeLeftS"),
            "heartsLeft": at.get("heartsLeft"), "lossReason": at.get("lossReason"),
            "tag": lf.get("tag"), "timerS": lf.get("timer_s"), "arrows": at.get("arrows"),
            "levelFileArrows": lf.get("arrows"),
            "playWallS": round((at.get("tEnd") or t_end or 0) - (at.get("tPlay") or t_vis or 0), 1) if t_vis else None,
            "goToVisibleMs": go, "goBudgetMs": BUDGET["play_to_board_ms"],
            "goPass": (go <= BUDGET["play_to_board_ms"]) if go is not None else None,
            "frames": {
                "source": "debug HUD (last 600 frames) via screenshot OCR; steady = >= 12 s after the reveal",
                "steadyWindows": len(steady),
                "fps": stat([h["fps"] for h in steady]), "p95ms": stat([h["p95"] for h in steady]),
                "p99ms": stat([h["p99"] for h in steady]), "allWindows": len(all_hud),
            },
            "appBench": ab,
            "memory": {"footprintMB": stat([s.get("mb") for s in ss]),
                       "peakMB": max([s.get("peakMB") or 0 for s in ss] or [0]) or None,
                       "appReportedMB": stat([h.get("appMB") for h in all_hud]),
                       "layers": stat([h.get("layers") for h in all_hud])},
            "hostLoad1": stat([s.get("load1") for s in ss]),
            "hitchLogLines": at["hitches"], "errors": at["errors"],
        }
        out_levels.append(b)
        write_json(os.path.join(d, f"bench-L{at['level']:03d}-{len(out_levels):02d}.json"), b)

    out_homes = []
    for h in homes:
        ss = window(h["start"], h["end"])
        out_homes.append({"afterLevel": h["afterLevel"], "seconds": round(h["end"] - h["start"], 1),
                          "footprintMB": stat([s.get("mb") for s in ss]),
                          "peakMB": max([s.get("peakMB") or 0 for s in ss] or [0]) or None})

    won = sorted({b["level"] for b in out_levels if b["outcome"] == "won"})
    stop, start = meta.get("stop", 30), meta.get("start", 1)
    spans = [(at.get("tVisible"), at.get("tTeardown") or at.get("tEnd")) for at in attempts if at.get("tVisible")]
    play_mb = [s.get("mb") for s in samples if s.get("mb") and any(a <= s["t"] <= (b or 1e18) for a, b in spans)]
    home_meds = [(h["afterLevel"], h["footprintMB"]["median"]) for h in out_homes if h["footprintMB"] and h["afterLevel"]]
    growth = None
    if len(home_meds) >= 2:
        xs = [x for x, _ in home_meds]
        ys = [y for _, y in home_meds]
        mx, my = statistics.mean(xs), statistics.mean(ys)
        den = sum((x - mx) ** 2 for x in xs)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0
        growth = {"homeFirst": home_meds[0], "homeLast": home_meds[-1], "homeMax": max(home_meds, key=lambda p: p[1]),
                  "lastMinusFirstMB": round(home_meds[-1][1] - home_meds[0][1], 1),
                  "slopeMBPerLevel": round(slope, 2), "fitOver30LevelsMB": round(slope * 29, 1)}
    fps_w = [b["frames"] for b in out_levels if b["frames"]["steadyWindows"]]
    A_small = dict(A)
    A_small["taps"] = {k: v for k, v in A["taps"].items() if k != "list"}
    A_small["frames"] = {k: v for k, v in A["frames"].items() if k != "hitches"}
    A_small["frames"]["hitches"] = A["frames"]["hitches"]
    summary = {
        "kind": "soak-summary", "dir": os.path.relpath(d, ROOT), "args": meta.get("args"), "build": meta.get("build"),
        "idleGate": meta.get("idleGate"), "hostStart": meta.get("hostStart"), "hostEnd": meta.get("hostEnd"),
        "end": meta.get("end"), "load1": stat([s.get("load1") for s in samples]),
        "levelsWon": won,
        # the autoplay's own tally (Levels 1-4 is one session: its win is logged once, as L1)
        "allWon": bool(A.get("autoplay")) and A["autoplay"]["won"] == A["autoplay"]["of"] and A["autoplay"]["to"] == stop
        and not A["losses"],
        "attempts": len(out_levels), "losses": [(b["level"], b["lossReason"]) for b in out_levels
                                                if b["outcome"] == "lost"],
        "crash": bool((meta.get("end") or {}).get("crashReports"))
        or (meta.get("end") or {}).get("endReason") == "process exited",
        "errors": A["errors"],
        "memory": {
            "source": "proc_pid_rusage every interval (phys_footprint; peak = the process's lifetime high-water mark)",
            "playMaxMB": max(play_mb) if play_mb else None, "playBudgetMB": BUDGET["mem_play_mb"],
            "processPeakMB": max([s.get("peakMB") or 0 for s in samples] or [0]), "peakBudgetMB": BUDGET["mem_peak_mb"],
            "homeMaxMB": max([h["footprintMB"]["max"] for h in out_homes if h["footprintMB"]] or [0]),
            "growth": growth, "growthBudgetMB": BUDGET["mem_growth_mb"],
            "homeByLevel": home_meds,
            "appBenchPeakMB": max([j.get("footprint_peak_mb") or 0 for v in app_bench.values() for j in v] or [0]) or None,
        },
        "frames": {
            "hud": {"levelsWithSteadyWindows": len(fps_w), "windows": sum(f["steadyWindows"] for f in fps_w),
                    "worstLevelFps": min(([(b["level"], b["frames"]["fps"]["min"]) for b in out_levels
                                           if b["frames"]["fps"]]), key=lambda p: p[1], default=None)},
        },
        "goToVisible": [(b["level"], b["goToVisibleMs"]) for b in out_levels],
        "goFails": [(b["level"], b["goToVisibleMs"], b["goBudgetMs"]) for b in out_levels if b["goPass"] is False],
        "homes": out_homes,
        "snapshots": snapshots,
        "analysis": A_small,
    }
    write_json(os.path.join(d, "soak-summary.json"), summary)
    print_analysis(A, os.path.relpath(d, ROOT))
    print(json.dumps({k: summary[k] for k in ("levelsWon", "allWon", "attempts", "losses", "crash", "memory", "goFails",
                                              "load1")}, indent=1, default=str))
    return summary


def parse_heap(path):
    """`heap -s -q` output -> ({class: (count, bytes)}, total bytes)."""
    rows, total, on = {}, None, False
    for line in open(path, errors="replace"):
        m = re.search(r"All zones: \d+ nodes \((\d+) bytes\)", line)
        if m:
            total = int(m.group(1))
        if line.strip().startswith("====="):
            on = True
            continue
        if not on:
            continue
        m = re.match(r"^\s*(\d+)\s+(\d+)\s+([\d.]+)\s+(.*)$", line)
        if not m:
            continue
        name = re.split(r"\s{2,}", m.group(4).strip())
        key = " | ".join(x for x in name if x)
        c, b = rows.get(key, (0, 0))
        rows[key] = (c + int(m.group(1)), b + int(m.group(2)))
    return rows, total


def cmd_heapdiff(a, extra):
    r0, t0 = parse_heap(a.before)
    r1, t1 = parse_heap(a.after)
    keys = set(r0) | set(r1)
    diff = sorted(((r1.get(k, (0, 0))[1] - r0.get(k, (0, 0))[1], r1.get(k, (0, 0))[0] - r0.get(k, (0, 0))[0], k)
                   for k in keys), reverse=True)
    out = {"before": os.path.relpath(a.before, ROOT), "after": os.path.relpath(a.after, ROOT),
           "mallocTotalMB": [round((t0 or 0) / 1048576, 1), round((t1 or 0) / 1048576, 1)],
           "growthMB": round(((t1 or 0) - (t0 or 0)) / 1048576, 1),
           "top": [{"class": k, "dBytesKB": round(db / 1024, 1), "dCount": dc,
                    "after": {"count": r1.get(k, (0, 0))[0], "KB": round(r1.get(k, (0, 0))[1] / 1024, 1)}}
                   for db, dc, k in diff[:a.top]]}
    print(json.dumps(out, indent=1))
    if a.out:
        write_json(a.out, out)


def cmd_report(a, extra):
    report(os.path.abspath(a.dir))


def cmd_logstats(a, extra):
    A = analyze(open(a.log, errors="replace").read())
    print_analysis(A, a.log)
    if a.json:
        write_json(a.json, A)


def main():
    argv = sys.argv[1:]
    extra = []
    if "--" in argv:
        i = argv.index("--")
        argv, extra = argv[:i], argv[i + 1:]
    if argv and argv[0] in SLOTS:                   # tools/bench.sh <slot> <cmd> ...  ->  <cmd> <slot> ...
        argv = [argv[1], argv[0]] + argv[2:] if len(argv) > 1 else argv
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(s):
        s.add_argument("--load-max", type=float, default=4.0, help="idle gate: 1-min load below this before the launch")
        s.add_argument("--idle-wait", type=float, default=900, help="max seconds to wait for the idle gate")
        s.add_argument("--out", help="output directory (default build/bench)")
        s.add_argument("--name", help="output base name")

    s = sub.add_parser("lab"); s.add_argument("slot"); s.add_argument("scenario")
    s.add_argument("--timeout", type=float, default=200); s.add_argument("--seed", type=int, default=1)
    s.add_argument("--interval", type=float, default=2.0)
    s.add_argument("--fresh", action="store_true", help="uninstall first (first-use effects after an install)"); common(s)
    s.set_defaults(f=cmd_lab)
    s = sub.add_parser("launch"); s.add_argument("slot"); s.add_argument("--warm", type=int, default=3)
    s.add_argument("--home", type=int, default=0); s.add_argument("--settle", type=float, default=4.0)
    s.add_argument("--no-watch", action="store_true"); s.add_argument("--no-first", action="store_true"); common(s)
    s.set_defaults(f=cmd_launch)
    s = sub.add_parser("screens"); s.add_argument("slot"); s.add_argument("--targets", required=True)
    s.add_argument("--level", type=int, default=60); s.add_argument("--settle", type=float, default=6.0)
    s.add_argument("--popup-delay", type=float, default=0.0,
                   help="present popups this many s after the first screen (-pc.popupDelay; 0 = at the first screen)")
    common(s)
    s.set_defaults(f=cmd_screens)
    s = sub.add_parser("level"); s.add_argument("slot"); s.add_argument("level", type=int)
    s.add_argument("--seconds", type=float, default=40); s.add_argument("--interval", type=float, default=5)
    s.add_argument("--autoplay", action="store_true"); s.add_argument("--no-shots", action="store_true")
    s.add_argument("--no-hud", action="store_true"); common(s)
    s.set_defaults(f=cmd_level)
    s = sub.add_parser("soak"); s.add_argument("slot"); s.add_argument("--stop", type=int, default=30)
    s.add_argument("--start", type=int, default=1, help="the first level the run plays (-pc.level N in the args)")
    s.add_argument("--timeout", type=float, default=5400); s.add_argument("--interval", type=float, default=2)
    s.add_argument("--keep-shot", type=float, default=60, help="keep one screenshot per this many seconds")
    s.add_argument("--tail", type=float, default=20, help="seconds of home sampled after the autoplay's done line")
    s.add_argument("--shot-every", type=float, default=0, help="screenshot + HUD OCR every this many seconds (0 = off; "
                                                               "the frame watch is the frame instrument)")
    s.add_argument("--heap-at", default="", help="levels after whose win home gets footprint/vmmap/heap snapshots")
    s.add_argument("--attach", help="resume sampling the running soak in this dir (its sampler died)")
    s.add_argument("--seed", type=int, default=1); common(s)
    s.set_defaults(f=cmd_soak)
    s = sub.add_parser("report"); s.add_argument("dir"); s.set_defaults(f=cmd_report)
    s = sub.add_parser("logstats"); s.add_argument("log"); s.add_argument("--json"); s.set_defaults(f=cmd_logstats)
    s = sub.add_parser("heapdiff"); s.add_argument("before"); s.add_argument("after")
    s.add_argument("--top", type=int, default=30); s.add_argument("--out"); s.set_defaults(f=cmd_heapdiff)
    a = p.parse_args(argv)
    a.f(a, extra)


if __name__ == "__main__":
    main()
