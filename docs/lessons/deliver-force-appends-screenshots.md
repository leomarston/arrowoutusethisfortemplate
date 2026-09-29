---
name: deliver-force-appends-screenshots
description: fastlane deliver --force ADDS screenshots to existing sets instead of replacing them; dedupe on ASC by matching fileSize
metadata:
  type: reference
---

`deliver(force: true, screenshots_path: …)` **appends**. Re-delivering a redesigned set left every
App Store screenshot set holding 10 images — the five new frames plus the five from the previous
design — with identical file names and different bytes. Nothing errors, and the listing would have
shipped the old rejected design as the first five frames.

Check after every delivery, and dedupe by matching `fileSize` against the local file:

```python
for L in localizations:
  for st in appScreenshotSets(L):
    for s in appScreenshots(st):
      local = Path(f"fastlane/screenshots/{L.locale}/{s.fileName}")
      if local.stat().st_size != s.fileSize:
        DELETE /v1/appScreenshots/{s.id}
```

Then assert every set is exactly 5/5 with `assetDeliveryState.state == COMPLETE`
([[copyright-and-five-screenshots]]). 100 deletes ran clean in about a minute.

Same run, worth knowing: `deliver` did NOT touch the keywords field for any locale (there is no
`keywords.txt` on disk — [[keywords-are-user-owned]], [[template-scaffolds-empty-keywords-txt]]),
and it uploaded 200 screenshots across 10 locales inside one token without hitting the 20-minute
cap that bit [[asc-token-20min-cap]].

**2026-09-06, second run, worse:** `deliver` died partway through the screenshot upload with
repeated `SSL_read: unexpected eof while reading` and **never reached the binary upload**, so there
was no new build to submit — and the log ends with a lane-context dump that never says the binary
was skipped. The IPA was sitting in `build/` the whole time.

Recovery, and the right order every time:
1. Dedupe the screenshots via the API (fileSize match), and note any set left under 5 — a failed
   upload leaves a gap, not just a duplicate.
2. Re-upload any missing frame directly: POST `/v1/appScreenshots` with `{fileName, fileSize}` and
   the set relationship, PUT each returned `uploadOperation`, then PATCH `uploaded: true` with the
   file's md5 as `sourceFileChecksum`. Same reserve→upload→commit shape as
   `scripts/asc_review_assets.py`.
3. Run `fastlane upload_build` — it sets `skip_metadata` and `skip_screenshots`, so the binary goes
   up without touching anything already fixed.

**Always verify the build landed via the API before submitting.** `asc_submit.py` will happily
attach the previous build if the new one never arrived.
