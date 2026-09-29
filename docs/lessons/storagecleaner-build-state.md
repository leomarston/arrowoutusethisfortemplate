---
name: storagecleaner-build-state
description: Storage Cleaner - FreeUp (id 6808934868) — photo-library cleaner; 1.2.0/build 10 submitted 2026-09-14 with a 5-a-day free delete cap
metadata:
  type: project
---

**Storage Cleaner - FreeUp**, bundle `com.manycode.storagecleaner`, App Store id **6808934868**.
1.0.0 (build 9) and 1.1.0 (build 10) are both **READY_FOR_SALE**; **1.2.0 / build 10 →
WAITING_FOR_REVIEW on 2026-09-14** (14 store locales, 140 screenshots, both subscriptions already
APPROVED so the submission carries one item). Build numbers are per-train, so 1.1.0 and 1.2.0 can
both be build 10.
Keywords (owner-supplied, en-US): `storage cleaner,clean up storage for iphone,cleanup phone storage
cleaner,photo cleaner`. Localized to **14** locales in-app and on the store: the top 13 ([[localize-top-13-locales]]) plus
**ru**. The store dir is `sl-SI`, the `.lproj` is `sl`.

**What it is:** finds byte-identical duplicates, burst runs, screenshots, similar photos, chat-app
media and large videos; compresses video; measures freed space honestly. Entirely on-device — the
only network call is the RevenueCat subscription check. **Monetisation, from 1.2.0** — copied off the leader ([[free-tier-copies-the-leader]]): scanning,
grouping and reviewing are free and unmetered; the free plan deletes **5 photos a day**
(`DeleteQuota`), and Pro removes the limit. Pro also = similar photos, chat media, video
compression. Prices $7.99/wk and $29.99/yr, and the 7-day trial sits on the **weekly** (moved off
the annual in 1.2.0, 175 territories). No lifetime — the owner ruled it out.

**Builds 1–2 were the rejected design.** Build 3 replaced the whole SwiftUI layer with the
category's own language — see [[copycat-the-category]] and `docs/CLEANER-DESIGN.md` §13 for the
measured teardown of the eleven leading cleaners.

**The engine is the asset; do not disturb it.** Every threshold in it was calibrated against ground
truth, not screenshots: similarity over 1,223 real photo pairs (different-photo floor 0.3373 →
thresholds 0.20/0.22 at ≥1.5× margin), duplicates verified against planted sha256 sets, video sizes
byte-for-byte, compression measured at 29.8 MB → 5.8 MB on real 4K.

**Design decisions that look like bugs but are not:**
- **Large videos is the only module that does not pre-tick.** Everywhere else the app can point at
  a reason an item is redundant; a big video is simply big, and unique. `CleanModule.preselects`.
- **The storage bar has three segments, not the category's four.** iOS publishes no photos/videos
  /apps breakdown, so competitors invent it. Ours shows freeable / rest-of-used / free, all read.
- **The commit button's second line is absent until the bytes are measured** — never "≈", never a
  projection. `ModuleSizer` reads the real bytes in the background, bounded by 1,200 assets per
  module and a 60s shared wall clock; a partial read renders with a leading "≥".
- **"All clear" is never printed for a pass that did not run.** The similar module reads "Not
  checked yet", or "Could not run on this iPhone" when Vision refuses (which it always does on the
  Simulator — the thresholds are checked by `tools/similarity_check.swift` on macOS instead).

**Simulators:** `FreeUp Shots Phone` / `FreeUp Shots Pad` were created deliberately with names no
"newest iPhone Pro" heuristic will match, after a parallel session installed a different app on the
shared simulator mid-capture. Keep doing that — see [[parallel-agents-and-simulators]].

**1.1.0 (2026-09-12) — pl/sk/sl-SI/ru + two dead localization lookups.** Two strings were
translated in every catalog and never looked up, so they rendered English everywhere; both are
documented as a reusable audit in [[localizedstringkey-not-string]]. Because the defect predated
the live listing, **all 14 locales were re-shot on both devices, not just the 4 new ones** —
"3 found" was baked into the screenshots of all 10 shipped storefronts.

Process notes worth reusing:
- `deliver` still cannot upload screenshots here, so the lanes are split. Added an **`upload_text`**
  lane (metadata, `skip_screenshots: true`); screenshots go through `scripts/asc_screenshots.py`,
  which clears each set first so re-uploads do not accumulate ([[deliver-force-appends-screenshots]]).
- **`usesIdfa` does not carry over to a new version.** 1.1.0 came out of `upload_build` with
  `usesIdfa=None` although 1.0.0 had `True` — `deliver`'s `submission_information` does not apply
  when `submit_for_review: false`. This app links FacebookCore, so it must be `True`
  ([[idfa-declaration-and-invalid-binary]]). A plain `PATCH /v1/appStoreVersions/{id}` **succeeds
  even in WAITING_FOR_REVIEW**, so no cancel-and-resubmit was needed. Check it on every update.
- Proving the ASO rule was honoured is cheap and worth doing: snapshot every locale's
  `keywords`/`description` before touching anything, then diff after. Both came back byte-identical
  on all 10 live locales, and `asc_keywords.py --dry-run` reported "would write 4, unchanged 10".
- The iPad simulator needed its photo-library grant copied from the iPhone one
  ([[simctl-photos-grant-is-a-lie]]); without it every frame was a plausible "All clear" empty state.

