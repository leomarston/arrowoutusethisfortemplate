---
name: revenuecat-cancel-does-not-throw
description: Under StoreKit 2 a cancelled RevenueCat purchase RETURNS successfully with userCancelled=true; it never throws
metadata:
  type: reference
---

`try await Purchases.shared.purchase(package:)` does **not** throw when the user cancels.
RC's `Result.init(value:error:)` prefers a non-nil value over a non-nil error, and under
StoreKit 2 (the default in RC 5.x) a cancellation hands back a non-nil `CustomerInfo`
*alongside* the cancellation error. So the call returns normally with
`result.userCancelled == true`, and any `catch ErrorCode.purchaseCancelledError` is
unreachable on that path — even though that catch DOES correctly match the error
(`domain=RevenueCat.ErrorCode code=1`) when one is actually thrown.

**Why it matters:** `soundanalyzer` build 2 read only `entitlements[...].isActive`, found it
false, and fell off the end of its `if` with no else. The CTA spun, stopped, said nothing —
and Apple rejected it under 2.1(b). Four other hypotheses (Paid Apps Agreement, RC config,
ASC config, the iPad change) were investigated and disproven first.

**How to apply:** branch on `result.userCancelled` FIRST, then the entitlement, and always
have an else that tells the user something. Add an entitlement listener so a delayed
activation still unlocks. Never show a raw SDK error string to a user.

**How it was proven:** compile the real RC sources at the pinned revision for
arm64-simulator and run probes with `xcrun simctl spawn` — reading the docs was what
produced two contradictory answers.

Related: [[verify-real-not-mock]], [[paywall-billed-amount-dominant]].
