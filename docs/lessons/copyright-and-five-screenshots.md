---
name: copyright-and-five-screenshots
description: "App Store copyright must be '2026 Manycode Apps'; every app has EXACTLY 5 screenshots (dedup any duplicates)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

Two hard requirements the user was angry about (2026-07-22, on wifispeed):

**Copyright = "2026 Manycode Apps"** — NOT the default account name ("2026 Emine Saridogan"). `create_app` sets the account name by default. Fix: every app's `fastlane/metadata/copyright.txt` = `2026 Manycode Apps` (added to `template/`), and/or PATCH `/v1/appStoreVersions/{id}` `attributes.copyright`. Applied to wifispeed + pomodoro. (Year is hardcoded 2026 — bump annually.)

**EXACTLY 5 screenshots** — never more. `deliver` can leave duplicates (9 instead of 5) when a screenshot upload hits ASC 500s / is interrupted and then re-run — it re-uploads the same fileName without deleting the old one. `asc_submit.py` now auto-dedups (deletes duplicate fileNames, keeping one each) right after cancelling open submissions, before submitting. If the version is already WAITING_FOR_REVIEW, screenshots are locked — cancel the review submission first (version → DEVELOPER_REJECTED, editable), delete dupes, then re-submit. **Watch:** cancelling orphans the subs/group version into DEVELOPER_REJECTED — `asc_submit.py`'s state filter now includes DEVELOPER_REJECTED so they re-bundle with the version ([[asc-subscription-submission]]). Related: [[app-naming-keyword-first]].
