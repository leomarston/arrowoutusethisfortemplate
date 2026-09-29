---
name: subscription-grace-period
description: "Every app's subscriptions get a 3-day billing grace period (production + sandbox); automated in asc_iap.py"
metadata: 
  node_type: memory
  type: project
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

User standard (set 2026-07-22): **every** app's auto-renewable subscriptions must have a **3-day billing grace period, in BOTH production and sandbox**. Reduces involuntary churn — a subscriber keeps access for 3 days if a renewal payment fails.

Settable via the ASC API (the app resource has a `subscriptionGracePeriod` relationship, id = app id):
`PATCH /v1/subscriptionGracePeriods/{app_id}` → `{optIn: true, sandboxOptIn: true, duration: "THREE_DAYS", renewalType: "ALL_RENEWALS"}`.

Automated in `scripts/asc_iap.py` (`ensure_grace_period`, called after the subscriptions are built). Reco (6791217141) + Pomodoro (6793207626) already have it (user did those two by hand). Related: [[asc-subscription-submission]].
