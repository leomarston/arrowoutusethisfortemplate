---
name: honesty-copy-no-vendor-impossibility
description: Never write "brand X offers no way for apps to do this" — it is a claim about someone else's protocol that goes false the moment you build it; state what YOUR app cannot do, and drive the list from the support matrix
metadata:
  type: feedback
---

`tvremote` shipped build 1 saying, verbatim, *"Fire TV. Amazon offers no remote-control connection
to other apps."* and *"Apple TV. Apple does not provide a way for other apps to control it."* The
first was simply **false** — Fire TV has a DIAL + remote service, and the app now drives it. The
second is unverifiable and not worth defending.

**Why:** an impossibility claim about another company's protocol is a claim you cannot check and
cannot maintain. It also freezes the app: the honesty screen said "not supported" in hard-coded
sentences, so switching a driver on would have left a screen contradicting the binary — and under
2.3.1 the store copy and the in-app copy have to agree.

**How to apply:**
- Every "cannot" line is a statement about **your app**: *"Control Apple TV. Use the Apple TV
  Remote in Control Centre instead."* — not about what the vendor publishes.
- A family you have not built yet is **"not supported yet"**, never "impossible".
- Generate both lists (*Works with* / *Not yet*) from the single source of truth in code
  (`SupportMatrix.supportedInThisBuild`), so the screen cannot go stale.
- Re-read the App Review notes when the support set changes: on tvremote they still described a
  three-platform app after nine shipped.

Related: [[tvremote-build-state]], [[verify-real-not-mock]], [[no-network-claim-is-false]] (the same
failure in the other direction — a claim that was too generous to the app).
