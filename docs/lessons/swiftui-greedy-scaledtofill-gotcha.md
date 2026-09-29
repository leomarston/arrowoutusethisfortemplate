---
name: swiftui-greedy-scaledtofill-gotcha
description: A scaledToFill Image inside a reusable .background view silently breaks parent layout across the whole screen
metadata: 
  node_type: memory
  type: reference
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

**`Image(uiImage:).resizable().scaledToFill()` placed inside a view you then use as `.background(...)` reports a greedy ideal size that corrupts the WHOLE layout** — collapsing sibling views' content behind the Dynamic Island, clipping other views mid-way, leaving huge gaps. It builds clean (no error) and the symptom looks like a mysterious layout bug everywhere, not at the image.

Hit while building VinCam's tactile "plastic camera" UI: a `PlasticSurface` helper (ZStack with gradients + a `scaledToFill` noise image) used as `.background()` on several controls broke the entire viewfinder screen. Removing/《replacing》 the noise image fixed it instantly.

**Fix:** never let a `scaledToFill` (or `.frame(maxHeight: .infinity)`) image be the greedy element inside a reusable background/material view. Options: tile it with `Image(uiImage:).resizable(resizingMode: .tile)` wrapped in `Color.clear.background(...)` (non-greedy), or drop it and use gradients only. General rule: a `.background`/material subview must be size-neutral — no greedy children.

Debugging technique that pinned it: add `.background(.red)` / `.border(.color)` to each VStack section → showed the top section was tall-but-empty (content shoved behind the notch), which pointed at a greedy background rather than the content.

**SECOND BITE (Kitz, 2026-08-01) — it also breaks TAP TARGETS, not just visuals.** A grid tile `Button` whose label was `ZStack { Image(bg).resizable().scaledToFill().frame(height:150).clipped(); Image(prey).frame(maxWidth:.infinity,maxHeight:.infinity); … }.frame(height:150)` rendered correctly BUT the button's real frame was **180×388** (vs the 150pt tile) — so `element.tap()` hit the center of an inflated frame, landing outside the visible tile, and the action never fired. Symptom: one tile works, another silently does nothing; XCUITest reports `isHittable = true` while the tap does nothing. `.clipped()` clips the DRAWING, not the layout/hit region.

**Diagnosis that nailed it:** log the element frame in the UI test — `NSLog("hittable=%d frame=%@", el.isHittable, NSCoder.string(for: el.frame))`. A frame much larger than the intended cell = greedy child. Also dump `app.buttons.allElementsBoundByIndex.map(\.identifier)` after the tap to see whether the expected screen appeared.

**Fix pattern (bounded box):** `Color.clear.frame(height: H).frame(maxWidth: .infinity)` as the layout anchor, then put the scaledToFill background, gradient, prey and label in `.overlay { … }` layers, then `.clipped()`. Layout is fixed by Color.clear; greedy children can't inflate it. Same recipe fixed the VinCam viewfinder (`Color.clear.aspectRatio(3/4, contentMode: .fit)` + overlays).
