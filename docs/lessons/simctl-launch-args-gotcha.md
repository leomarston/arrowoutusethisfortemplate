---
name: simctl-launch-args-gotcha
description: simctl launch re-foregrounds a running app and DROPS new launch args; cold-start or two-step for screenshot captures
metadata: 
  node_type: memory
  type: reference
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
  modified: 2026-08-22T23:06:11.462Z
---

**`xcrun simctl launch <dev> <bundle> -Args…` silently ignores the args if the app is already running** — it just brings the existing process to the foreground with its old state. Terminating first is NOT enough (terminate is async / the relaunch races). Symptom: `-SkipOnboarding` / `-ShowScreen X` captures intermittently show the WRONG screen (usually onboarding), even though the same command worked moments earlier.

**Reliable capture recipe (used for VinCam screenshots):**
- Cold start: `simctl terminate` → `simctl uninstall` → `simctl install` → `sleep 2` → `simctl launch …args` → `sleep 5` → screenshot. A fresh install guarantees the first launch honors args.
- If a screen needs BOTH a persisted flag AND a `-ShowScreen` (e.g. skip-onboarding + open develop), do it two-step: launch once with `-SkipOnboarding` (which in these apps also PERSISTS `hasOnboarded=true` in AppState.init), terminate, then launch again with `-ShowScreen X`. The second launch shows home deterministically because hasOnboarded is now persisted, and only needs the `-ShowScreen` arg.
- Belt-and-suspenders in code: make `-SkipOnboarding` write `UserDefaults hasOnboarded=true` in AppState.init (not just the DEBUG routing override), so routing is deterministic even if the override path races on cold launch. Done in ProCam + VinCam.

**bug_check.py is unaffected** — XCUITest `app.launch()` with `launchArguments` uses a different mechanism that reliably applies args on every test.

**2026-08-23 (strobelight), worse than the above: even a guaranteed-clean `simctl launch --terminate-running-process` with correct args does not activate the scene, so SwiftUI never runs the `.task` blocks the whole `-ShowScreen` / `-ScrollTo` routing hangs off.** The args DO arrive (verified via `--console-pty`; init-time flags like `-Pro` take effect) — the routing just never fires, and every capture comes back as the untouched first screen. Repeating the launch, reinstalling, or lengthening the sleep does not help.

**Stop fighting simctl for captures — use XCUITest.** `scripts/capture_shots.py --slug <slug>` runs a `CaptureTests` UI test that foregrounds properly, can scroll and tap, attaches each screen with `XCTAttachment`, and exports them to `shots/final/` via `xcrun xcresulttool export attachments` (the legacy graph API returns no attachment ids — use the modern `export attachments` subcommand and its `manifest.json`; strip the `_<n>_<uuid>` suffix Xcode appends). Bonus: XCUITest screenshots get the clean 09:41 / full-signal status bar.

Related SwiftUI trap when adding scroll anchors: an `.id()` on a section whose content republishes (a running engine, a timer) makes SwiftUI rebuild that subtree and **reset the scroll offset**, so `scrollTo` appears to do nothing. Put anchors on inert `Color.clear.frame(height: 0).id(…)` markers instead.
