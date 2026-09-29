---
name: permission-button-must-not-direct
description: HARD — the button that leads to a system permission prompt must say Continue/Next, never "Allow X access"; 5.1.1(iv) rejection on storagecleaner build 8
metadata:
  type: reference
---

**Apple rejected `storagecleaner` build 8 under Guideline 5.1.1(iv)** for one word on one button.
Their wording:

> The app encourages or directs users to allow the app to access the photo library… A custom
> message appears before the permission request, and to proceed users press a "Allow photo access"
> button. **Use words like "Continue" or "Next" on the button instead.**

**The rule:** a pre-permission explainer screen is fine and Apple encourages it — but the BUTTON
that leads to the system prompt must be neutral. Anything that pre-frames the answer counts as
directing: "Allow…", "Grant…", "Enable…", "Turn on…", "Give…". This applies to every factory app
with a permission primer, not just photos — microphone, camera, local network, notifications.

**The second half, from their own Next Steps, and worth fixing at the same time:**
`requestAuthorization` is one-shot. Once someone declines, it returns the stored answer **without
showing anything**, so a button that calls it again is a dead end — the user taps and the screen
never changes. Detect it and offer Settings instead:

    var isBlocked: Bool { status == .denied || status == .restricted }
    // title: isBlocked ? "Open Settings" : "Continue"
    // action: isBlocked ? openSettings() : request()

Apple explicitly suggests this ("provide a link to the Settings app"), so it reads as compliance
rather than a workaround.

**Testing it:** assert the LABEL, do not drive the prompt. A UI test that taps through the system
alert consumes the one-shot prompt and leaves the simulator permanently denied, which then breaks
every other test on that device — and `simctl uninstall` does NOT clear the resulting TCC row
(observed `auth_value=0` surviving an uninstall). See [[permission-prompt-is-one-shot]]. Screen the
whole banned-word class, not the single word that got rejected.

Also check messages, not only buttons: the Swipe tab's empty state said "Allow photo access to
start swiping". Apple did not flag it, but it is the same imperative pattern one screen away.
