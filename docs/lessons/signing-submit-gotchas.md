---
name: signing-submit-gotchas
description: "Faz 11 submit pitfalls — codesign keychain partition-list, build auto-attach, stale-submission item deletion, sub review screenshot"
metadata: 
  node_type: memory
  type: project
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
  modified: 2026-08-07T19:31:58.134Z
---

Faz 11 (`fastlane release` + `asc_submit.py`) pitfalls hit + fixed while shipping partylights (2026-07-26). All fixes are now baked into the factory scripts, but know the symptoms:

- **`errSecInternalComponent` during `fastlane release` export** = codesign can't access the Distribution private key non-interactively. Fix: `security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k <pass> <keychain>` on the signing keychain. `signing_setup.py` now does this via `ensure_keychain_access()` using a dedicated `~/Library/Keychains/manycode-signing.keychain-db` (password = `keys/signing/keychain.pass`). Re-run `signing_setup.py` if it recurs.
- **"version'a build ekli degil"** after `fastlane release`: `deliver` uploads the binary but never LINKS it to the appStoreVersion, and Apple needs ~5-15 min to process it to `processingState: VALID` first. `asc_submit.py` now auto-attaches the newest VALID build (PATCH `/appStoreVersions/{vid}/relationships/build`).
- **A RESUBMIT can silently ship the OLD binary (2026-08-07, burned 9 apps at once).**
  `asc_submit.py` used to attach the build **before** cancelling the open submission. A
  version in `WAITING_FOR_REVIEW` is LOCKED, so `PATCH /appStoreVersions/{vid}/relationships/build`
  is refused — and because the response status was never checked, it printed
  "+ build … eklendi" while the version kept the PREVIOUS build. Every app went back into
  review with the unfixed binary and *looked* successful. It only worked on the first app
  tried (bracketmaker) because that version was already `REJECTED`, hence editable — so a
  single-app test does NOT prove this path. **Fixed:** attach now happens AFTER the cancel
  propagates (WAITING_FOR_REVIEW → CANCELING → DEVELOPER_REJECTED, a few min), retries the
  PATCH ~5 min, **reads the relationship back to verify**, and hard-exits instead of
  submitting the wrong build. **Always verify the attached build NUMBER via
  `GET /v1/appStoreVersions/{vid}/build` after any resubmit — never trust the script's log line.**
- **A build-number bump can miss the binary when the app has a literal `Info.plist`.**
  With `GENERATE_INFOPLIST_FILE: NO` + an xcodegen `info:` block (rfdetector needs one for
  `NSBonjourServices`), the plist's literal `CFBundleVersion` WINS over the
  `CURRENT_PROJECT_VERSION` build setting, so uploads die with "bundle version must be higher
  than the previously uploaded version". Fix: put `CFBundleVersion: "$(CURRENT_PROJECT_VERSION)"`
  and `CFBundleShortVersionString: "$(MARKETING_VERSION)"` in the info properties — and keep
  MARKETING_VERSION equal to the ASC appStoreVersion string (rfdetector is `1.0`, not `1.0.0`)
  or the build won't attach to that version.
- **"already been used / must be higher than N" on an upload retry usually means the FIRST
  upload SUCCEEDED** and Apple just hasn't surfaced the build yet. Don't bump the version —
  poll `/v1/builds` until it appears and goes VALID.
- **Stale submissions lock the version** (`ITEM_PART_OF_ANOTHER_SUBMISSION`): a `READY_FOR_REVIEW` (built-but-not-submitted) reviewSubmission CANNOT be `canceled:true` (409 "not in cancellable state") and keeps the appStoreVersion. Fix: DELETE its `reviewSubmissionItems` to free the version. `asc_submit.py` now deletes items for READY_FOR_REVIEW and only PATCH-cancels WAITING_FOR_REVIEW ones.
- **Subscriptions stuck MISSING_METADATA** → `subscriptionVersions ... not in valid state` at submit. Cause: missing subscription **review screenshot** (localization alone isn't enough). Fix: `python3 scripts/asc_review_assets.py --slug <slug> --image apps/<slug>/shots/raw/paywall.png` (use the `-DemoPaywall` capture).
- **`fastlane create_app` needs NO Apple session** — it works via the ASC API key ("Available session is not valid anymore. Continuing with normal login." then succeeds). The [[reco-build-state]] note about being blocked on session auth is outdated for create_app.
- **asc_iap.py transient crashes** (`RemoteDisconnected`) mid per-territory loop: now retried in `_send()`.

Related: [[app-factory-setup-state]], [[asc-subscription-submission]], [[reco-build-state]].
