---
name: submit-without-subscriptions
description: asc_submit could submit an app with ZERO subscriptions right after a cancel; now retries + hard-exits
metadata:
  type: project
---

Right after `asc_submit.py` cancels an open review submission, the subscription **group version
and subscription versions stay non-editable for minutes** (`REJECTED`/`IN_REVIEW` →
`DEVELOPER_REJECTED` propagation). The old code read them **once**, found nothing editable,
printed `sub_versions=0`, and submitted the **app version alone**.

Hit on `stopdog` 2026-08-20 — caught only by checking the sub states after the run, not by the
script's own "OK" output.

**Why:** an app approved that way ships a paywall with nothing purchasable — it looks like a
clean success in every log line.

**How to apply:** `scripts/asc_submit.py` now retries the group/sub lookup ~3 min, skips only
when the group is already APPROVED/LIVE, and **exits rather than submitting a subscription app
without its subscriptions**. After ANY submit, verify sub states independently
(`/v1/subscriptionGroups/{gid}/versions` + each subscription's versions), don't trust the
"OK ... WAITING_FOR_REVIEW" line.

Related: [[asc-subscription-submission]], [[signing-submit-gotchas]]
