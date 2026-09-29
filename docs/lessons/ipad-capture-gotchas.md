---
name: ipad-capture-gotchas
description: "Capturing a universal app on an iPad — screenshot size is in points, the iOS 26 tab bar is Cells, and the sim needs its own locale + status bar"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-08-28T23:11:41.572Z
---

A universal app REQUIRES an iPad screenshot set in ASC ([[ipad-is-a-review-device]]).
`scripts/capture_shots.py --sim "iPad Pro 13-inch"` runs the same `CaptureTests` there. Three
things bite:

1. **`XCUIScreenshot.image.size` is in POINTS, not pixels.** A 13" iPad is 1032 pt wide, an
   iPhone 17 Pro is 402 pt. A "> 1400" test to pick the output folder sends every iPad shot
   into the phone folder and overwrites the phone set. Use ~700.
2. **iOS 26 draws the iPad tab bar as floating `_UIFloatingTabBarItemCell`s.**
   `app.tabBars.buttons["Hunt"]` matches nothing there, and `app.buttons["Hunt"]` throws on
   multiple matches because the navigation title carries the same label. Tap tabs through a
   helper that tries `tabBars.buttons / cells / buttons / otherElements`, each `.firstMatch`.
3. **The iPad simulator has its own region.** It inherits the Mac's, so a US listing gets
   "176 m away" and a "%100" battery ([[simulator-inherits-mac-region]]). Before capturing:

```bash
xcrun simctl spawn $IPAD defaults write .GlobalPreferences AppleLocale -string en_US
xcrun simctl spawn $IPAD defaults write .GlobalPreferences AppleLanguages -array en-US
xcrun simctl spawn $IPAD defaults write .GlobalPreferences AppleMetricUnits -bool false
xcrun simctl status_bar $IPAD override --time "9:41" --batteryState charged --batteryLevel 100
```

Render with `make_screenshots.py --device ipad13 --raw-dir final-ipad` (2064×2752).

Found shipping [[podfind-build-state]].
