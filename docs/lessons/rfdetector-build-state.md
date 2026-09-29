---
name: rfdetector-build-state
description: RF Signal Detector - Sweep submitted 2026-08-03; built only on sensors iOS really exposes (BLE RSSI, magnetometer, Bonjour)
metadata:
  type: project
---

**RF Signal Detector - Sweep** (slug `rfdetector`, app id **6797538167**, bundle
`com.manycode.rfdetector`) — submitted 2026-08-03. Version 1.0 + both subscriptions all
`WAITING_FOR_REVIEW`.

**The category is full of fake detectors; this one only claims what iOS can do.**
Hard technical limits, established before writing a line of code:
- iOS has **no API to scan for nearby Wi-Fi networks** and no broadband RF sensor. Any
  app claiming to "detect RF" generally is lying.
- What genuinely works: `CBCentralManager.scanForPeripherals` with
  `allowDuplicates: true` → real RSSI in dBm; `CMMotionManager` magnetometer → µT;
  `NWBrowser` Bonjour → devices on the joined network.
- RSSI does not convert to distance — the app shows coarse proximity buckets, never a
  fabricated metre reading.

Three detectors: Bluetooth (free), magnetic field (free), network scan (Pro).
Onboarding leads with "What a phone can't do" *before* the value slide — deliberate, to
stop day-two one-star reviews.

Gotchas found here:
- **Bonjour needs `NSBonjourServices` in Info.plist** listing every service type, or the
  browse silently returns nothing. An array can't go through `INFOPLIST_KEY_*`, so
  `project.yml` uses an `info:` block with `GENERATE_INFOPLIST_FILE: NO`.
- **XCUITest can't see SwiftUI rows via `app.otherElements[id]`** even with
  `.accessibilityElement(children: .combine)`. Use
  `app.descendants(matching: .any).matching(identifier:).firstMatch`.
- CoreBluetooth and the magnetometer **do not exist in the Simulator**, so the real
  detection path is unverified pre-submit — same caveat as [[twocam-build-state]].
  DEBUG-only demo data renders the screens; release builds never fabricate a detection.
- Signing died on [[signing-keychain-shadowing]]; the upload then hit a transient SSL
  error and was completed with `xcrun altool --upload-app`.
