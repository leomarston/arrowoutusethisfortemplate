---
name: swiftui-navigation-and-funnel-traps
description: "Three defect classes found building Couch — a dropped NavigationStack push, a paywall trigger wedged by a stale screen enum, and order-dependent UI tests"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 195160ba-b6c0-4fae-8afc-86456f932056
  modified: 2026-09-05T23:44:26.202Z
---

Found on `tvremote` (Couch) 2026-09-06, all three invisible to a build and to screenshots:

**1. An imperative `path.append` into a `NavigationStack` can be silently dropped.** The Settings
gear was a `Button { path.append(.settings) }` in a toolbar. When anything re-rendered the stack's
root in the same runloop turn (a saved TV finishing its reconnect, an `ObservableObject`
publishing), the append vanished — tapping Settings did nothing and the person stayed put. Use
`NavigationLink(value:)` for a push that must not be lost; keep imperative appends for cases where
you control the timing. Symptom in XCUITest: the first tap does nothing, a second tap works.

**2. A paywall gated on a screen enum dies when a handover forgets to release it.**
`PaywallTrigger` only presents while `session.screen == .remote`. The connect flow set
`.connect` and handed over to the remote trusting the remote's `onAppear` to reclaim it — it did
not always win the race, so the screen stayed `.connect` and **the app's only monetisation event
never fired**, no matter how many commands succeeded. Nothing else failed: the build was clean,
every driver test green, the UI looked right. Two lessons: a handover must set the new state
explicitly rather than trust the arriving view, and a funnel state machine needs a debug trace
(`-DebugFunnel` NSLogging every evaluation) because it is otherwise unobservable. That trace is
what found it, in one line: `tick scenePhase active screen connect`.

**3. UI tests that inherit simulator state are order-dependent and lie both ways.** Tests passed
alone and in pairs, failed in the full suite, and the failure moved between tests run to run —
because each test inherited the previous one's saved TV, pairing record and funnel history, and a
TV reconnecting mid-launch raced every toolbar tap. Fix: a DEBUG `-ResetState` launch arg that
wipes saved devices, Keychain pairing, funnel state and one-time flags at startup, used by every
UI test. Do this before chasing a "flaky" harness. Related: [[xcuitest-hittable-lies]] — dump
`app.debugDescription` at the failure instant instead of guessing.
