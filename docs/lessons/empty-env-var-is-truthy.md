---
name: empty-env-var-is-truthy
description: SKIP_PRIVACY= (empty) still skips in Ruby; a new app then cannot be submitted
metadata:
  type: project
---

In the Fastfile the privacy step is guarded by `unless ENV["SKIP_PRIVACY"]`. **An empty string
is truthy in Ruby**, so `SKIP_PRIVACY= fastlane release` SKIPS the privacy upload just as
surely as `SKIP_PRIVACY=1`.

Hit on `hearup` 2026-08-21: submission failed with
`STATE_ERROR.APP_DATA_USAGES_REQUIRED — "You must have published answers to your app's data
usages"`, surfaced by `asc_submit.py` only as `!! appStoreVersion item eklenemedi`.

**How to apply:** for a FIRST submission never pass `SKIP_PRIVACY` at all (not even empty).
If the app data usages were missed, run the `privacy_only` lane (added to hearup's Fastfile;
copy it when needed) rather than re-running the whole release. Data usages are not in the
public ASC API, so this needs the Apple ID session.

Related: [[app-privacy-needs-apple-id]], [[new-app-needs-keywords]]
