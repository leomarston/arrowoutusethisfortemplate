---
name: capture-doubles-neutral-identity
description: "App Store screenshots taken against protocol test doubles must show a neutral device identity on a LAN address at the real port — never 127.0.0.1, a test port or a real model string"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 195160ba-b6c0-4fae-8afc-86456f932056
  modified: 2026-09-06T16:11:15.030Z
---

When an app's screens show a **discovered device**, the marketing capture inherits whatever the
test double says it is. On `tvremote` the first App Store shots showed `127.0.0.1`, `answers on
:18060`, and `OLED65C9PUA` — a loopback address, a five-digit test port and a real LG model
string. The first two read as a dev build; the third is a manufacturer's mark in a screenshot,
which is exactly what App Store 5.2.5 forbids outside the description.

**The capture profile** (documented per app in `tools/faketv/PORTS.md`):
- bind the doubles to `0.0.0.0` so they answer on the Mac's LAN address, and run them on the
  REAL protocol ports (Roku 8060, LG 3000/3001 — all above 1024, no privilege needed);
- POST a neutral identity to each double's control endpoint before capturing
  (`vendor`, `friendly_model_name`, `user_device_name` for Roku; `model_name` for webOS) — the
  doubles keep the captured fixture values by default for protocol fidelity, so this is an
  override, not a change to the double;
- point the capture tests at that host/port with `TEST_RUNNER_`-prefixed env vars (plain env
  does NOT reach an XCUITest runner);
- stop the capture doubles afterwards: they sit on the ports the fidelity gates need.

**Also:** pin the status bar with `xcrun simctl status_bar <sim> override --time 9:41
--batteryState charged --batteryLevel 100 --wifiMode active --wifiBars 3` — the iPad shots
showed the Turkish `%100` battery format because the simulator inherits the Mac's region
([[simulator-inherits-mac-region]]).

Related: [[never-ship-stand-in-content]] (the opposite failure — a stand-in shown as real data;
here the data is real, the identity around it is what has to be neutral).

**Two ways a capture pass silently ships the wrong pixels (both hit tvremote on 2026-09-07):**

1. **The LAN address changes and every capture SKIPS.** The Mac moved from 192.168.1.56 to
   10.0.0.81 mid-session; `PortProbe` found nothing, the tests `XCTSkip`ped, and `xcodebuild`
   printed *"Executed 8 tests, with 0 failures"* while the previous run's PNGs sat on disk waiting
   to be shipped. A skip is not a pass. When `CAPTURE_HOST` is set explicitly — i.e. this is a
   store capture, not an everyday test run — a missing double must `XCTFail`. Re-read the address
   with `ipconfig getifaddr en0` at the start of every pass; never hard-code it.
2. **A real device answers and walks into the frame.** A stranger's *Philips UHD Android TV* landed
   in the iPad finder screenshot with the manufacturer's name on it — exactly the 5.2.5 problem the
   neutral identity above exists to avoid. A DEBUG-only `-OnlySeededTVs` now turns Bonjour and the
   sweep off for a capture pass, so only the seeded doubles can appear. Bonus: it also made the
   *"No TV answered"* frame capturable, which used to skip on any network where something answered.
