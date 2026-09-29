---
name: verify-real-not-mock
description: Prove an app actually works before submitting — run the real path, and prove demo data cannot ship
metadata:
  type: feedback
---

The user's standing concern (stated 2026-08-22): *"make sure the app is not fake and there is
nothing fake or mock inside it, make sure it is actually working and we are not scamming."*

Every factory app carries `-Demo*` launch flags so screenshots and UI tests are deterministic.
That is legitimate, but it means **the demo path is the one usually exercised** — so before
submit, prove two things:

1. **The REAL path works.** Run the app with NO demo flag and make it do the actual thing.
   Much is testable even in the simulator: the iOS simulator shares the Mac's LAN, so Bonjour
   discovery finds real devices (this is how LD was proven). For genuinely device-only
   capabilities (camera, BLE, multi-cam, live mic) say so plainly instead of implying it was
   verified — see [[camera-and-payment-testing]].
2. **Demo data cannot ship.** Build `-configuration Release` and grep the binary:
   ```
   strings <App.app>/<App> | grep -c "<fixture name>"     # must be 0
   ```
   plus `awk` over the sources to confirm every demo/seed symbol sits inside `#if DEBUG`.

**Also watch for dishonest COUNTING**, not just fake data: LD counted one Mac twice because
AirPlay advertises `HWADDR@Name`, inflating "2 devices can hear you". A number that overstates
the threat is the thing that makes a detector app feel like a scam, even with real inputs.

Related: [[camera-and-payment-testing]], [[interactive-bug-check]], [[listendetect-build-state]]
