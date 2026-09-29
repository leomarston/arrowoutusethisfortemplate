---
name: phone-driver
description: "tools/phonedriver drives the owner's USB iPhone 15 (tap/swipe/shot/launch) for 1:1 copycat research; setup steps + gotchas"
metadata:
  node_type: memory
  type: reference
  originSessionId: 0c154f3b-15af-44af-adf5-6b546962dd29
  modified: 2026-09-23T23:03:24.857Z
---

`tools/phonedriver/` (committed d7c8d6f, 2026-09-24) lets Claude control the owner's USB-connected
iPhone 15 ("Ozcan'in iPhone'u", CoreDevice id 878DB538-F187-596F-B24B-EAF8853617DE, UDID
00008120-000964E426440032, iOS 26.6.1, 393×852 pt) to study apps it will copy.

- Start: `tools/phonedriver/start-runner` in the background (XCUITest runner, HTTP :8100 over the
  CoreDevice USB tunnel; signs with team GDU77F3MXL via the ASC API key in `.env`).
- Drive: `tools/phonedriver/phone status|shot F|tap X Y|press X Y S|swipe X1 Y1 X2 Y2 S|launch B|activate B|source B|home|apps`
  (points, not pixels). Gestures go through SpringBoard coordinates so animating games don't block
  on idle.
- Full-res capture without the runner: `tools/phonedriver/capture/build.sh`, then
  `open -W build/PhoneCapture.app --args out.png`. It needs the macOS camera permission, because
  the iPhone screen appears to macOS as a camera, and only an .app bundle gets that prompt.

**Phone prerequisites the owner turned on:** Developer Mode, then Settings → Developer → Enable
UI Automation (without it: "Timed out while enabling automation mode"). Auto-Lock should be Never
for unattended runs.

**Gotchas:**
- The auto-mode classifier blocked creating the runner ("Create Unsafe Agents") and curl to it
  ("Expose Local Services") until the owner approved in `/permissions`.
- The tunnel IPv6 changes per devicectl session; `phone` caches it and refreshes on failure.
- xcodebuild needs an ABSOLUTE `-authenticationKeyPath`.
- The first device build can fail with "Provisioning profile … cannot be found"; just retry.
- `devicectl device info apps` needs `--include-all-apps` to show App Store apps.

Verified by playing Arrows (com.ecffri.arrows) levels 3 and 4. The original's exiting arrow turns
**blue** and snakes along its own path; the win confetti fires from both bottom corners.

Related: [[account-and-no-browser]], [[copycat-the-category]]
