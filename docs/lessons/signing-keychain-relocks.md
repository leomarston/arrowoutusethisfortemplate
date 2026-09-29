---
name: signing-keychain-relocks
description: errSecInternalComponent at gym EXPORT usually means the signing keychain re-locked; unlock inside the lane
metadata:
  type: reference
---

`errSecInternalComponent` during `fastlane` export is most often the dedicated
`manycode-signing` keychain having **re-locked** (lock-on-sleep, plus its own timeout) —
not a duplicate-certificate problem.

**Tell them apart:** `security show-keychain-info <keychain>` answering "User canceled
the operation" means it is locked. If instead `security find-identity -v -p codesigning`
shows two different SHA-1s under the same name, it is [[signing-keychain-shadowing]].

`scripts/signing_setup.py` unlocks it, but that can run an hour before the archive
finishes. Fix is to unlock immediately before signing — `apps/soundanalyzer/fastlane/Fastfile`
now has `unlock_signing_keychain` called at the top of `release` and `upload_build`.
**Backport to `template/fastlane/Fastfile`.**

Note gym reports this as "Error packaging up the application" and its own log ends with
`** ARCHIVE SUCCEEDED **` — the failure is in the EXPORT step, so grep the fastlane log
for `exportArchive`, not the gym log.
