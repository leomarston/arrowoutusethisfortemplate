---
name: pair-free-press-paid
description: tvremote's free tier (2026-09-07, owner's call) — finding and pairing ONE TV is free, every command that reaches the TV is Pro; gate it in ONE place and rewrite every claim that the buttons were free
metadata:
  type: project
---

The owner set this model in his own words: *"connecting is free, but any kind of control is paid.
Only connecting is free, and its free for one tv, after connection its paid, the remote buttons and
everything."* It replaced build 2's split (whole remote free for one TV, Pro for phone-side extras).

**Gate it in ONE place.** `RemoteSession.allowControl()` sits in front of all three command funnels
(`send`, `typeText`, `launch`) plus hold-to-repeat. Gating per-button guarantees one gets missed.
A refused command must record **nothing** — the strip reading *No answer* for a command the TV was
never asked is a lie about the TV — and must raise the paywall directly, past any cooldown.
`freeControlTaps` (0) is the knob for "let the TV prove itself once, then lock"; with 0, nobody
sees the TV react before paying, which is a real conversion risk on an app never tested on
hardware.

**Two silent breakages this shape causes**, both found by running the app, not reading it:
- Anything keyed on "the first ANSWERED KEY" is now unreachable for free users. Onboarding
  completed there, so the finder came back at every launch; it has to complete at **pairing**.
- A coach state like *"Get the TV answering first."* becomes a permanent dead end — a free user
  can never leave it. Keep such a line only where it is still achievable.

**The honesty half is the bigger half.** Every "the buttons are free" claim had to go from the app
AND all ten storefronts: *no locked keys*, *every key is free for one TV, forever*, *not a trial of
one*, *four hotkeys are free*, *the free remote keeps working*, and the paywall's *Keep the free
remote* dismiss label. Shipping those beside a locked remote is the actual scam. Also tell App
Review how to exercise the paid path (the weekly plan's 3-day trial unlocks it for a sandbox
account) or they can fairly say the app cannot be evaluated.

Related: [[tvremote-build-state]], [[honesty-copy-no-vendor-impossibility]], [[no-free-trial-toggle]].

**Delete the retired strings, not just the code that used them.** Removing a false claim from the
Swift source leaves the entry sitting in all ten `.lproj` catalogues, and a dead resource string
still ships inside the bundle: *"Keep the free remote"* in a binary whose paywall says *Not now* is
exactly what an auditor greps for. Sweep `App/` and `fastlane/metadata/` for the retired phrases
before archiving, and check the sources first so a key the code still uses is never deleted.
