---
name: podfind-build-state
description: "Earbud Finder - PodFind submitted 2026-08-29; three honest tools, Apple marks kept to the keyword field only"
metadata: 
  node_type: memory
  type: project
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-08-28T23:10:44.247Z
---

`podfind` — **"Earbud Finder - PodFind"**, app **6806362174**, bundle `com.manycode.podfind`,
scheme `PodFind`. v1.0.0 build 1 WAITING_FOR_REVIEW on 2026-08-29, with both subscriptions
(weekly $4.99 + 3-day trial, yearly $29.99). Built on user request, not from the daily queue.

**What it actually does** — iOS gives no third-party app the list of paired Bluetooth
devices, so a "find my earbuds" app has only three honest capabilities, and PodFind is exactly
those three: (1) a locator tone played into whatever `AVAudioSession.currentRoute` is feeding
right now, (2) a CoreBluetooth LE radar plus a hot/cold dial driven by a smoothed RSSI, (3) a
drop map recorded from the audio-route disconnect, with opt-in background location. A Limits
screen states that a flat, cased or out-of-range bud transmits nothing and that the app does
not use Apple's Find My network.

**Identity:** temperature. Cold navy ink `#0A0F1C` heating to amber `#FFB020`; the signature is
a 260° `HeatDial` whose arc runs blue → periwinkle → amber → ember. Cyan is deliberately NOT in
the ramp — cyan→amber passes through green, and green reads as "all good", not "getting warmer".

**Keywords:** every high-volume term here is an Apple mark. They live in the keyword field
only (invisible, editable without a build); name/subtitle/description/screenshots are
trademark-free. See [[no-clone-apps]] and the 5.2.5 rejection that hit `trackdetect`.

Related: [[verify-real-not-mock]], [[infoplist-array-keys-need-a-base-plist]],
[[locale-urls-before-the-length-check]], [[ipad-capture-gotchas]], [[localize-all-50-locales]].
