---
name: test-delete-alert-wedges-suite
description: a unit test calling PHAssetChangeRequest.deleteAssets raises a springboard alert that blocks every UI test behind it — the run hangs with no failure
metadata:
  type: reference
---

`PHAssetChangeRequest.deleteAssets` **always** raises the system "Allow <App> to delete this photo?"
alert. A unit test has no way to answer it, so the alert sits on the springboard and blocks every
UI test scheduled after it in the same `xcodebuild test`. There is no failure and no message: the
run simply never finishes.

It is invisible until the unit target and the UI target run together. `scripts/bug_check.py` passes
because it runs `-only-testing:<App>UITests`; a bare `xcodebuild test` hangs.

Diagnosing it: screenshot the simulator while the run is stuck
(`xcrun simctl io <dev> screenshot`). A system alert over an unrelated screen is the tell — the
alert survives app relaunches, so the background belongs to whatever test is stuck behind it, not
to the test that raised it. A reboot clears it; `simctl` cannot tap it.

**So: never delete assets from a unit test.** If a test creates a fixture asset, leave it. Any
"clean up so the library is unchanged" step that goes through PhotoKit's change request is a trap.
The same applies to anything else that prompts — a `PHAssetCreationRequest` save prompts too when
the app only holds add-access.

Same family as the browser-dialog rule: a modal the harness cannot dismiss stops everything behind
it. See [[interactive-bug-check]] and [[simctl-photos-grant-is-a-lie]].
