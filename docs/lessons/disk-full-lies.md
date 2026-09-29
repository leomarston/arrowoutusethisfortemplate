---
name: disk-full-lies
description: A full disk on this Mac surfaces as codesign/gym errors that never mention space — check df first
metadata:
  type: reference
---

This Mac runs chronically near-full (228 GB volume, repeatedly under 1 GB free). When it
fills, the toolchain reports something else entirely:
- `codesign ... internal error in Code Signing subsystem` during `xcodebuild test`
- gym `Error packaging up the application`

Both happened in one session on 2026-08-25 and both were pure disk exhaustion.

**How to apply:** when a build/sign step fails oddly, run `df -h /` BEFORE debugging
signing. `rm -rf ~/Library/Developer/Xcode/DerivedData/*` reclaims ~10 GB and is safe
(pure build cache), but it refills within a few builds. Larger stores, NOT cleared
without asking: `~/Library/Developer/Xcode/Archives` (~5.5 GB, holds dSYMs for submitted
builds — deleting loses crash symbolication) and `~/Library/Developer/CoreSimulator/Devices`
(~31 GB, `xcrun simctl delete unavailable` trims old runtimes).
