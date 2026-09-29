---
name: paywall-billed-amount-dominant
description: Apple 3.1.2 — the billed amount must be the most conspicuous pricing element; trial and per-week maths must be subordinate
metadata:
  type: project
---

**Apple rejected `bluetoothmic`, `twocam`, `stopdog` and `rfdetector` on 2026-08-21** (this is
the reason that was unknown through three blind resubmissions):

> The auto-renewable subscription promotes the free trial ... more clearly and conspicuously
> than the billed amount ... displays the yearly calculated pricing ... more clearly and
> conspicuously than the billed amount.

**What was wrong:** the plan card showed "3-DAY FREE TRIAL" in the **accent colour** with the
real price under it in secondary grey at the *same* size, plus "≈ $0.35/week" as prominent as
the actual $17.99/year charge. The CTA said "Start My 3-Day Free Trial" and the disclosure
opened with "Auto-renews at ... after the free trial".

**The compliant shape (now in `template/` + all 4 apps):**
- `billedAmount()` — 24pt **bold, primary colour**: `$3.99` + `/week` (14pt secondary)
- `subordinate()` — 11pt **tertiary** for the trial line and the ≈/week maths, BELOW the price
- Plan title ("Weekly") demoted to caption/secondary so it does not compete
- CTA is **"Subscribe"**, never trial-forward
- Disclosure leads with price: "$3.99/week, starting after your 3-day free trial. Auto-renews
  until canceled."

**How to apply:** never restyle `billedAmount`/`subordinate` in `PaywallView.swift`. Any new
pricing element (intro offer, discount, per-day maths) goes in `subordinate`. Prices themselves
were NOT changed — weekly $3.99 + 3-day trial, yearly $17.99.

Related: [[no-free-trial-toggle]], [[submit-without-subscriptions]]
