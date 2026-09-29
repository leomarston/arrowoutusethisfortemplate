---
name: stopdog-build-state
description: Dog Whistle - StopDog submitted 2026-08-03; user rejected a frequency-generator UI and rejected fabricated frequency claims
metadata:
  type: project
---

**Dog Whistle - StopDog** (slug `stopdog`, app id **6797339926**, bundle
`com.manycode.stopdog`) — submitted 2026-08-03. Version 1.0.0 + both subscriptions all
reached `WAITING_FOR_REVIEW`.

Two corrections the user made mid-build, both worth remembering as general rules:

1. **Don't build a frequency generator when the user asked for a dog whistle.** The first
   version had a tuning dial (100 Hz–22 kHz, log scale, drag to tune). The user's reaction:
   "THIS IS NOT A FUCKING FREQUENCY GENERATOR APP ... YOU CLIK IT, IT OPENS THEN IF YOU
   WANT YOU STOP IT, THAT SIMPLE." Shipped shape is a 6-card grid — tap a card, it plays,
   tap again to stop. No dial, no numbers to set.

2. **Never invent a mechanism that doesn't exist.** The cue copy originally claimed
   frequencies caused behaviours ("Come Here", "Settle Down" @ 7 kHz, "Stop Jumping"),
   which is false — a whistle tone has NO innate meaning to a dog and no frequency calms
   one. The user spotted it ("they are feeling scammy, does come here really work?").
   Rewrote to honest framing: six *distinguishable signals* you condition by pairing with
   a reward; the only causal claim kept is the bark interrupter breaking focus, which is
   real. `TrainingModels.swift` carries a comment forbidding reintroduction of the claims.
   This is also 2.3.1 rejection avoidance — see [[camera-and-payment-testing]].

Technical note: `.repeatForever` SwiftUI animations make XCUITest hang — the app never
reaches idle, so the bug-check went flaky. Removed the emitting ripple for that reason.
