---
name: no-network-claim-is-false
description: Never write "no network access at all" in store copy — RevenueCat's subscription check is a network call
metadata:
  type: feedback
---

Every factory app bundles the RevenueCat SDK, so "works entirely offline / no network
access at all" is a false statement in the App Store description.

**Why:** it is a factual claim in public marketing copy, and the factory's whole
positioning is honest copy (cf. the rewrites on `stopdog`, `rfdetector`, `listendetect`).
Caught in all 50 locales of `whitenoise` just before submit.

**How to apply:** write instead — no account, no sign-up, no analytics, no tracking;
nothing is streamed, recorded or uploaded; the only connection the app makes is the
subscription check with the App Store. `strobelight` (app 6804283838) still carries the
overstated wording; fix it on its next revision.

Related: [[whitenoise-build-state]], [[verify-real-not-mock]].
