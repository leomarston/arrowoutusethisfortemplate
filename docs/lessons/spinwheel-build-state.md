---
name: spinwheel-build-state
description: "Spin the Wheel (sealed draw) submitted 2026-09-02 — pick the winner FIRST with a CSPRNG, animate the wheel onto it, read it back before announcing"
metadata: 
  node_type: memory
  type: project
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-09-02T13:19:49.582Z
---

**Spin the Wheel: Sealed Draw** (`spinwheel`, app `6807786487`, bundle `com.manycode.spinwheel`)
submitted 2026-09-02. Version 1.0.0 + both subscriptions WAITING_FOR_REVIEW in one review
submission. Weekly $4.99 (3-day trial) / yearly $29.99. 50 metadata locales, 49 in-app
languages, universal (5 iPhone + 5 iPad screenshots).

**The counter-intuitive core:** picking the winner first with a CSPRNG and animating the
wheel onto it is the FAIR option; simulating physics and reading what comes up only looks
fair. A physics wheel's final angle is a deterministic function of start angle + flick, so a
practised push repeats, and the wheel starts where the last spin stopped, so consecutive
draws correlate. Design details in PROJECT_LOG.md §8 — whole extra turns only, settle
back-off scaled to the wedge, cumulative-bounds array instead of a segAngle, and a read-back
that is compiled into Release (not `assert`) but recovers by redrawing rather than halting.

**4.3 separation from `bracketmaker`:** one spin returns exactly one name and the app never
makes a second assignment. Cycle mode only takes the winner out. The history is a flat log —
never a grid, table or standings.

**Keyword note to raise with the user:** their en-US keyword `tiny decision` is close to the
live competitor app *Tiny Decisions*. Shipped verbatim because keywords are user-owned
([[keywords-are-user-owned]]), but it carries Guideline 2.3.7 risk if Apple reads it as a
competitor name.

Related: [[no-clone-apps]], [[app-naming-keyword-first]], [[localize-all-50-locales]],
[[verify-real-not-mock]]
