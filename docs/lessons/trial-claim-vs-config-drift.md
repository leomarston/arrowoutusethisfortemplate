---
name: trial-claim-vs-config-drift
description: A missing ideas.yaml weekly_trial_days ships a listing that promises a free trial the product does not have
metadata:
  type: reference
---

Found 2026-09-10: **ledbanner** (live, READY_FOR_SALE) and **boxingtimer**
(IN_REVIEW) both promised "a 3-day free trial" in the store description AND in
the subscription review screenshot, while having ZERO offers on ASC.

Root cause is config, not code. `asc_iap.py` creates the trial only when
`ideas.yaml` has `<plan>_trial_days`; both apps omitted it, so the lane
correctly created nothing while the copy was written assuming a trial. Nothing
cross-checks the copy against the config.

**The trap that makes it worse:** `ensure_intro_offer` DELETES every existing
offer when `trial_days` is 0. So an app fixed by hand in ASC gets silently wiped
by the next `asc_iap.py` run unless the key is added to ideas.yaml too. Always
fix BOTH.

Two counter-intuitive details when auditing this:
- Offers are stored **PER TERRITORY** — a healthy app shows **175**, not 1. A
  small non-zero count means a partial write (trackdetect once got 13/175).
- `?limit=N` silently caps the count, so a naive query looks like "10 offers".
  Read `meta.paging.total`, or paginate.

**Third occurrence, and why the sweep missed it (2026-09-19):** **spinwheel**
shipped 2026-09-02 with no `weekly_trial_days` key → zero offers, and a REAL
CUSTOMER paid $3.99 with none of the intended 3 free days. It escaped the
2026-09-10 sweep because that sweep compared offers against the LISTING — and
spinwheel's listing never mentioned a trial (the in-app gate correctly hid the
copy too). Lesson: **audit config-vs-ASC, not listing-vs-ASC** — a silent
mismatch harms customers without ever making a public false claim. The owner
found it via the customer charge and (rightly) read it as a trust breach.

**Now guarded in code (2026-09-20):**
- `asc_iap.py` refuses to run when no plan has a trial unless `--allow-no-trial`
  is passed, and after creating offers it RE-READS ASC and exits nonzero if any
  plan with `trial_days>0` has <170 territories (or a 0-trial plan has any).
- `asc_submit.py verify_trial_offers()` runs before ANY submit mutation and
  aborts if config-promised trials are missing in ASC (tested against the exact
  pre-fix spinwheel state).

**How to apply:** audit with the portfolio sweep — for every app compare
`meta.paging.total` on `/v1/subscriptions/{id}/introductoryOffers` against
whether `description.txt` matches /free trial/i. Expect 175 or a deliberate 0.
Fix by calling `asc_iap.ensure_intro_offer` directly (never the whole lane) when
the app is IN_REVIEW, then add the key to ideas.yaml. Since the description is
[[never-touch-keywords-or-description]], the fix is always to make the PRODUCT
match the copy, never the reverse.
