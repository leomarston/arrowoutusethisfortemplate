---
name: no-free-trial-toggle
description: "Apple 3.1.2(c): a free-trial on/off toggle on the paywall gets the app rejected — plan cards must state their own terms"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: af304055-c323-4932-95ec-dca1c6b99b7b
  modified: 2026-08-07T16:52:51.218Z
---

**Never put a "Free Trial Enabled" toggle (or any switch that adds/removes the trial) on
a paywall.** Apple rejected `bracketmaker` v1.0.0 on **2026-08-06** under **Guideline
3.1.2(c) — Business: Payments: Subscriptions**, submission `5dc61645-245d-4519-86fd-c89364b96a04`:

> The purchase screen includes a toggle to add or remove a free trial from the subscription
> purchase. This design is confusing and may prevent users from understanding that they are
> committing to an auto-renewing subscription that will begin charging them after the free
> trial period.
> …Remove the toggle… Users should be presented with a clear subscription offer that
> explicitly states whether a free trial is included.

**Why it mattered so much here:** the toggle came from `template/App/Paywall/PaywallView.swift`,
so it shipped in **all 13 factory apps**. Note it is NOT an automatic rejection — `reco` and
`partylights` were **approved** with the same toggle. It is reviewer-dependent, which makes it
the worst kind of latent defect: it passes often enough to look fine.

**The compliant shape (already in the template) is per-plan disclosure, no toggle:**
each `planCard` states its own terms — "3-DAY FREE TRIAL" + "$3.99/week after" on the weekly
card, plain "$17.99/year" on the yearly — plus the CTA "Start My 3-Day Free Trial" and the
`renewalDisclosure` line ("Auto-renews at $3.99/week after the 3-day free trial ends. Cancel
anytime."). Deleting `trialToggleRow` + `trialToggleBinding` (and the now-dead `yearlyPackage`)
needs **no copy rewrite** and breaks no UITest.

**How to apply:** the template is fixed (with a comment forbidding reintroduction), and the
toggle is now gone from **every** app in the repo — all 13 plus the template.

*Decision history (the user reversed it, so don't re-litigate):* on 2026-08-06 the call was
"dont pull them just do the one we are on" — bracketmaker only. The next day they overrode it:
"make sure you fix them and send to submit again," so all 9 apps sitting in WAITING_FOR_REVIEW
were pulled, fixed, rebuilt and resubmitted, knowingly giving up their queue positions.
`reco` (live) and `partylights` (live) and `pomodoro` (developer-rejected) got the **code** fix
but were NOT resubmitted — resubmitting a live app is a new-version decision that is the user's
to make.

**Gotcha found while verifying:** `strings` on `Foo.app/Foo` finds nothing — Xcode 16 puts the
app code in `Foo.app/Foo.debug.dylib` and leaves a ~57 KB stub as the main executable. Always
grep the `.debug.dylib`, and always include a control string you know is present, or an absent
match is meaningless.

Related: [[camera-and-payment-testing]] (2.3.1 advertised-features rule), [[signing-submit-gotchas]].
