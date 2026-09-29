---
name: att-prompt-is-one-shot-too
description: Never assert that the ATT prompt APPEARS — an earlier test in the same run consumes it, exactly like the photo prompt
metadata:
  type: reference
---

`testCaptureOnboarding` asserted the App Tracking Transparency alert appears, and failed on a
perfectly healthy app: an earlier test in the same run had already answered it. ATT is one-shot per
install, exactly like the photo-library prompt.

**Why:** The assertion was trying to prove the Meta SDK is linked and `NSUserTrackingUsageDescription`
ships. A one-shot system prompt cannot carry that proof — it is order-dependent and silently
decays as the suite grows.

**How to apply:** Answer the prompt if it shows (`_ = answerTrackingPrompt()`), never assert it
did. Prove linkage where it cannot go stale: read the built binary and the built Info.plist
(`MetaSDKLinkageTests`). To genuinely re-test the prompt, `xcrun simctl privacy <sim> reset tracking <bundle>`
first.

Related: [[permission-prompt-is-one-shot]], [[simctl-photos-grant-is-a-lie]], [[meta-sdk-wiring]].
