---
name: tvremote-build-state
description: Couch (Universal TV Remote) — build 2 resubmitted 2026-09-07; nine TV platforms, plain-language UI; the first app designed around the measured funnel; protocol doubles instead of hardware
metadata: 
  node_type: memory
  type: project
  originSessionId: 195160ba-b6c0-4fae-8afc-86456f932056
  modified: 2026-09-06T16:35:59.636Z
---

**"Universal TV Remote - Couch"**, app `6808961238`, slug `tvremote`, accent `#5CE65C`, UTILITIES,
universal. Submitted 2026-09-06 — version 1.0.0, weekly $3.99 (3-day trial) and yearly $17.99 all
verified `WAITING_FOR_REVIEW` through the API. Design: `docs/TVREMOTE-DESIGN.md` (1,141 lines);
per-platform wire specs + skeptic corrections in `apps/tvremote/design/research/*.json`.

**It is the first app built after the funnel was measured** ([[funnel-baseline-2026-09-05]]) and
the funnel is the design: **no onboarding paywall at all**. `PaywallTrigger` may present only
after the TV has visibly answered a key; the yearly card leads; every Pro bullet names its call
site. This deliberately deviates from CLAUDE.md gate 3 (onboarding → paywall → home).

**Build 2 (2026-09-07) drives NINE families**, after the owner's *"THIS IS SUPPOSED TO BE A
UNIVERSAL ONE"*: Roku ECP, Samsung Tizen 2016+, LG webOS 2014+, Vizio SmartCast, Android TV /
Google TV, Sony BRAVIA, Philips JointSpace, Fire TV and Hisense VIDAA. (Build 1 shipped three
while Vizio and Android TV sat complete-and-green but switched off; Android TV only needed
`CodeEntryView`, a screen for the 6-digit code.) Panasonic and Samsung pre-2016 remain "Found,
not supported yet". The honesty screen is GENERATED from `SupportMatrix.supportedInThisBuild`,
never hard-coded — see [[honesty-copy-no-vendor-impossibility]] for why the old Fire TV line was
both false and unmaintainable.

**Build 2 also rebuilt the UI in plain words** ("too many texts and almost everything looks
technical, bro we are selling this to old papas maybe"): no instrument readouts, no small-caps
eyebrows over numbers, sentences an owner would say. Four layout defects were found by LOOKING at
the contact sheet, not by testing — Pro cards pinned to the top of a 13" iPad, a greedy ScrollView
stretching the apps card to full height, the first-success toast lying across the ENTER key, and a
full-width green "Try again" out-shouting the TVs the finder had just found.

**No TV exists on this network**, so nothing is verified against hardware. Every driver is proven
against a Python double in `tools/faketv/` that must FIRST pass the real reference client
(`rokuecp`, `samsungtvws`, `aiowebostv` 0.10 + `bscpylgtv`, `pyvizio`, `androidtvremote2`) — the
double is only trustworthy because a client written against real firmware drives it unchanged.
State at build 2: **440 package tests, 121 fidelity tests across nine platforms, 22 XCUITests
(20 pass / 2 no-TV skips), bug_check 20/20** in dark and light; 10 locales x 505 keys. Port map: `tools/faketv/PORTS.md` (collisions between walk doubles and test
fixtures broke both suites twice).

**Eleven defects were found by driving the app, none by reading it.** The two that mattered:
Pro bullet 1 was **hollow** (a paying user's second TV was never saved — the save was keyed on
"first success ever" and passed a hard-coded `isPro: false`), and the funnel was **wedged**
(handover left `session.screen == .connect`, and the trigger only fires on `.remote`, so the
paywall could never appear after the finder flow). Both now have regression walks. See
[[swiftui-navigation-and-funnel-traps]] and [[capture-doubles-neutral-identity]] for the
reusable lessons.

Localized to the top 10 locales (505 keys × 10 at build 2). Two locale names were **taken by other
accounts** (it, pt-BR) — App Store names are unique per locale; check every locale's name against
its storefront BEFORE `fastlane release`, not one failed upload at a time.
