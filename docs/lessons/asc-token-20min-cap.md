---
name: asc-token-20min-cap
description: "fastlane deliver can't finish a 50-locale screenshot upload — Apple caps the API token at 20 min; PATCH whatsNew directly when only notes changed"
metadata:
  type: reference
---

Apple caps an App Store Connect API JWT at **20 minutes**. A `deliver` run that re-uploads
screenshots for 50 locales (250 images) takes longer than that, so the token dies mid-run and the
log loops forever on:

    Waiting for screenshots to appear before uploading. This is unlikely to be recovered unless
    it's 503 error. error="Authentication credentials are missing or invalid. - ... make sure
    that it has not expired."

It never recovers and never exits cleanly. `overwrite_screenshots: true` makes it worse — it
deletes and re-pushes images that did not change.

**How to apply:**
- **Only the release notes changed?** Skip fastlane entirely. PATCH `whatsNew` onto each
  `appStoreVersionLocalization` (GET `/v1/appStoreVersions/<id>/appStoreVersionLocalizations`,
  then PATCH each). 50 locales in about 30 seconds. Used for camdetect 1.0.1 on 2026-09-02.
- **Only text changed but you still want deliver?** Add `skip_screenshots: true` to the lane.
- Screenshots only need re-uploading when the images actually changed.

Two neighbours from the same run: fastlane dies with `getaddrinfo(3): nodename nor servname
provided` on a DNS blip (purely transient — retry), and the ASC API returns 429
`RATE_LIMIT_EXCEEDED` if you poll app states in a tight loop, which surfaces as *empty* results
rather than an error if you do not check the status code. Related: [[altool-checksum-wedge]].
