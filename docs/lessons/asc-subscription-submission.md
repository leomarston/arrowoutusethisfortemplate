---
name: asc-subscription-submission
description: How to submit first-version app + new subscription group for review via ASC API — needs version + subscriptionGroupVersion + subscriptionVersion items together
metadata: 
  node_type: memory
  type: reference
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

Submitting an app whose subscriptions are in a **new** subscription group (no prior approved version) via the App Store Connect API. `fastlane deliver`/`release` only submits the app version — subscriptions do **not** auto-bundle, and neither the public API nor the iris/Spaceship API accepts a `subscription` (or `inAppPurchase`) relationship on `reviewSubmissionItems`. Both `deliver` and manual version-only submission leave subs stuck in `READY_TO_SUBMIT`, which risks a first-review rejection (paywall referencing unreviewed IAPs).

**Correct mechanism — one review submission containing FOUR item types:**
1. `POST /v1/reviewSubmissions` `{platform: IOS, app}` → get `rs_id` (cancel any open one first; a cancel flips the version to `DEVELOPER_REJECTED` and needs a few seconds to propagate, so retry the version-item add).
2. `POST /v1/reviewSubmissionItems` with relationship `appStoreVersion` → the version.
3. `POST /v1/reviewSubmissionItems` with relationship `subscriptionGroupVersion` → the group's inflight version (`GET /v1/subscriptionGroups/{gid}/versions`, pick the non-approved one).
4. `POST /v1/reviewSubmissionItems` with relationship `subscriptionVersion` → **each** subscription's inflight version (`GET /v1/subscriptions/{sid}/versions`).
5. `PATCH /v1/reviewSubmissions/{rs_id}` `{submitted: true}` → `WAITING_FOR_REVIEW`.

Why all four: a new group errors `SUBSCRIPTION_GROUP_SUBMISSION_NOT_ALLOWED` ("submit at least one subscription first") if you submit the group version alone; a subscription version errors `SUBSCRIPTION_SUBMISSION_REQUIRES_GROUP_VERSION` if submitted without the group version. They must go together. Reco's working submission has exactly 4 items → this is the shape.

**App-level prereqs for a FIRST version (else the appStoreVersion item 409s with `contentRightsDeclaration required` + `APP_PRICING_REQUIRED`, hit on wifispeed 2026-07-22):** the app needs `contentRightsDeclaration` set (`PATCH /v1/apps/{id}` → `DOES_NOT_USE_THIRD_PARTY_CONTENT`) and a price schedule — for a free app, `POST /v1/appPriceSchedules` with the USA base territory + the $0 `appPricePoint` via an inline `${...}` local id. Both are now auto-handled by `asc_submit.py`'s `ensure_submission_prereqs`. (Age rating is set by `deliver`'s defaults; it did not block.)

Gotchas: the `/reviewSubmissions/{id}/items` sub-endpoint returns empty/unreliable — use `?include=items` on the submission instead. Read the real blocking reason from the 409 `meta.associatedErrors`. Automated in **`scripts/asc_submit.py --slug <slug>`** (Faz 11). Related: [[revenuecat-asc-key-required]], [[reco-build-state]].
