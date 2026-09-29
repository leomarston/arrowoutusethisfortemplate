---
name: arrowout-build-state
description: "Arrow Out (slug mazeout) — 1:1 Maze Out copy, submitted 2026-09-30 01:2x with 12 consumables + Meta SDK; where everything lives and what is still open"
metadata:
  node_type: memory
  type: project
  originSessionId: 67834757-7bc9-4e4f-a907-36f39cf8e3e8
  modified: 2026-09-29T22:23:08.738Z
---

**Arrow Out: Arrow Escape Puzzle** — slug `mazeout`, bundle `com.manycode.arrowout`, ASC app 6816880848, branch `build/mazeout`
(commit via the private-index recipe in apps/mazeout/PLAN.md; the factory checkout is on another app's branch).
1.0.0 build 1 uploaded 2026-09-30 01:17, VALID 01:20, submitted ~01:2x (reviewSubmission 659f0b29…, 13 items = version + 12 IAPs).

- Monetisation: 12 consumables (coins.1000…100000, bundle.mini/mega/epic/elite/legendary, offer.special), no subscriptions, so
  no Restore button by design (notes.txt explains). RevenueCat observer mode (recordPurchase), app app5e0e8dfedb, offering
  arrowout_shop. Payments verified by RC read-back, NOT a device purchase (owner's call, SPEC ruling 57).
- Meta SDK (FacebookCore 18.1.1) for our own install ads, SPEC ruling 58: token only in the factory .env → built Info.plist;
  store lanes run tools/meta_dashboard_check.py (dashboard auto-log + AAM must stay OFF). ATT once after the L6 win.
  App Privacy label with tracking uploaded 09-30 00:56; usesIdfa true; privacy page privacy-arrow-out.html.
- Levels: 150 authored (99 are the original's boards, from videos/phone recordings; L34-105 re-ordered; L1-33 in the
  original order) + endless 151+ from the deterministic generator. Owner 09-30: keep them for now; replacing the copied
  boards is the known fix if a copyright complaint ever comes.
- Sims: slot A 177520B6 (build/dd-A), slot B B80EDB24 (owner's manual test sim).
- Template repo for future games: leomarston/arrow-out (private, GitHub template), pushed after the submission.

**Open after approval:** add the App Store ID to the Meta app (~24 h after live), link the owner's FB Page, check the first
real RevenueCat transactions, F8 probe() UI-test flake. If the version goes INVALID_BINARY: [[idfa-declaration-and-invalid-binary]].
Related: [[meta-sdk-wiring]], [[gameprompt]], [[apple-session-30-days]], [[device-install-can-wipe-save]].
