---
name: swiftui-container-identifier-swallows-children
description: A bare .accessibilityIdentifier on a container is applied to EVERY descendant, overwriting the children's own identifiers
metadata:
  type: reference
---

In SwiftUI a container that is not itself an accessibility element passes
`.accessibilityIdentifier` down to every descendant. camdetect's locked-results
card was marked `net.locked`, and the dump showed its Image, all its StaticTexts
AND its "Unlock the results" Button each reporting `identifier: 'net.locked'` —
the Button's own `net.unlock` was gone, so `app.buttons["net.unlock"]` could
never match.

Fix: `.accessibilityElement(children: .contain)` BEFORE the identifier. That
makes the container its own element and leaves the children's identifiers alone.

**Why:** it reads as a test bug and is actually an accessibility bug — VoiceOver
announces the whole card as one undifferentiated blob. It also wastes a full
15-minute bug_check cycle per guess.

**How to apply:** when a UI test cannot find a control that is plainly on screen,
`print(app.debugDescription)` and read the identifiers rather than theorising
about timing or scrolling ([[xcuitest-hittable-lies]]). If a parent view carries
an identifier, suspect it first. Audit any container in the factory that has an
identifier and also contains identified children.
