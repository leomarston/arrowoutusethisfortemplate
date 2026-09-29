---
name: funnel-baseline-2026-09-05
description: "Measured portfolio funnel (RevenueCat, production only) as of 2026-09-05 + how to pull it; ASC key cannot read analytics/sales"
metadata: 
  node_type: memory
  type: project
  originSessionId: 195160ba-b6c0-4fae-8afc-86456f932056
  modified: 2026-09-05T10:50:31.982Z
---

**Measured 2026-09-05 from RevenueCat v2 (production env only, sandbox excluded):**
1,023 installs seen by RC since mid-July 2026 (329 in the last 7 days) → 42 subscription
starts (4.1%; 40 weekly trials + 2 direct yearly buys) → 4 weekly trials converted of 28
resolved (14%) → gross $59.28 all-time, proceeds $36.51 (= $0.036 proceeds per install).
Median install→trial start is **1.1 minutes**: the onboarding paywall is effectively the only
monetization surface; in-app Pro gates produce ~nothing. 8 of the 12 trials open that day had
auto-renew already off. `camdetect` (Spot) drove 17 of 42 starts; 11 live apps had zero paid.
The 2 no-trial yearly buys were 66% of gross. TR = 26% of installs, 1 trial. 1 rating across
18 apps in 8 storefronts.

**How to pull it:** `curl` (python urllib fails on SSL) with `RC_SECRET_KEY` (strip the inline
`#` comment from `.env`) against `/v2/projects/{id}/metrics/overview` (project-wide only — no
per-app filter works), `/customers?limit=100` (paginate; no app id on a customer), and
`/customers/{id}/subscriptions` (product_id → app via `/products`). Revenue is
`total_revenue_in_usd.gross/.proceeds` — a dict, not a number. Script kept at the session
scratchpad `funnel/rc_pull.py` (not in repo).

**Blocked:** the ASC API key returns **403 "The API key in use does not allow this request"**
on `/v1/analyticsReportRequests`, and `/v1/salesReports` needs a vendor number that is not in
`.env`. The old spaceship web analytics endpoint is deprecated by Apple. Per-app installs /
impressions / page views are therefore unmeasurable until the user creates an Admin-role ASC
key or pastes the vendor number. There is no in-app funnel instrumentation by rule
([[no-servers-not-no-libraries]]); RC customer attributes would be the rule-compliant way to
attribute installs per app — proposed, not approved.

**Why it matters:** every earlier estimate ($0.20–0.50/install in `docs/AD-NICHE-RESEARCH.md`
round 8) was 5–10× too optimistic; paid acquisition is off the table at this monetization.
Related: [[static-ad-niche-verdict]], [[standard-price-3-99-17-99]].
