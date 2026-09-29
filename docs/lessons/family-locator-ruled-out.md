---
name: family-locator-ruled-out
description: RULED OUT 2026-09-10 — a family locator needs a relay; Find My has no API and CloudKit needs a one-time web-dashboard token the owner declined
metadata:
  type: project
---

Built `phonetracker` ("Phone Location Tracker - Kin", a Findo id1348649804
copycat) to a working state — build green, 28 unit tests passing, running on a
real map — then **removed it entirely at the owner's instruction**. Do not
rebuild it without a new explicit go-ahead.

**The physics, established properly so it need not be re-derived:** showing
another person's position requires their phone's data to reach yours. There is
no on-device route.

| Option | Verdict |
|---|---|
| **Find My** | NO public API. The only third-party door is the Find My Network **Accessory** programme — MFi hardware, not apps. Apple's own Find My already does free family sharing, which is why this category sells history/geofences/battery rather than the map. |
| iCloud KVS / Drive | Syncs only between ONE person's own devices. Different Apple IDs cannot share. |
| MultipeerConnectivity | Bluetooth/Wi-Fi, ~30 m. |
| Nearby Interaction (U1) | A few metres, both apps foregrounded. |
| APNs push | Sending requires a server. |
| **CloudKit + CKShare** | The only serverless answer. Works. |

**Why CloudKit still got declined:** an App Store build talks to CloudKit
**Production**, record types do NOT auto-create there (only in Development), and
promoting the schema needs `xcrun cktool import-schema` with a management token
that only Apple's CloudKit web Dashboard issues. Every path — cktool, web
services API, server-to-server keys — routes through that dashboard once. The
owner preferred to drop the app over doing that setup.

**How to apply:** if a future idea needs two phones to exchange anything live,
it needs CloudKit, and CloudKit needs that one-time token — surface this BEFORE
building, not after. An offline-only fallback exists as a product (personal live
map + location history + route replay + own-geofence alerts + trips + manual
Maps-link share) but it cannot honestly target find-my-family search intent,
which is the only thing that makes the keyword valuable.

**Salvage kept:** `scripts/signing_setup.py` gained `ensure_capabilities()`,
which opens the App ID capabilities implied by an app's own `.entitlements`
BEFORE creating the profile (a profile freezes its entitlement set at creation).
Verified a no-op for all 33 remaining apps. See [[no-servers-not-no-libraries]]
and [[static-ad-niche-verdict]] — that round-14 research had already killed the
family-locator niche once, on ad-honesty grounds.
