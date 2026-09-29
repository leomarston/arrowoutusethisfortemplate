---
name: altool-checksum-wedge
description: "altool can loop forever on \"Checksums do not match\" for one asset part; kill it and re-run the upload on the same IPA instead of waiting"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-08-30T20:32:53.147Z
---

During `fastlane release`, altool can get stuck retrying a single upload part with
`ERROR: ... WILL RETRY PART 1. Checksums do not match.` It never gives up — noisemeter sat there for
30 minutes and 40 retries on the app-analyzer asset while the IPA itself was fine.

**Why:** transient Apple CDN corruption on one part, not a problem with the archive.

**How to apply:** the give-away is `~/Library/Logs/ContentDelivery/com.apple.itunes.altool/*_Upload_*.txt`
showing repeated "Checksums do not match" for the same part, with `/v1/builds` still empty. Don't wait it
out and don't re-archive. `pkill -f "fastlane release"; pkill -f altool`, then re-upload the IPA that gym
already produced:

    xcrun altool --upload-app -t ios -f build/<App>.ipa --apiKey $ASC_KEY_ID --apiIssuer $ASC_ISSUER_ID

That took 10 seconds on the retry. Then run `fastlane upload_meta` for the metadata/screenshots that the
killed `release` lane never reached. Related: [[build-lag-never-bump]] — after a successful upload
`/v1/builds` is still empty for a few minutes, which is normal and not a failed upload.
