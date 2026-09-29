---
name: deliver-cannot-upload-screenshots
description: fastlane deliver dies with SSL_read errors on every screenshot call; use scripts/asc_screenshots.py instead
metadata:
  type: reference
---

`fastlane deliver` **cannot upload App Store screenshots on this machine.** Every screenshot
call fails in Faraday/OpenSSL with:

    SSL_read: unexpected eof while reading

fastlane 2.236.1 on Ruby 4.0.5. It fails on the *read* (`get_app_screenshot_sets`), not the
upload, and `languages:` does NOT narrow the pass — deliver enumerates all 50 locales and
fails on each, then loops. The identical requests through the REST API return 200, so this is
fastlane, not Apple and not the network.

**Use `python3 scripts/asc_screenshots.py --slug <slug> --version <x.y.z>`** (optionally
`--locales en-US,ja`). It does reserve → upload → commit against `/v1/appScreenshots`, takes a
fresh JWT per locale (Apple caps it at 20 min, and 250 images outlive that —
[[asc-token-20min-cap]]), and deletes each set before writing so a re-upload cannot append
([[deliver-force-appends-screenshots]]).

**A newly opened version record has NO screenshot sets** — they are not inherited from the
previous version. Submitting without uploading them will fail.

Verify by API afterwards, never by assumption: count `appScreenshots` per
`appScreenshotSet` and assert exactly 5 in every locale.

Split lanes exist in camdetect's Fastfile and are worth copying: `upload_ipa` (uploads
`build/Spot.ipa` with no rebuild), `upload_text` (metadata, no images), `upload_shots_batch`.
A single `release` lane rebuilds the whole archive just to die on metadata.

**Screenshots cannot be replaced while a version is in review.** ASC returns
*"Can't Delete Screenshot After Submit for review appScreenshots"*. Cancel the review
submission first (`PATCH /v1/reviewSubmissions/{id}` with `canceled: true`), which moves the
version to `DEVELOPER_REJECTED` — that state IS editable, despite the alarming name — then
push and resubmit with `asc_submit.py`.

Apple also drops the connection mid-push (`RemoteDisconnected`, no status code to branch on),
so the script retries transport errors and takes `--only-incomplete` to resume a part-finished
run instead of re-uploading all 250 images.
