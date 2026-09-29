---
name: daily-routine
description: "Factory is USER-TRIGGERED (no schedule as of 2026-07-22): when the user says start/next, run the full build+submit pipeline for the next ROUTINEAPPS.MD ⬜ app"
metadata: 
  node_type: memory
  type: project
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

**NO automated schedule — user-triggered (user removed the schedule 2026-07-22).** The user decides *when*; the moment they say "start" / "next app" / "go" (or similar), run the FULL autonomous pipeline for the next `⬜` app — the same work a scheduled run would do, just on their trigger. Do NOT set up any cron/launchd schedule unless they explicitly ask. Queue + rules in `ROUTINEAPPS.MD`; each ⬜ row → `✅` on a verified WAITING_FOR_REVIEW.

**On-trigger pipeline:** `python3 scripts/routine_next.py` (next ⬜ → slug/seed/store_name) → research long-tail keywords (seed first) → write the ideas.yaml entry → app-factory skill Faz 0-11 (`rc_setup.py`, `asc_iap.py`, marketing screenshots, **`bug_check.py` gate green in light+dark**, `create_app` with the STORE name, upload build, **submit via `asc_submit.py`**) → verify app + weekly + yearly WAITING_FOR_REVIEW → `routine_done.py <slug> submitted` + commit. Any step failing 3× → `BLOCKED.md`, stop, never fake success. (The launchd installer `scripts/install_routine.sh` + `scripts/routine.sh` still exist if the user ever wants scheduling back; leave them dormant.)

**Install (the classifier blocks ME from writing to ~/Library/LaunchAgents or running the autonomous agent — the USER must do it):** plist is committed at `scripts/launchd/com.manycode.appfactory.routine.plist`; user runs `bash scripts/install_routine.sh` (cp → `launchctl load -w`). As of 2026-07-22 it is NOT yet installed until the user runs that.

**Prerequisites for TRUE unattended runs (told the user):**
1. `sudo pmset repeat wakeorpoweron MTWRFSU 04:55:00` (sudo — user runs) so the Mac is awake for the 05:00 run; 17:00 assumes the Mac is awake in the afternoon.
2. Mac stays plugged in + **logged into the GUI** (Simulator needs a user session for build/screenshots/bug-check).
3. `fastlane spaceauth -u esaridogann@gmail.com` valid — cached cookie refreshed 2026-07-21; ~30-day life, refresh monthly (create_app needs it).
4. Headless `claude -p` must be authenticated (verify once: `claude -p "say hi"` in Terminal).
Known risk: Faz 5 icon step uses Gemini MCP, which may be absent in headless runs — if so the run BLOCKs at icon; may need a fallback. First scheduled run is the real end-to-end test.

**Done (all WAITING_FOR_REVIEW):** #1 pomodoro, #2 wifispeed, #3 bluetoothmic ("Bluetooth Speaker Mic - BM", app 6793614682, 2026-07-23). **Next up: #4 `applock`** (seed "app lock for iphone", store "App Lock for iPhone - Vault") — but the user edits ROUTINEAPPS.MD, so re-read it on the next "start". Related: [[app-naming-keyword-first]], [[keywords-are-user-owned]], [[interactive-bug-check]], [[asc-subscription-submission]], [[subscription-grace-period]], [[app-price-schedule-required]], [[copyright-and-five-screenshots]].
