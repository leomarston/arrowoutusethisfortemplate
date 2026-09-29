---
name: camera-device-only-bug-classes
description: "The five camera bug classes the Simulator can never catch — check every one before shipping any AVFoundation app"
metadata:
  type: feedback
---

The user reported "the cameras are not working" across the factory's camera apps on 2026-09-01.
24 real failures were found in 7 apps. **Every one was invisible in the Simulator**, which has no
camera — so a green build and clean screenshots prove nothing about a camera app.

**Why:** the factory's quality gates run in the Simulator. Camera apps take the demo-scene branch
there, so the entire capture path is never executed before submit.

**How to apply** — audit each of these before shipping anything that touches AVFoundation:

1. **`.notDetermined` treated as denied.** `guard isAuthorized else { status = .denied }` never
   shows the permission dialog, so the camera is 100% dead on a fresh install and silently falls
   back to demo content. Route `.notDetermined` to `requestAccess` explicitly. (twocam shipped
   this in 1.0.0.)
2. **Data-output frames are SENSOR-oriented.** A preview layer auto-rotates; an
   `AVCaptureVideoDataOutput` / `AVCaptureMovieFileOutput` / photo connection does NOT. Set
   `videoRotationAngle` (iOS 17: `AVCaptureDevice.RotationCoordinator`) and front mirroring, or
   frames render and files save sideways. The Simulator hides it because synthetic scenes are
   generated portrait.
3. **Main-actor frame pileup.** `captureOutput` hopping every frame to `@MainActor` with no
   backpressure = frozen UI, climbing memory, watchdog kill. Process on the capture queue, keep
   one frame in flight, publish only results.
4. **Write-only status.** A `@Published statusMessage` that no view renders means every capture
   and save error is invisible — worst case the thumbnail and success haptic fire while the photo
   is discarded (Photos add-only denied). Grep that every published error is actually displayed.
5. **Advertised-but-fake features (2.3.1).** procam's paid aspect ratios were a preview-only mask
   and its "live" histogram/peaking/zebra read the demo image, not camera frames. If it is sold,
   it must operate on real frames and real saved bytes.

Also: torch control must survive brightness/lifecycle changes (partylights' torch never fired
below 50% screen brightness; strobelight left it burning solid past 10 Hz).

Related: [[camera-and-payment-testing]], [[interactive-bug-check]], [[verify-real-not-mock]].
