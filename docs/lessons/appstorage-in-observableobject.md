---
name: appstorage-in-observableobject
description: @AppStorage inside an ObservableObject never emits objectWillChange — the app can stick on onboarding
metadata:
  type: project
---

`AppState` had `@AppStorage("hasOnboarded") var hasOnboarded`. **Inside an
`ObservableObject`, `@AppStorage` writes UserDefaults but does NOT emit
`objectWillChange`.** `RootView` gates onboarding vs. home on that value, and the onboarding
paywall's `onDismiss` sets it — so after tapping the paywall X, RootView had no reason to
re-render and **the app could stay stuck on the onboarding screen**.

It only "worked" when some unrelated SwiftUI invalidation happened to redraw RootView, which is
why bug_check failed it ~50/50 across light/dark runs. A reviewer hitting the bad half sees a
dead end on first launch — a certain rejection.

**The fix** (now in `template/` and every app): a computed property.
```swift
var hasOnboarded: Bool {
    get { UserDefaults.standard.bool(forKey: "hasOnboarded") }
    set { objectWillChange.send(); UserDefaults.standard.set(newValue, forKey: "hasOnboarded") }
}
```
This also removes the older [[appstorage-raw-write-gotcha]] hazard, because `-ForceOnboarding`'s
raw `UserDefaults.set` is now read back correctly instead of being shadowed by a cached wrapper.

**How to apply:** never use `@AppStorage` for state an `ObservableObject` publishes to a view
that switches on it. An intermittent UI test is a signal to look for a missing publish, not a
reason to add a retry.

Related: [[appstorage-raw-write-gotcha]], [[interactive-bug-check]]
