---
name: permission-prompt-is-one-shot
description: iOS shows a privacy prompt once per INSTALL; a torn-down test run consumes it and every later run sees no alert — uninstall before re-running
metadata:
  type: reference
---

`PHPhotoLibrary.requestAuthorization` (and every other privacy prompt) is **one-shot per install**.
If a test run is killed, times out, or is interrupted while the alert is on screen, the prompt is
consumed. Every later run then calls `requestAuthorization`, gets an immediate return, and **no
alert ever appears** — while TCC still holds no row, so the app is correctly reporting
"not determined" and correctly showing its permission screen.

Symptom: `XCTAssertTrue(allowPhotos())` fails with "the permission alert never appeared", the
springboard's `debugDescription` shows no alert at all, and re-running changes nothing. It looks
like the app is broken; it is not.

`xcodebuild test` does NOT reinstall when the binary is unchanged, so the consumed state persists
across runs indefinitely.

**Fix: uninstall before the run.**

    xcrun simctl terminate <dev> <bundle>
    xcrun simctl uninstall <dev> <bundle>
    xcodebuild test …

`simctl erase` works too but costs the whole media library. Note that `simctl privacy grant photos`
is NOT a way out — see [[simctl-photos-grant-is-a-lie]].

When a system alert cannot be dismissed it blocks everything behind it, which is the same failure
family as [[test-delete-alert-wedges-suite]]. Always screenshot the simulator when a UI run stalls.
