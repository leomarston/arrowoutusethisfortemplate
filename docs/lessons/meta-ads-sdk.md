---
name: meta-ads-sdk
description: Meta install-attribution SDK is built and opt-in per app (scripts/meta_sdk.py); blocked on a Meta App ID + Client Token and a Page linked to the ad account
metadata:
  type: project
---

**The user asked for this directly on 2026-09-05** — *"All i am looking for is to implement
the meta ads sdk that we will use in our campaigns, properly to our apps so we can actually
launch campaigns."* It overrides the CLAUDE.md no-analytics default for apps he chooses to
advertise. Do not re-litigate it; do keep it opt-in.

**Ad account:** `1026654543083432` "Mutlu Taner", ACTIVE, MCP-enabled, payment method on file,
currency TRY, minimum 48.23 ₺/day per ad set. One unrelated campaign already runs there
("PinGrow — Prospecting CBO"), and the identity is NOT the esaridogann@gmail.com account the
Apple/RC rule pins — flagged to the user, his call.

**Built and verified (commit on build/procam):**
- `template/App/Support/MetaAds.swift` — inert unless `Config.metaAppID` is real. Tracking off
  before SDK init; only enabled after ATT `.authorized`. ATT prompt at the END of onboarding
  (earlier is an Apple rejection). Logs purchase + trial + paywall-view, price and currency
  from the StoreKit product.
- `scripts/meta_sdk.py --slug X --app-id … --client-token …` — adds the SPM package, writes
  every plist key **through xcodegen's `info:` block** (array keys have no `INFOPLIST_KEY_`
  form — see [[infoplist-array-keys-need-a-base-plist]]; here it would mean installs are never
  attributed, silently), rewrites `PrivacyInfo.xcprivacy` + `app_privacy_details.json` to
  declare tracking, and prints every store sentence that becomes false, per locale.

**TWO BLOCKERS, both need the user:**
1. **Meta App ID + Client Token** — only from developers.facebook.com > App Dashboard. The Ads
   MCP cannot create or read apps (`ads_get_datasets` returns empty), and the browser is
   off-limits ([[account-and-no-browser]]). Without these nothing can be wired.
2. **No Facebook Page is linked to the ad account** (`ads_get_ad_account_pages` → `[]`). Every
   ad creative needs a `page_id`, so a campaign and ad set can be created but not an ad.

**The cost, which the user must accept per app:** privacy label gains DEVICE_ID +
PRODUCT_INTERACTION marked "used to track you"; an ATT prompt appears; and every description
sentence promising "no tracking / no analytics / nothing uploaded / works offline" becomes
false in up to 50 locales and must be rewritten before submit (2.3.1, and it would be a lie).

Related: [[no-network-claim-is-false]], [[app-privacy-needs-apple-id]]
