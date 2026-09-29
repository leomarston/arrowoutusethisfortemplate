---
name: build-lag-never-bump
description: /v1/builds lags after upload — an empty list is not a failed upload; never bump on cfBundleVersion-already-used
metadata:
  type: project
---

After `fastlane release`/`upload_build` succeeds, **`GET /v1/builds` can still return an empty
list for minutes**. That is API lag, not a failed upload.

Misread on `hearingtest` 2026-08-21: the empty list looked like "the binary never uploaded", so
a second upload was attempted and failed with

```
409 ENTITY_ERROR.ATTRIBUTE.INVALID.DUPLICATE
The bundle version must be higher than the previously uploaded version: '1'
```

**That error is PROOF the first upload succeeded.** The correct response is to WAIT for
processing — never to bump `CURRENT_PROJECT_VERSION`, which would abandon a perfectly good
binary and desync the build numbers.

**How to apply:** after any upload, poll `/v1/builds?filter[app]=...&sort=-uploadedDate` until a
build reaches `processingState == VALID` (usually 5–15 min). Only treat it as failed if the
fastlane log itself shows an error, or a build goes `FAILED`/`INVALID`.

Related: [[signing-submit-gotchas]], [[new-app-needs-keywords]]
