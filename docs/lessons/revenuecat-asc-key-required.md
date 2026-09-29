---
name: revenuecat-asc-key-required
description: RevenueCat needs the ASC In-App Purchase Key + API key set per app or offerings are empty; rc_setup.py now automates it
metadata: 
  node_type: memory
  type: project
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

RevenueCat warns "Your app <X> is missing its In-App Purchase Key and/or bundle id … configure the App Bundle ID, P8 key file, Key ID and Issuer ID … for StoreKit 2." Without the **In-App Purchase Key**, RC can't validate purchases and offerings come back **empty** ("Could not load plans" on the paywall). Our existing ASC API key (`~/keys/AuthKey_B46H6FGV43.p8`, key id in `.env` `ASC_KEY_ID`, issuer `ASC_ISSUER_ID`, App Manager role) satisfies both credentials.

**Fix (automated in `scripts/rc_setup.py`, step 1b):** `POST https://api.revenuecat.com/v2/projects/{RC_PROJECT_ID}/apps/{app_id}` with body `{"app_store": { bundle_id, subscription_private_key=<p8 PEM>, subscription_key_id, subscription_key_issuer, app_store_connect_api_key=<same p8 PEM>, app_store_connect_api_key_id, app_store_connect_api_key_issuer }}`. Success = response `app_store.subscription_key_configured: true` and `app_store_connect_api_key_configured: true`. The .p8 is already PEM (`-----BEGIN PRIVATE KEY-----`); pass its raw text. Setting the ASC API key also auto-populates the vendor number.

Applied 2026-07-21 to Pomodoro (`appb184ee85f0`) and Reco (`appb4787edd1d`), both bundles `com.manycode.<slug>`. RC project `proj5f4f704a`. Every new factory app now gets this for free via rc_setup.py. Related: [[daily-routine]], [[reco-build-state]].
