---
name: distinctive-ui-not-slop
description: "User rejects generic default-SwiftUI \"AI slop\" UI; apps need a distinctive, subject-specific visual identity that justifies paying"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

User feedback (2026-07-28, on the bracket app): the default look — system grouped grey cards, `.rounded` fonts, accent-on-white, floating cards — reads as **"AI slop"** and won't convert. They want apps people actually pay for.

**Why:** these are paid subscription apps; a templated look kills trust + conversion. The factory template (`Theme` = systemGroupedBackground/secondarySystemGroupedBackground + `.rounded`) is a starting point, NOT the finished design.

**How to apply — give each app a distinctive identity (use the `frontend-design` skill):**
- Pin a subject-specific aesthetic and build a real design language: custom palette (not system semantic greys), deliberate type (heavy/condensed display + monospaced for data where it fits — drop the default `.rounded`), depth, and ONE signature element that embodies the subject.
- Example that landed: the Tournament Bracket Maker was redesigned into a **dark "broadcast scoreboard"** identity — deep-ink canvas, victory-gold accent, and the signature = a real bracket rendered with gold elbow CONNECTORS (SwiftUI `Canvas`) that light up for decided matches, seed chips, winner-glow rows, a champion card. Dark-only via `preferredColorScheme(.dark)`. That's subject-specific, not a default.
- Override `Theme` colors/type per app (or at least meaningfully), redesign the hero/core screen with a custom layout (not a `List`), and make the home + paywall feel premium. Spend the boldness in one place; keep the rest disciplined.
- Still pass the gates: build green, bug_check green, and (per [[camera-and-payment-testing]]) an ultracode review before submit. Redesign BEFORE submitting, not after.

Related: [[no-clone-apps]], [[signing-submit-gotchas]].
