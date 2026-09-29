---
name: resubmit-update-checklist
description: shipping an UPDATE differs from a first release — new version record, re-run signing_setup, and the builds API is not date-ordered
metadata:
  type: reference
---

Shipping an **update** to an app that is already `READY_FOR_SALE` (first done 2026-09-03 for
twocam / procam / camdetect / hearup):

1. **Open a new version record first.** `asc_submit.py` always takes the LATEST iOS version
   and never creates one — correct for a first release, useless for an update, where the
   live version cannot be edited. Use `scripts/asc_new_version.py --slug X --version Y
   --notes "..."` (written for this). It also writes `release_notes.txt` to EVERY locale;
   an update with an empty What's New is rejected, and the field is per-locale.
2. **Re-run `scripts/signing_setup.py --slug X`.** Both twocam and procam failed
   `fastlane release` with the useless message **"Error packaging up the application"** and
   nothing else in the log. The cause was a stale locally-installed provisioning profile.
   Re-running signing_setup fixed both immediately. Suspect this FIRST for that error —
   after checking disk ([[disk-full-lies]]).
3. Bump `MARKETING_VERSION` **and** `CURRENT_PROJECT_VERSION` in `project.yml`, then
   `xcodegen generate`.
4. `SKIP_PRIVACY=1 fastlane release` — privacy details are set once per app and the action
   needs an interactive Apple ID password.
5. **`GET /v1/apps/{id}/builds` is NOT date-ordered.** A `limit=3` poll for a freshly
   uploaded build reported "not visible yet" for 20 minutes while the build sat at index 3,
   already VALID. Fetch `limit=10+` and match on `version`, or you will wait on nothing.
6. `python3 scripts/asc_submit.py --slug X`. A 500 UNEXPECTED_ERROR right after upload
   usually means the build is still processing — wait and retry.

Related: [[build-lag-never-bump]], [[signing-submit-gotchas]], [[asc-version-platform-filter]]
