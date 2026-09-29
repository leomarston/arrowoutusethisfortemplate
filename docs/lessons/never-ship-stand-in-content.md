---
name: never-ship-stand-in-content
description: HARD — a bundled photo/tone/animation standing in for a live sensor must be #if targetEnvironment(simulator), never shippable; twocam+procam shipped a JPEG as the camera feed
metadata:
  type: feedback
---

**The user found this and was furious, 2026-09-03:** *"I LOOKED AT TWOCAM ... IN THE APP
THERE WAS JUST A FUCKING IMAGE. IT WAS NOT EVEN USING THE CAMERA."* He was right.

`twocam` and `procam` bundled a JPEG and rendered it whenever the capture session was not
running. It was **not gated**, so it shipped. On a real device a failed or not-yet-started
session was indistinguishable from a working camera. Worse:
- twocam's **shutter composed the two demo photos and saved them to the user's photo
  library** as a picture they had taken.
- procam fed the same JPEG to the **histogram and the focus-peaking/zebra overlays**, so the
  "pro instruments" were measuring a stock photo.
- `hearup` animated its level meter from a `Timer` in demo mode, and the App Store
  screenshots were captures of that fake arc.

`vincam` did it correctly all along: `#if targetEnvironment(simulator)` for the demo scene,
an honest "CAMERA UNAVAILABLE" panel on device.

**THE RULE.** Any stand-in for live sensor data — photo, tone, animated meter, canned
findings — must be inside `#if targetEnvironment(simulator)` or `#if DEBUG`. On a device the
app shows the real thing or says why it cannot. Never a third option that resembles the real
thing. And never let a stand-in reach a *saved artefact* (a photo, a finding, a recording).

**HOW TO CHECK — the Simulator cannot tell you.** Build for a real device and grep the
binary, with a CONTROL string, or the zero counts prove nothing:

    xcodebuild build -project X.xcodeproj -scheme X -configuration Release \
      -destination 'generic/platform=iOS' -derivedDataPath /tmp/x \
      CODE_SIGNING_ALLOWED=NO CODE_SIGNING_REQUIRED=NO
    strings /tmp/x/Build/Products/Release-iphoneos/X.app/X | grep -c "CAMERA UNAVAILABLE"  # control, >0
    strings ... | grep -c "SceneBack"                                                      # must be 0

The device build also **catches ungated references the Simulator build compiles happily** —
that is exactly how the second twocam site (the shutter) was found.

Related: [[camera-device-only-bug-classes]], [[verify-real-not-mock]], [[interactive-bug-check]]
