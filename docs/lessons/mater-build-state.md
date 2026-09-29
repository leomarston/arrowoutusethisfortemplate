---
name: mater-build-state
description: Ruler Measuring Tape - Mater — 1:1 Tape Measure copycat, submitted 2026-09-09; English-only, localisation is the open job
metadata:
  type: project
---

`apps/mater` = **Ruler Measuring Tape - Mater**, app `6810365600`, bundle
`com.manycode.mater`. **1.0.0 build 1 submitted 2026-09-09, WAITING_FOR_REVIEW.**

Built on the owner's instruction as a **1:1 functional copycat of Tape Measure** (Level Labs,
id1271546805, 88k ratings). Palette sampled from its App Store screenshots, not eyeballed:
tape yellow `#FFDD00`, level gold `#FFCF2F`, black `#010101`. The signature chrome is the
**black three-unit readout bar** (cm / **in** largest / ft) plus undo · yellow `+` · save.

Tools: AR tape (chained points), height, area, 2D floor plan, on-screen ruler, bubble +
surface level, TV sizer, converter. **Gating per the owner's rule — one simple thing free:**
the ruler is free in full, every other tool is Pro.

`Units.swift` is the contract every tool formats through. Lengths are **metres** internally
(ARKit's unit). Imperial switches to feet-and-inches above 12", and 1/16" fractions carry, so
11.97" prints `12"` not `11 16/16"`.

**ARKit does not run in the Simulator at all** — no camera, no motion sensors either. Every
affected screen says so in plain words; each synthetic preview is
`#if targetEnvironment(simulator)` gated. A `-Capture` DEBUG flag suppresses those notices for
App Store shots only. **The AR measuring has never been verified on hardware** — that is the
single biggest open risk. See [[camera-device-only-bug-classes]].

**Four submit blockers, all reported by Apple as the same useless "not in valid state":**
1. `primaryCategory` unset — deliver skipped it after erroring on review detail. PATCH
   `appInfos/{id}` with `appCategories/UTILITIES`.
2. Subscriptions stuck `MISSING_METADATA` for want of a **review screenshot** —
   `scripts/asc_review_assets.py --slug X --image <paywall.png>`.
3. `TARGETED_DEVICE_FAMILY: "1,2"` means UNIVERSAL, so **iPad screenshots are required**.
   Needed an iPad Pro 13" simulator (2064x2752). See [[ipad-is-a-review-device]].
4. Disk fell to 1.6 GB; an archive will not fit. Simulators are the hog.

Also fixed the blank-screenshot guard from [[screenshots-verify-content-not-count]] — it
false-positived on mater's yellow ruler face (89% one tone). It now requires flat **AND**
featureless (edge density < 1.2%), verified in both directions.

**Open: English only.** 376 UI strings, no `.lproj` tables. The top-10 locale pass
([[localize-top-10-locales]]) is the immediate 1.0.1 job.
