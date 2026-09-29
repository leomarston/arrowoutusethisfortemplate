---
name: swiftui-no-a11y-tree-in-unit-tests
description: "A SwiftUI view mounted in a unit-test host exposes NO accessibility identifiers, so \"is this control on screen\" tests must measure pixels"
metadata: 
  node_type: memory
  type: reference
  originSessionId: fc7b699b-a869-4b18-8ef7-1c0149346fa1
  modified: 2026-09-09T17:08:36.706Z
---

Mount a SwiftUI view in a `UIHostingController` inside a unit test and walk it for
`accessibilityIdentifier`: you get **nothing**. Measured on `vincam`'s HomeView —
7 objects walked, all UIViews, **0 carrying an identifier**, with a real window scene
attached and the window key. SwiftUI only materialises its accessibility elements for an
assistive client, and a unit-test host is not one. XCUITest is fine; unit tests are not.

**Why it matters:** a test that asks "is Settings still reachable while the camera is
denied?" via an identifier lookup fails *identically* whether the control is missing or
merely invisible to the harness — it looks like the defect it was written to catch, and
"fixing" the app cannot make it pass.

**What to do instead — measure the render.** Snapshot the window and compare regions:
- Is a control still there? Diff its rect between two states. `vincam`'s Rolls/Import
  strips measured **0.00 levels** of change between a live finder and a denied one, which
  proves nothing covers them far better than an identifier lookup would.
- Is this a panel or a photograph? **Flatness** (fraction of pixels within ±10 luma of the
  region's median) separates them; colour saturation does NOT — a warm dark panel is more
  saturated than the average photo, which ranked every error panel as "more live-looking"
  than the live finder.
- Locate a region from the pixels rather than hard-coding a rect: the bounding box of
  pixels that CHANGED between two states finds the finder; a hard-coded guess landed on
  the camera body.
- Compare with a margin, not a ratio, when values sit near 1 (0.738 × 1.4 > 1 is
  unreachable).

**Also: a detached window never completes `.animation(_:value:)`.** A control mid-fade
renders at its start opacity, so a test looking for "the largest accent blob" found the
wrong control entirely. Mount in a real `UIWindowScene` and `makeKeyAndVisible` when
anything animated matters — `Host.mountVisible` in `apps/vincam/Tests/FilmHarness.swift`.

See [[xcuitest-hittable-lies]], [[verify-real-not-mock]].
