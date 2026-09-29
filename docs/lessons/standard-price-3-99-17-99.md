---
name: standard-price-3-99-17-99
description: HARD — factory subscription price is $3.99/week (3-day trial) + $17.99/year; six apps drifted to 4.99/29.99 and need fixing
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-09-03T16:21:27.874Z
---

**The factory's subscription price is $3.99 weekly with a 3-day free trial, and $17.99
yearly.** The user's words, 2026-09-03: *"BRO, SINCE THE BEGINNING WE ARE APPLYING
$3.99/$17.99"*. 25 of the 33 `ideas.yaml` entries carry exactly that.

**Why it drifted:** `scripts/asc_iap.py` reads prices from each idea's `pricing:` block, and
`plans_from_pricing()` has a stale fallback of `("monthly","4.99"),("yearly","29.99")`. Six
newer ideas were written with 4.99/29.99, so `asc_iap.py` faithfully created them at the
wrong price. **Do not trust an idea's `pricing:` block — check it against 3.99/17.99 first.**

**Apps live/in-review at the WRONG price (4.99/29.99), not yet corrected — ASK the user
before touching them, [[one-app-per-task]]:** `podfind`, `noisemeter`, `watereject`,
`boxingtimer`, `ledbanner`. (`spinwheel` was corrected 2026-09-03.)

**How to reprice an app that is already submitted:**
1. Fix `pricing:` in `ideas.yaml`.
2. A CURRENT `subscriptionPrice` cannot be DELETEd ("Only future price changes can be
   deleted") — POST a new `subscriptionPrices` with the target price point and
   `preserveCurrentPrice: false`. That supersedes it. Do it for the USA point AND every
   `equalizations` point, or the untouched territories keep the old price.
   `ensure_price()` will NOT help: it only fills territories that have no price at all.
3. Revert the DEBUG demo-paywall literals in `PaywallView.swift` (amount, the per-week
   figure, and the two subscription-disclosure strings). **That capture is what Apple
   attaches to each subscription as its review screenshot**, so a stale price there is a
   3.1.2 contradiction.
4. Those literals are KEYS in `design/strings_en.json` — rename them in all 49 `.lproj`
   files and re-run `tools/keys.py`, or the table goes stale.
5. Fix `fastlane/metadata/review_information/notes.txt` if it quotes the price.
6. The review screenshot CANNOT be replaced while the submission is open
   (`MEDIA_ASSET_DELETE_NOT_ALLOWED`): cancel the reviewSubmission, wait for the subs to
   leave the review state, `asc_review_assets.py --force`, then `asc_submit.py` again.

The uploaded BINARY does not need rebuilding for a price change — the live paywall reads
prices from StoreKit at runtime, and the demo literals are DEBUG-only.

Related: [[paywall-billed-amount-dominant]], [[no-free-trial-toggle]], [[one-app-per-task]]

**2026-09-06 — the first deliberate exception: `storagecleaner` is $7.99/week and $29.99/year with
a 7-DAY trial on the ANNUAL plan.** Those are the category leader's own numbers, read off its App
Store page (it price-tests $5.95–$11.99 weekly; $7.99 is the modal SKU). The owner instructed the
copy explicitly. Two things worth carrying to other apps: the leader puts its trial on the annual
plan, not the weekly, and it charges double the factory rate — the factory price may be leaving
money on the table wherever a competitor's page can be checked.

`scripts/asc_iap.py` could only ever FILL price gaps, so changing a price on a live subscription
silently did nothing. It now takes `--reprice` (writes the new point to every territory) and a
`*_trial_days: 0` DELETES an existing introductory offer instead of leaving a second trial live.
