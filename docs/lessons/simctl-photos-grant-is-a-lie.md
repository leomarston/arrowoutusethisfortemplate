---
name: simctl-photos-grant-is-a-lie
description: simctl privacy grant photos sets the TCC row but PhotoKit still reports undetermined; only tapping the springboard alert works
metadata:
  type: reference
---

`xcrun simctl privacy <dev> grant photos <bundle>` **returns 0, writes `kTCCServicePhotos = 2` into
the device's TCC.db, and does not grant anything.** `PHPhotoLibrary.authorizationStatus(for:
.readWrite)` still answers `.notDetermined`; `tccd` logs `AUTHREQ_RESULT … authValue=1`. It survives
a device reboot and a `grant all`, so no amount of retrying fixes it.

Symptom: every capture on a fresh simulator comes back showing the permission prompt, and a
photo-library app looks broken when it is fine.

**The only thing that works is tapping the springboard alert from XCUITest:**

```swift
let springboard = XCUIApplication(bundleIdentifier: "com.apple.springboard")
for label in ["Allow Full Access", "Allow Access to All Photos", "Allow All Photos", "Allow"] {
    let b = springboard.buttons[label]
    if b.exists, b.isHittable { b.tap(); break }
}
```

So the recipe for a localized capture run is: run the XCUITest ONCE to grant, then drive
`simctl launch` for the rest. `simctl install` over an existing app preserves the grant;
`simctl uninstall` or a fresh device destroys it and the test must be re-run.

Two related capture traps found the same day:
- **The simulator inherits the Mac's region** ([[simulator-inherits-mac-region]]) and passing
  `-AppleLocale` to `simctl launch` is not enough for a *test* run. Set it per device and reboot:
  `simctl spawn <dev> defaults write .GlobalPreferences AppleLocale -string en_US`.
- **A screenshot taken the instant a scan finishes** catches numbers mid-`contentTransition
  (.numericText())` and thumbnails still loading. Wait for the state to settle.

**Faster path once ANY simulator has a real grant: copy the row.** `simctl privacy grant` fails
because it writes `auth_reason` = the wrong value; a row created by a tapped alert carries
`auth_reason=2` (user consent) and `flags=16`, and PhotoKit accepts *that*. So a second device
never needs its own XCUITest run — shut it down, insert the row, boot:

```sql
-- data/Library/TCC/TCC.db  (device must be SHUT DOWN; tccd caches while booted)
INSERT OR REPLACE INTO access
  (service,client,client_type,auth_value,auth_reason,auth_version,
   indirect_object_identifier,flags,last_modified,boot_uuid,last_reminded)
VALUES ('kTCCServicePhotos','<bundle>',0,2,2,2,'UNUSED',16,
        CAST(strftime('%s','now') AS INTEGER),'UNUSED',0);
```

Verified 2026-09-12 seeding an iPad for FreeUp's store captures: before the row the app read
"0 photos · in 0 groups" on a library whose `Photos.sqlite` already held 160 `ZASSET` rows — so
**check the authorization before blaming the media import**, and note that an unauthorized library
renders as a plausible "All clear" empty state, not as an error.
