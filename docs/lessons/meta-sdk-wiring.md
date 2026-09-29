---
name: meta-sdk-wiring
description: how to actually link the Meta SDK — the tracking-domain trap that kills it for 80% of users, the copy it makes false, and the ASC label that needs a human
metadata:
  type: reference
---

`scripts/meta_sdk.py --slug <slug> --app-id <id> --client-token <tok>` does the wiring. Getting the
credentials: developers.facebook.com → Create App → use case **"Create & manage app ads with Meta
Ads Manager"** → App ID is in the dashboard URL, Client Token is Settings ▸ Advanced ▸ Security.
Then Settings ▸ Basic ▸ Add Platform ▸ iOS for the bundle id.

**The server can override the app's auto-log switch** (FBSDK 18.1.1 Settings+AutoLogAppEvents.swift: a server
`auto_log_app_events_enabled` beats the plist/code value), and implicit purchase logging is bit 1 of the server's
`app_events_feature_bitmask` — so check Meta's side, not the plist: `GET graph.facebook.com/v26.0/<app id>?fields=
app_events_feature_bitmask,aam_rules,auto_log_app_events_enabled` needs NO token (the SDK itself sends none).
apps/mazeout/tools/meta_dashboard_check.py gates it and also proves the .env token is the CLIENT token, not the App
Secret: `<app id>|<token>` must answer 200 on /<app id>?fields=id but 104 on /<app id>/subscriptions (an app secret
would be an app access token and get data there).

**Two things on that page matter.** Turn OFF *"Log in-app events automatically"* — with it on, Meta
logs purchases/trials from its own App Store feed and double-counts everything `logSubscription`
and `logTrialStarted` already send. And the **iPhone Store ID cannot be saved until the app has
been publicly live for 24 hours**, so that field is a post-approval step, not a blocker.

**Two traps around NSPrivacyTrackingDomains — they pull in OPPOSITE directions.**

1. The key must NOT be empty. `NSPrivacyTracking=true` with an EMPTY domains array is
   **ITMS-91064 "invalid tracking information"**: the build is failed as INVALID_BINARY with no
   readable reason anywhere in the ASC API. This cost storagecleaner three builds on 2026-09-09.
2. It must NOT list `graph.facebook.com` or `www.facebook.com`. `NSPrivacyTrackingDomains` is
   ENFORCED, not descriptive: iOS BLOCKS any connection to a listed domain when ATT is not
   granted, and those two carry the SDK's non-tracking traffic too — listing them kills the SDK
   for the ~75-80% who decline.

The resolution is to name exactly `ep1.facebook.com`, which is what FBSDKCoreKit declares in its
own bundled manifest. Naming it changes no runtime behaviour (it is already ATT-blocked either
way) and it satisfies Apple's validator. Fixed in `scripts/meta_sdk.py`, commit 9713636.

**Verify the SDK is actually linked, because the failure is silent.** Every method in MetaAds.swift
sits inside `#if canImport(FacebookCore)`, so a missing package compiles the whole file to no-ops
that build and ship. It was dead for four builds. In a Debug build the code is in
`FreeUp.debug.dylib`, NOT the thin main binary — `otool -L` on the app binary finds nothing and
looks like failure:

    otool -L <App>.app/<App>.debug.dylib | grep -i fbsdk     # frameworks bound
    strings -a <App>.app/<App>.debug.dylib | grep -c activateApp   # real bodies compiled

`MetaSDKLinkageTests` now asserts all of this plus the Info.plist keys, so it cannot rot again.

**What linking it breaks, and the script now reports honestly:**
- Every "no analytics / no tracking / nothing is uploaded" claim, in EVERY locale — the old audit
  matched English substrings and said "1 locale" when ten were false. Scope blanket negatives to
  the photo library ("no photo is uploaded") and replace exclusivity claims with a closed list.
- The shared privacy policy at manycode-legal says "no advertising SDKs". It serves ~20 apps, so it
  cannot be edited in place — `privacy-ads.html` is the advertised-app version, and Config.privacyURL
  plus every locale's privacy_url.txt point there.
- ATT needs `NSUserTrackingUsageDescription` or iOS answers `.denied` with no prompt at all.
  Onboarding awaits the prompt before the paywall, so **every onboarding UI test must dismiss the
  springboard alert** or it hangs — see [[permission-prompt-is-one-shot]].

**The App Store privacy label is NOT in the public ASC API** — verified, `/v1/appDataUsages` 404s.
It needs `upload_app_privacy_details_to_app_store` with a live Apple ID web session (spaceauth,
~30 days) or a human in ASC. See [[app-privacy-needs-apple-id]] and [[apple-session-30-days]].

Use `fastlane upload_meta` for a metadata-only change: it sets `overwrite_screenshots: true`, which
deletes and re-uploads rather than appending — the problem in [[deliver-force-appends-screenshots]].
