---
name: ipad-is-a-review-device
description: Apple reviews iPhone-only apps ON AN IPAD; ship universal and audit on the iPad before submit
metadata:
  type: feedback
---

Apple rejected `soundanalyzer` under guideline 4.0.0 after reviewing it on an **iPad Air
11-inch (M3)** — an app that was `TARGETED_DEVICE_FAMILY: 1` (iPhone-only). In iPad
compatibility mode it ran letterboxed in a phone-shaped window with wallpaper down both
sides, and in that narrower geometry two things truncated that never truncate on iPhone.

**Why:** the reviewer's device is not your device. The rejection note is explicit —
"apps that may be downloaded onto iPad devices should function as expected for iPad
users". Fixing only the truncation leaves a phone app in a box, which invites the same
rejection again.

**How to apply:** ship `TARGETED_DEVICE_FAMILY: "1,2"` with a layout that earns the
width (on `soundanalyzer`: an instrument rail beside a full-height chart in landscape, a
single column with a capped measure in portrait), give iPad all four orientations, and
capture every screen on a real iPad simulator and LOOK at them before submit. A universal
app also REQUIRES an iPad screenshot set in ASC or the listing cannot be submitted —
`scripts/make_screenshots.py --device ipad13` renders the 2064x2752 canvas.

Two traps that cost a full upload cycle each:
- `INFOPLIST_KEY_UISupportedInterfaceOrientations__iPad` (double underscore) is NOT a
  build setting. It is silently dropped and the bundle ships with NO orientations;
  Apple's uploader then fails with a 409. Use ONE underscore, and verify with
  `plutil -p` on the BUILT Info.plist rather than trusting project.yml.
- `Text` in an `HStack` with a trailing `Spacer` takes its ideal single-line width and
  truncates when the row is narrower. `.fixedSize(horizontal: false, vertical: true)`.

Related: [[distinctive-ui-not-slop]], [[interactive-bug-check]], [[signing-keychain-shadowing]].
