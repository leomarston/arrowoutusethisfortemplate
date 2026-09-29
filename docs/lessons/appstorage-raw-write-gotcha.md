---
name: appstorage-raw-write-gotcha
description: "@AppStorage caches — a raw UserDefaults.standard.set for the same key is not seen, breaking -ForceOnboarding UI tests"
metadata: 
  node_type: memory
  type: reference
  originSessionId: af304055-c323-4932-95ec-dca1c6b99b7b
  modified: 2026-08-07T19:32:14.481Z
---

**Never reset an `@AppStorage`-backed flag with `UserDefaults.standard.set(...)`. Assign
through the wrapper instead.**

Diagnosed on `kitz`, 2026-08-07. `AppState` had:

```swift
@AppStorage("hasOnboarded") var hasOnboarded = false
init() {
    if ProcessInfo.processInfo.arguments.contains("-ForceOnboarding") {
        UserDefaults.standard.set(false, forKey: "hasOnboarded")   // ← does NOT take effect
    }
}
```

The wrapper caches its value, so the gate `!appState.hasOnboarded` in `RootView` still read
the OLD value: the app launched straight into the game and `testOnboardingReachesHome` failed
with "Onboarding question not shown" — deterministically, in both light and dark. Fix is one
line: `hasOnboarded = false` (write through the wrapper). Applied to kitz + `template/App/AppState.swift`.

**Compounding cause — simulator preferences survive `simctl uninstall`.** The sim's cfprefsd
keeps an app's UserDefaults cached, so a "fresh install" can start with `hasOnboarded = 1` from
earlier runs. Clear it with `xcrun simctl spawn <udid> defaults delete <bundleid>` before
onboarding tests. This is a strictly worse version of the known "SwiftData persists across
simctl install" trap.

**Release builds are unaffected** — those DEBUG-only resets don't exist, and a real user's first
install has genuinely empty prefs, so shipped onboarding works. This is a test-harness defect,
not a user-facing one. Worth remembering when triaging a red bug-check: **check whether the
failure predates your change** by re-running the same test against the original file (that is
what proved this one wasn't caused by the paywall edit).

Related: [[interactive-bug-check]], [[simctl-launch-args-gotcha]], [[no-free-trial-toggle]].
