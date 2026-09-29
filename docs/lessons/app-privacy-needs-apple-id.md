---
name: app-privacy-needs-apple-id
description: "App Privacy data usages are NOT in the public ASC API; a new app can't pass review submission without publishing them via an Apple ID session"
metadata: 
  node_type: memory
  type: project
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

Every NEW app must have App Privacy ("what data your app collects") **published** before
`asc_submit.py` can attach the appStoreVersion item. Without it the item POST returns
409 `STATE_ERROR.ENTITY_STATE_INVALID` with associated error
`APP_DATA_USAGES_REQUIRED` on `/v1/appDataUsages/`.

**Why:** `/v1/appDataUsages`, `/v1/appDataUsageCategories`, `/v1/appDataUsagePurposes`
and `/v1/apps/{id}/appDataUsagesPublishState` all return **404** — Apple never shipped
these in the public App Store Connect API. Only the Apple-ID-authenticated (spaceship /
Tunes) API can write them, which is why the factory Fastfile uses
`upload_app_privacy_details_to_app_store` with `APPLE_ID` rather than the ASC API key.

**How to apply:** `SKIP_PRIVACY=1 fastlane release` skips that step — fine on re-releases
of an existing app, but it silently leaves a brand-new app unsubmittable. For a new app
either drop `SKIP_PRIVACY`, or run it standalone afterwards:

```
cd apps/<slug>
fastlane run upload_app_privacy_details_to_app_store \
  app_identifier:com.manycode.<slug> username:$APPLE_ID \
  json_path:./fastlane/metadata/app_privacy_details.json skip_publish:false
```

It reuses `~/.fastlane/spaceship/<apple-id>/cookie`, so it runs non-interactively while
that session is alive; otherwise it needs 2FA (`fastlane spaceauth`). Confirmed on twocam
2026-08-03. See [[signing-submit-gotchas]] and [[daily-routine]].

**2026-08-31 (watereject):** hit again by a different route — the privacy step lives INSIDE the
`release` lane, so running `upload_meta` + `upload_build` separately (to dodge an upload failure)
skips it just as silently as `SKIP_PRIVACY=1` does. The template Fastfile now has a standalone
`upload_privacy` lane for exactly this: **whenever you split `release`, run `fastlane upload_privacy`
too.** It takes six seconds and the failure otherwise only appears at the very last step.
