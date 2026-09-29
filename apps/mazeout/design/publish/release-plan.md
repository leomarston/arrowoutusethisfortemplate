# Arrow Out — RELEASE PLAN (PUBLISH items 9, 10, 11-text)

Author: release planner, 2026-09-28 00:05–00:40 +03. This phase only investigates and plans: no App/Packages/Tests/UITests edits, no
simulator, no xcodebuild, no phone, no git commit. Only read-only calls were made to App Store Connect and RevenueCat, plus curl to
Apple's public search endpoints.

How claims are tagged:
- **VERIFIED**: seen in a file, a live API response, Apple's OpenAPI spec (v4.5, downloaded 2026-09-28) or a live web page.
- **INFERRED**: reasoned from evidence. The plan says how each one gets confirmed.
- **DECISION**: our recommendation. Anything that needs the owner is listed in §10.

Owner's words (PLAN.md "OWNER 2026-09-28 (PUBLISH)", verbatim):
- 9: "also we shoudl remove the watch video and get money or etc thing, we wont have admob connected so we can not do that"
- 10: "… all can be done without me touching anything. So make sure you properly upload and ready for review and properly set everything
  and make sure you connect revenuecat properly, localize perfectly for the 10 langueages we always localize to, also localize the
  moneys, I mean if that possible, to make them dynamic … worst case scenerio you can write the prices in dollars … BUT THIS IS ONLY THE
  WORST CASE SCENERIO."
- 11 (text part): "Never mention mazeout in our description or keywords ever."

---

## 0. TL;DR

1. **The IAP list stays as it is: 12 consumables.** Items: 1 Special Offer, 5 bundles, 6 coin packs, all `com.manycode.arrowout.*`.
   The US prices run $0.99–$99.99.
   - I read Apple's own price equalisation for those 12 US price points. In Turkey it gives exactly v552's TL list (49,99 … 4.999,99)
     (**VERIFIED**, §2.1). The original uses Apple's automatic prices, and we can too.
   - Nobody ever changes a price by hand: StoreKit's `displayPrice` shows every user their own currency. The owner's "worst case" of
     dollar prices is not needed.
2. **The factory scripts cannot create consumables today.**
   - `asc_iap.py` and `rc_setup.py` only create subscriptions.
   - Every script except the screenshot and keyword tools derives the bundle id as `com.manycode.<slug>`. That gives
     `com.manycode.mazeout`, which is wrong for us.
   - Needed: one new ASC consumables script, one new RevenueCat consumables script, a `--bundle` flag on `asc_submit.py` and
     `signing_setup.py`, and IAP review items in `asc_submit.py`. Apple's spec now has `reviewSubmissionItems.inAppPurchaseVersion`
     (**VERIFIED**), so the first IAPs can ship in the same submission as version 1.0.0.
3. **Release builds sell nothing today.** A Release build always uses the FakeStore (`StoreService.swift`: "a Release build never even
   asks StoreKit"). It grants coins for free and shows "Test store: nothing is charged". This is a P0 code change before submit (§2.5).
4. **Item 9 covers one ad offer:** the green "[clapper] [heart +1] Live" button on the More Lives popup, routed to `AdSlot` ("Video not
   available"). §4 lists all 13 places it touches and how to remove it cleanly.
5. **Locales: 13, not 10.** Ruling 37 and memory `localize-top-13-locales` supersede the owner's "10". That means 207 string keys ×
   12 new languages. The display font has no Japanese, Korean or Chinese glyphs (**VERIFIED**), so those three need a font plan (§5).
6. **ASO.** "Arrow Out" is a crowded name: at least 15 live apps carry "Arrow Out" in the title, and "Arrow Escape: Arrow Out" is taken
   (**VERIFIED**). Recommended: seed **"arrow out"** and name **"Arrow Out: Arrow Escape Puzzle"** (30 characters). Keywords must never
   contain "maze": Apple would combine it with the "Out" in our name and rank us for "maze out" (§6).
7. **The owner must act at least twice** (§8, §10). Everything else is scripted.
   - The Apple web session **expired on 2026-09-20** (cookie dates, **VERIFIED**). App creation and the App Privacy upload need
     `fastlane spaceauth` with 2FA.
   - The account has **0 sandbox testers** (**VERIFIED**). An on-device purchase test needs one, or a TestFlight internal tester.

---

## 1. Current state (checked 2026-09-28 00:08–00:35, secrets not printed)

| What | State | Tag |
|---|---|---|
| `.env` | APPLE_ID, TEAM_ID GDU77F3MXL, ASC_KEY_ID B46H6FGV43, ASC_ISSUER_ID, ASC_KEY_PATH (file exists), BUNDLE_PREFIX com.manycode, DEV_NAME, PRIVACY_URL, SUPPORT_URL, REVIEW_FIRST/LAST/PHONE/EMAIL, RC_PROJECT_ID proj5f4f704a, RC_SECRET_KEY, GEMINI_API_KEY: all set. ITC_TEAM_ID empty (unused). There is **no** FASTLANE_SESSION line. | VERIFIED |
| ASC API key | Works (HTTP 200; 39 apps on the account). | VERIFIED |
| ASC app record for `com.manycode.arrowout` | **None.** No bundle-id record either. `com.manycode.mazeout` has none as well. | VERIFIED |
| RevenueCat secret key | Works (HTTP 200). The shared project has 40 apps, none for Arrow Out. Every existing product is type `subscription`. | VERIFIED |
| Apple web session (`~/.fastlane/spaceship/esaridogann@gmail.com/cookie`) | `DES…` trust cookie created 2026-08-21 00:02 +03 with max_age 30 d, so it **expired on 2026-09-20**. `myacinfo` was refreshed on 2026-09-14. The fastlane keychain password entry is present. | VERIFIED (dates); INFERRED: the next Apple-ID login asks for 2FA |
| Apple ID–only features | There is no `POST /v1/apps` and no app-privacy (`appDataUsages`) endpoint in the public API spec v4.5. | VERIFIED |
| Signing material | `keys/signing/dist.{cer,key,id,csr}` and `keychain.pass` exist. Both `manycode-signing` and `manycode-build` keychains exist. `manycode-build` is the known shadowing trap; `signing_setup.py` rewrites the search list. | VERIFIED |
| Sandbox testers | **0** (`GET /v2/sandboxTesters`). | VERIFIED |
| Legal pages | privacy/support/terms return HTTP 200. The support page lists esaridogann@gmail.com; the in-app Support button uses anycodeapps@gmail.com. | VERIFIED |
| `apps/mazeout/fastlane/` | **Does not exist.** | VERIFIED |
| project.yml | MARKETING_VERSION 0.1.0, build 1, `TARGETED_DEVICE_FAMILY "1"`, `ITSAppUsesNonExemptEncryption NO`, **no RevenueCat package**. | VERIFIED |
| Privacy manifest | **No `PrivacyInfo.xcprivacy`** in App/. The app uses UserDefaults and `ProcessInfo.systemUptime`, both "required reason" APIs. | VERIFIED |
| App icon | `icon-1024.png` is a 4.5 KB placeholder with no alpha. Owner item 11 replaces it. | VERIFIED |
| ideas.yaml | No `mazeout` or `arrowout` entry, so every script that calls `idea.py` fails for this app. | VERIFIED |

---

## 2. In-app purchases: products, App Store Connect, RevenueCat (owner item 10)

### 2.1 The product list (12 consumables; the catalogue source is `PathCore/Economy/ShopCatalog.swift` + `rules.json:shop`)

Product id = `com.manycode.arrowout.` + catalogue id (**VERIFIED**: `ShopCatalog.productPrefix` and `ArrowOut.storekit`). "N of each" means
N Time Freeze + N Hint.

| # | Catalogue id | Grants (VERIFIED `defaultProducts`) | Badge | US price | US-price source | TRY equalised by Apple | = v552 TL? | DEU / JPN |
|---|---|---|---|---|---|---|---|---|
| 1 | offer.special | 1,000 coins, 1 of each, 1h ∞ lives; **once per install** | "90% OFF" | $0.99 | VERIFIED US IAP list | 49.99 | yes 49,99 | €0.99 / ¥150 |
| 2 | bundle.mini | 2,000 coins, 1 of each, 3h ∞ | — | $4.99 | VERIFIED | 249.99 | yes | €5.99 / ¥800 |
| 3 | bundle.epic | 4,000 coins, 3 of each, 6h ∞ | — | $9.99 | VERIFIED | 499.99 | yes | €9.99 / ¥1500 |
| 4 | bundle.elite | 8,000 coins, 8 of each, 12h ∞ | "Popular" | $19.99 | VERIFIED | 999.99 | yes | €22.99 / ¥3000 |
| 5 | bundle.mega | 20,000 coins, 18 of each, 36h ∞ | — | $49.99 | INFERRED* | 2499.99 | yes 2.499,99 | €59.99 / ¥8000 |
| 6 | bundle.legendary | 60,000 coins, 36 of each, 72h ∞ | "Best Value" | $99.99 | INFERRED* | 4999.99 | yes 4.999,99 | €99.99 / ¥15000 |
| 7 | coins.1000 | 1,000 coins | — | $1.99 | VERIFIED | 99.99 | yes | €1.99 / ¥300 |
| 8 | coins.5000 | 5,000 coins | — | $7.99 | VERIFIED | 399.99 | yes | €8.99 / ¥1300 |
| 9 | coins.10000 | 10,000 coins | — | $14.99 | VERIFIED | 799.99 | yes | €17.99 / ¥2500 |
| 10 | coins.25000 | 25,000 coins | — | $29.99 | VERIFIED | 1499.99 | yes | €34.99 / ¥5000 |
| 11 | coins.50000 | 50,000 coins | — | $54.99 | VERIFIED | 2999.99 | yes | €59.99 / ¥9000 |
| 12 | coins.100000 | 100,000 coins | — | $99.99 | VERIFIED | 4999.99 | yes | €99.99 / ¥15000 |

- **Price points exist.** All 11 distinct US prices exist as USA price points (read from `appPricePoints` on an existing app). Each
  one's `/v3/appPricePoints/{id}/equalizations` gives the TRY/EUR/JPY above (**VERIFIED** 2026-09-28).
- *Mega and Legendary were not in the US store's top-10 IAP list (research/web-research.md §IAPs). But Apple's TRY equalisation of
  $49.99 and $99.99 matches the phone's 2.499,99 and 4.999,99 TL exactly, so the USD points are near-certain.
- **Quirk.** In euro storefronts the Mega Bundle ($49.99) and the 50,000-coin pack ($54.99) both equalise to €59.99. That comes from
  Apple's grid, and the original has the same quirk.
- **Assumption.** IAP price points use the same grid as app price points (INFERRED). The script reads
  `/v2/inAppPurchases/{id}/pricePoints?filter[territory]=USA` and matches `customerPrice` exactly, so a mismatch fails loudly. This is
  the `asc_iap.py` pattern.

**App Store Connect text for each product**, English shown. The script writes all 13 locales.
- Reference name (internal, ≤64): "Special Offer", "Mini Bundle" … "1,000 Coins".
- Display name (≤35, INFERRED from ASC Help): same as the reference name.
- Description (≤55, INFERRED): "1,000 coins, 1 of each booster, 1h unlimited lives" (50) … "60,000 coins, 36 of each booster, 72h
  unlimited lives" (53). Coin packs: "A pack of 1,000 coins" (21–23).
- If the first POST returns a length error (409), fall back to "60,000 coins, 36 each booster, 72h ∞ lives" style (≤45).
- Family Sharing: false. Consumables cannot be family-shared.
- The review note (for all 12): "Consumable in-game currency/bundle. Open the basket (Shop) tab at the bottom left of the home screen;
  every product is on that page. Coins are also offered when a player runs short (More Lives, Out of Time, booster popups). No account
  or login."
- **Our coin-pack names differ from the original's.** v552 calls them "Tiny/Small/Medium/Big/Super/Giant Coin Package" (**VERIFIED**
  US list). Ours are "1,000 Coins" etc.

### 2.2 Creating them in App Store Connect (every endpoint VERIFIED in Apple's OpenAPI spec v4.5)

Per product, idempotently (look up existing IAPs by `productId` first):

1. `GET /v1/apps?filter[bundleId]=com.manycode.arrowout` gives the app id. Then `GET /v1/apps/{id}/inAppPurchasesV2?limit=200` gives
   the existing IAPs.
2. `POST /v2/inAppPurchases` with `{name, productId, inAppPurchaseType: "CONSUMABLE", reviewNote, familySharable: false}` and the
   relationship `app`.
3. Localizations: `POST /v1/inAppPurchaseLocalizations` with `{name, locale, description}` and relationship `inAppPurchaseV2`, once for
   each of the 13 locales.
   - Spec 4.5 also has the versioned `POST /v2/inAppPurchaseLocalizations` (relationship `version`). If v1 answers 409, fall back to v2
     using the IAP's version id from `GET /v2/inAppPurchases/{id}/versions`. Which one Apple wants for a brand-new IAP is INFERRED; the
     first run decides.
4. Availability: `POST /v1/inAppPurchaseAvailabilities` with `availableInNewTerritories: true` and `availableTerritories` = the same
   territory list as the app (DECISION §10.4: every territory except CHN).
5. Price: `POST /v1/inAppPurchasePriceSchedules` with `baseTerritory` USA and one inline `inAppPurchasePrices` (`${p1}`, startDate
   null) pointing to the USA `inAppPurchasePricePoint`.
   - **Only USA is written.** Apple generates the other storefronts itself: `GET
     /v1/inAppPurchasePriceSchedules/{id}/automaticPrices` exists (**VERIFIED**).
   - Unlike `asc_iap.py`'s subscriptions, there is **no per-territory loop**, and there must not be one. A manual price in a territory
     freezes that territory's automatic adjustment.
6. Review screenshot: `POST /v1/inAppPurchaseAppStoreReviewScreenshots` with `{fileName, fileSize}` and `inAppPurchaseV2`, then PUT the
   upload operations, then PATCH `uploaded: true` + md5. Same reserve → upload → commit shape as `scripts/asc_review_assets.py`.
   - The same Shop capture can serve all 12 products: the Shop page from a Release-like run with StoreKit prices and **no** test-store
     chip.
   - Without a screenshot the IAP stays `MISSING_METADATA` (INFERRED from the subscription lesson in memory `signing-submit-gotchas`).
7. **Verify by reading, not by trusting the POSTs.** For each product:
   - state `READY_TO_SUBMIT`, 13 localizations, a price schedule whose USA manual price equals the table;
   - `automaticPrices` total ≥ 170 (read `meta.paging.total`, never a capped `limit`: memory `trial-claim-vs-config-drift`);
   - the TUR automatic price equals the golden TRY column above. That makes a golden test of "localize the moneys".

**Submitting the first IAPs.** Spec 4.5 lists `inAppPurchaseVersion` among the `reviewSubmissionItems` relationships, next to
`appStoreVersion`, `subscriptionVersion` and `subscriptionGroupVersion` (**VERIFIED**). So the 12 IAPs go into the same review
submission as version 1.0.0:
- for each IAP, take its editable version (`PREPARE_FOR_SUBMISSION` / `READY_FOR_REVIEW` / `DEVELOPER_REJECTED`) from
  `GET /v2/inAppPurchases/{id}/versions`;
- add a `reviewSubmissionItems` entry with `inAppPurchaseVersion` for each.

`POST /v1/inAppPurchaseSubmissions` also exists, but that is the per-IAP route for later additions. Apple ties the first IAPs to an app
version (INFERRED from Apple's rule "your first in-app purchase must be submitted with a new app version").

### 2.3 Does `asc_iap.py` handle consumables? No. The gaps:

| Gap (VERIFIED by reading the script) | Consequence |
|---|---|
| It only creates `subscriptionGroups` / `subscriptions` / `subscriptionPrices` / `introductoryOffers` / grace period. It has no `inAppPurchases`. | It cannot create a single product for us. |
| Refuses to run without a trial unless `--allow-no-trial`. | Irrelevant to us, but it shows the script is built for subscriptions. |
| `idea.py json <slug>` → ideas.yaml | No entry for mazeout, so it crashes. |
| `bundle = BUNDLE_PREFIX + "." + slug` | Would target `com.manycode.mazeout`. |
| Writes price territory by territory | This is correct for subscriptions but wrong for IAP price schedules (§2.2 step 5). |

**DECISION: write a new `scripts/asc_consumables.py`.** It is a new file, so no other app is touched, and future coin games can reuse
it.
- Arguments: `--bundle com.manycode.arrowout --catalog apps/mazeout/design/publish/iap.json [--screenshot PATH] [--dry-run]`.
- It reuses the `API` class (token refresh, 429/5xx/RemoteDisconnected retries) by importing `scripts/asc_iap.py`, the way
  `asc_keywords.py` imports `asc_submit`.
- `iap.json` has one row per product: `id`, `usd`, `type`, and `locales{loc: {name, description}}`. A self-check asserts that the ids
  and USD prices equal `rules.json:shop` and `ArrowOut.storekit` (three copies, one truth). It also bans "maze", "grand" and "jam" in
  every text field.

### 2.4 RevenueCat (one shared project; the ASC In-App Purchase Key per app)

The facts that bind us:
- memory `revenuecat-one-project`: one project, `proj5f4f704a`. The secret key is project-scoped and cannot create projects.
- memory `revenuecat-asc-key-required`: without the In-App Purchase Key, RC cannot validate StoreKit 2 transactions. `rc_setup.py`
  step 1b already sets both keys from the same .p8.

What Arrow Out needs in RC:
1. **An app entry**: `POST /v2/projects/proj5f4f704a/apps` with `{name: "Arrow Out", type: "app_store", app_store: {bundle_id:
   "com.manycode.arrowout"}}`. Then step 1b: set `subscription_private_key/key_id/issuer` and `app_store_connect_api_key/_id/_issuer`
   to the .env key. Success = both `subscription_key_configured` and `app_store_connect_api_key_configured` true.
2. **12 products** with `type: "consumable"`. RC v2 lists `consumable` among its product types (INFERRED from RC's v2 docs; the first
   POST confirms it, and the script prints the body on error).
3. **No entitlement.** Consumables unlock nothing persistent, and `rc_setup.py`'s `<slug>_pro` entitlement would be meaningless.
4. **An offering (optional, DECISION: create it for completeness).** Lookup key `arrowout_shop` with 12 packages, custom lookup keys
   `offer_special`, `bundle_mini` … `coins_100000` (never `$rc_*`). The app does not depend on it (see mode below). It gives the RC
   dashboard a catalogue and leaves room for a remote price-test later.
   - Offerings belong to the whole shared project. Factory paywalls fetch `offerings.offering(identifier: Config.offeringId) ??
     offerings.current` (**VERIFIED** template `PaywallView.swift:496`). So `arrowout_shop` must **never** be made the project's current
     offering, or an app whose own offering is missing would fall back to our coin packs.
5. **The public `appl_…` key goes into a new `App/Shell/Shop/StoreConfig.swift`** (`static let rcAPIKey = "appl_…"`), so the
   `rc_setup.py`-style regex writer can target it.

**SDK mode. DECISION: observer mode**, `Purchases.configure(with: .init(withAPIKey:).with(purchasesAreCompletedBy: .myApp, storeKitVersion:
.storeKit2))`.
- Our existing StoreKit 2 `StoreService` stays the purchase engine: verified result, then grant once per transaction id, then `finish`.
  It is already covered by `ShellStoreKitTests` (`SKTestSession`). After each purchase the app calls `Purchases.shared.recordPurchase(result)`.
- **Why not let RC purchase?**
  - RC finishes consumable transactions itself. If the app dies between RC's finish and our grant, the coins are lost.
  - Recovering them would need `CustomerInfo.nonSubscriptions`, which needs the network, and a reinstall watermark so old packs are
    not re-granted.
  - Our grant-then-finish plus `Transaction.unfinished` / `Transaction.updates` recovers offline.
- **INFERRED:** `recordPurchase(_:)` is the RC 5.x API for StoreKit 2 observer mode. Pin the RC version (template: `from: 5.0.0`) and
  prove the call with a compile probe before relying on it (memory `revenuecat-cancel-does-not-throw` explains why a probe, not the
  docs).
- **Cancellation still returns, it does not throw.** Our `StoreService` already maps `.userCancelled` to `.cancelled` (**VERIFIED**
  code).

**`rc_setup.py` gaps (VERIFIED by reading):**
- bundle from the slug;
- `idea.py` dependency;
- products are always `type: subscription` with `$rc_weekly/$rc_monthly/$rc_annual` packages;
- always creates `<slug>_pro`;
- writes `App/Config.swift`, which we do not have.

**DECISION:** a new `scripts/rc_consumables.py --bundle … --catalog … --config-file apps/mazeout/App/Shell/Shop/StoreConfig.swift`. It
reuses `call` / `must` / `create_or_get` and step 1b verbatim by importing `rc_setup`.

**RC verification (no in-simulator purchase):**
- After setup, `GET /v2/projects/{pid}/products?app_id=…` returns 12 consumables, and the app's `app_store` block shows both keys
  configured.
- After an on-device sandbox purchase (§9), the RC customer record shows the transaction. RC `offerings()` throws under simulator
  StoreKit testing, so payment checks use the RC API (memory `camera-and-payment-testing`).

### 2.5 App changes the store needs (for the build owner; listed here because release depends on them)

| # | Change | Why |
|---|---|---|
| S-1 (P0) | `ShopStore.start()`: in **Release**, use `StoreService` (StoreKit 2) + RC observer. The FakeStore stays for DEBUG, tests and captures (`-pc.fakeStore`, UI tests) only. | Today Release grants for free (`#else Log.mark("store: FakeStore (Release)")`, **VERIFIED**). Shipping that is a free-money exploit and a 3.1.1/2.1 rejection. |
| S-2 (P0) | `StoreService.isTestStore` → `false`. The "Test store: nothing is charged" chip is FakeStore-only. Release gate: the string is absent from the Release binary. | The chip is honest only for the FakeStore. |
| S-3 (P0) | `ShopView` line 328: remove the fallback `?? ShopFormat.price(p, list: .usd)` in the real-store path. A product without a StoreKit price shows a disabled price well ("…") and the page retries `loadProducts()` on appear and on `Transaction.updates`. | That fallback would show a hard-coded dollar price in any currency, which is exactly the owner's "worst case". |
| S-4 | Add the RevenueCat SPM package (pin the exact version) to project.yml. project.yml belongs to the orchestrator/LEAD (SPEC-architecture §3.4). Configure RC once at boot, off the launch path. | Owner item 10. |
| S-5 | Add `App/PrivacyInfo.xcprivacy`: UserDefaults `CA92.1`, SystemBootTime `35F9.1` (`ProcessInfo.systemUptime` in AppModel, **VERIFIED**), `NSPrivacyTracking` false, collected type PurchaseHistory (not linked, not tracking) to mirror RC. | Since 2024 an upload that uses required-reason APIs without declaring them fails with ITMS-91053 (INFERRED from Apple policy; the template ships this file for the same reason). |
| S-6 | project.yml: `MARKETING_VERSION 1.0.0` (must equal the ASC version string that `create_app` makes), `CURRENT_PROJECT_VERSION 1`. | memory `signing-submit-gotchas`: a mismatch means the build does not attach. |
| S-7 | In-app Privacy page ¶1/¶3 (`strings.tsv` rows 140/142). Today they say "no analytics" and "Purchases are handled by Apple". Add: "Purchases are processed by Apple; our purchase service (RevenueCat) receives an anonymous ID and your purchase records." Keep "no ads, no tracking". | Honest copy once RC ships (memory `no-network-claim-is-false`). Ruling 24 still holds: nothing about other players. |
| S-8 | `ArrowOut.storekit`: align the descriptions with the ASC texts (§2.1) so local testing matches the store. | Parity. |

Tests to add (never weaken existing ones):
- a Release-config store-selection test (a build-config-agnostic factory function);
- "no dollar fallback in the real path";
- `recordPurchase` called exactly once per verified purchase (protocol mock);
- a grant surviving a kill between purchase and finish (`Transaction.unfinished` replay; `ShellStoreKitTests` already has the replay
  primitive).

The existing FakeStore tests (`ShellS3Tests` lines 34–39: "49,99 TL", "$0.99"; the UI tests' `shop.testStoreNote`) stay valid for
DEBUG.

---

## 3. Dynamic local prices (owner item 10: "localize the moneys")

### 3.1 Every price string in the app today (grep of App/ + PathCore, **VERIFIED**)

| Where | What it shows today | Source of the text |
|---|---|---|
| `ShopView.swift` PriceTag (Special Offer card, 5 bundle cards, 6 coin tiles) | `prices[storeID]` = `app.shop.products[].displayPrice` | FakeStore in Release: **hard-coded** `ShopFormat.price`, TL if the device region is TR, else US$ |
| `ShopView.swift:328` fallback | `ShopFormat.price(p, list: .usd)` = **hard-coded US$** | `ShopCatalog.priceUSD` |
| `FakeStore.products` | `ShopFormat.price($0, list: priceList)` → "49,99 TL" / "$0.99" | `priceTRY` / `priceUSD` literals in `ShopCatalog.defaultProducts` |
| `StoreService.loadProducts` (DEBUG + StoreKit config only) | `Product.displayPrice` | StoreKit, **already dynamic** |
| `ShopView.swift:8, 349–360` | "Test store: nothing is charged" chip | FakeStore flag |
| Every other price in the game (Refill 900, Buy ×3 900, Add Time 900, Play On 900) | **coins**, not money | `rules.json` economy |

No other surface shows real money: no popup, banner or notification (grep of `displayPrice` / `ShopFormat.price` / `priceUSD` /
`priceTRY`).

### 3.2 How each one changes

- **Shop PriceTags (Release)** show `Product.displayPrice` from StoreKit 2. It is formatted in the user's **storefront currency**,
  e.g. "₺49,99", "59,99 €", "¥8,000", "₩149,000", "R$ 599,90", "499,99 zł".
- With RC observer mode we keep StoreKit's `Product` as the source. RC's `StoreProduct.localizedPriceString` is the same string if RC
  is ever the engine.
- **Fit.** PriceTag has `maxWidth` 112 pt for cards and 80 pt for coin tiles, with GameText's 0.7 minimum scale.
  - TRY ("4.999,99 TL", 11 chars) was already the design's widest case and is VERIFIED on v552's tiles.
  - The other 12 storefronts' strings are ≤ 10 characters (INFERRED from the equalised amounts above).
  - Add a fit check: render every product's `displayPrice` for storefronts USA/TUR/DEU/FRA/JPN/KOR/BRA/POL/GBR through
    `GameTextLayout` and assert scale ≥ 0.7. This uses the numbers, so no simulator is needed (a macOS unit test).
- **FakeStore (DEBUG/tests/captures)** keeps its literal TL/US$ list. It must not be reachable in Release (S-1).
- `ShopCatalog.priceUSD` / `priceTRY` stay as **reference data only**: the FakeStore and the `iap.json` self-check. Rename the doc
  comment to say so.

### 3.3 Why no daily manual changes are needed (the owner's inflation worry)

- An IAP whose price schedule has a **base territory** (USA) gets Apple-generated prices in every other storefront. Apple re-adjusts
  them when taxes or exchange rates move (INFERRED from Apple's pricing docs; the `automaticPrices` endpoint is VERIFIED).
- The app never stores a price. It reads `displayPrice` at runtime, so a Turkish user sees whatever TRY price Apple has set that week.
- **Evidence that this is what the original does:** Apple's current TRY equalisation of our 12 USD points equals v552's TL shop list
  character for character (§2.1, **VERIFIED**).
- **Do not** add manual per-country prices. Each one freezes that storefront against Apple's future adjustments.
- The owner's worst case (dollar prices in-app, local currency only in Apple's sheet) is **not needed**.

### 3.4 Edge cases the Release store must handle

| Case | Behaviour |
|---|---|
| No network at first open | The disabled price well ("…") and a retry on appear. Gameplay is unaffected (offline game). |
| Pending (Ask to Buy) | Existing toast "Purchase pending". The grant arrives through `Transaction.updates`. |
| Refund / revocation | No claw-back of coins (DECISION; RC records the refund). |
| Special Offer bought | It disappears for this install (`specialOfferOnce`, **VERIFIED**). |
| Reinstall | Consumables are not restorable. Purchased coins live only on the device (INFERRED consequence of local saves). See §11. |

---

## 4. Owner item 9: every ad / "watch video" offer, and removing it cleanly

### 4.1 Inventory (grep of App/, Packages/, Tests/, UITests/, strings, tuning, art, design; **VERIFIED**)

| # | Place | What |
|---|---|---|
| A1 | `App/Shell/Popups/NoLivesPopup.swift:43` | `AdLiveButton { AdSlot.show(app) }` |
| A2 | `NoLivesPopup.swift:111-134` | `AdLiveButton`: its offer well (69.4, 558.8, 254.5 × 104.1), green face (80.7, 567.5, 231.9 × 86.4), `iconVideoAd`, `heartGlossySmall`, "+1", "Live"; a11y id `popup.noLives.ad` |
| A3 | `NoLivesPopup.swift:137-143` | `enum AdSlot` → toast "Video not available", `Log.mark("ad", …)` |
| A4 | `NoLivesPopup.swift:1-13` header comment | describes the ad button |
| A5 | `App/Resources/Strings/strings.tsv:65` + `Localizable.xcstrings:3208` | "Video not available" / "Video şu anda kullanılamıyor" |
| A6 | `tools/strings/sources.json:245`, `tools/strings/tr_review.py:59` | coverage and fit rows for the toast |
| A7 | `App/Shell/Components/UIArt.swift:109/324/541/758` | `case iconVideoAd` (generated by `tools/uiart_gen.py`) |
| A8 | `art/MANIFEST.json:7120-7147` | `iconVideoAd` entry (`art/ui/out/iconVideoAd@3x.png`, `gen_missing.py:iconVideoAd`) |
| A9 | `App/Resources/Tuning/rules.json:32` | `"rewardedAd": "adSlot"` |
| A10 | `Packages/PathCore/Sources/PathCore/Economy/EconomyRules.swift:61-62, 74` | `Lives.rewardedAd` field + decoder |
| A11 | `Packages/PathCore/Tests/Fixtures/c3_rules_spec15.json:224` | `"rewardedAd": "adSlot"`, read by `EconomyTests.testTheSpecSection15DecodesToExactlyTheCompiledDefaults` (its `unknownKeys` check fails if the field goes but the fixture keeps it) |
| A12 | `UITests/ShellS3UITests.swift:72-85` | `testMoreLivesRefillAndOfflineAd`: taps `popup.noLives.ad` and expects the toast |
| A13 | Specs | SPEC.md §5.18; SPEC-gameplay §8.4 (lines 418-420), §15 (line 800), §16.6 (line 923); SPEC-ui §2.9 `moreLives.adLive` (line 634), §2.20 (932-940); CONSISTENCY X-13, U-26, S-20 |

**Nothing else offers a video or an ad.**
- The Continue / Out of Time / Out of Lives / booster popups are coin-only.
- The win panel has no "x2 with video".
- The home screen has no ad slot.
- There is no ad SDK: no network code other than StoreKit (grep for `URLSession` / `http` in App/ found nothing).

### 4.2 Clean removal (one change set, owned by SHELL + CORE + CONTENT; orchestrator approves the non-frozen PathCore edit)

1. **UI.**
   - Delete `AdLiveButton`, `AdSlot` and the A4 comment lines. Rewrite the header: "Refill [coin] 900 is the only offer".
   - **Shorten the More Lives panel under its one button, as `BoosterBuyPopup` already does** ("The panel is shortened to end under the
     one button", **VERIFIED** comment).
   - Remove the 115.8 pt ad row: panel 164.5 → 706.3 becomes 164.5 → 590.5, and the X / ribbon / heart / timer / Refill positions stay.
     Re-centre only if the other one-button popups are centred. That is a V2-style side-by-side check against `BoosterBuyPopup`, done
     by the UI owner.
2. **Economy.**
   - Remove `Lives.rewardedAd` (field, CodingKey, decoder line) from `EconomyRules.swift`, `"rewardedAd"` from `rules.json` and from the
     fixture `c3_rules_spec15.json`, and the §15 JSON in SPEC-gameplay line 800. All four in one commit, so `unknownKeys`,
     `EconomyRules.default` equality and `ScaffoldTests.testTuningFilesAgreeWithTheCompiledDefaults` stay green unchanged.
   - `EconomyRules.swift` is **not** a frozen ◆ contract (**VERIFIED** against `build/wp0/frozen-contracts.sha256`), so no re-hash.
3. **Strings.** Delete the row in strings.tsv, the sources.json coverage row and the tr_review.py fit row, then rebuild the catalogue
   (`python3 tools/strings/build.py`, then `--check`). The key disappears from all 13 locales before translation starts. Do this first,
   so nobody translates it.
4. **Art.** Mark `iconVideoAd` NOT-SHIPPED in MANIFEST.json, regenerate `UIArt.swift` (`tools/uiart_gen.py`) and remove the PNG from
   `art/ui/out`. **Before removing the generated case, grep Tests/ and UITests/ for `iconVideoAd`**: that is the PLAN 00:18 pitfall
   (today: no hits outside UIArt.swift, **VERIFIED**).
5. **Tests.** Rename `testMoreLivesRefillAndOfflineAd` to `testMoreLivesRefill`.
   - Replace the ad-tap block with `XCTAssertFalse(app.element("popup.noLives.ad").exists, "no rewarded-ad offer (owner item 9)")`.
   - Keep every refill assertion (count 3 → full, coins 1000 → 100).
   - This is a spec change (ruling 37d), not a weakening; log it in the report.
   - `AccessibilityIDTests` only requires `popup.noLives` and `.close`, so it is unaffected.
6. **Specs.** Mark SPEC.md §5.18 "SUPERSEDED by ruling 37(d)". Annotate SPEC-gameplay §8.4/§16.6, SPEC-ui §2.9/§2.20 and CONSISTENCY
   X-13/U-26/S-20 the same way. Never delete evidence rows.
7. **Release gates** (added to the release checklist, §8 R6):
   - `strings` of the Release binary and bundle has 0 hits for `Video not available`, `iconVideoAd`, `AdSlot`, `rewarded`, `popup.noLives.ad`;
   - `otool -L` shows no ad framework;
   - the More Lives popup screenshot is looked at in EN and one long locale (DE or PL).

**Store consequence.** "No ads" becomes a true claim. It is used in the description and in keyword 5 (§6). App Privacy stays "no
tracking", and the age rating answers `advertising: false`.

---

## 5. 13-locale plan (owner item 10: "localize perfectly")

**Which set.** The owner wrote "the 10 languages we always localize to". The factory rule changed on 2026-09-12 to **13**
(`localize-top-13-locales`: + pl, sk, sl), and ruling 37 already says 13. DECISION: 13, and the owner confirms (§10.2).

- Store locales: `en-US de-DE fr-FR es-ES it pt-BR tr ja ko zh-Hans pl sk sl-SI`.
- In-app catalogues: `en de fr es it pt-BR tr ja ko zh-Hans pl sk sl`. The store says **sl-SI**; the catalogue uses **sl**.

### 5.1 What has to be translated (VERIFIED counts)

| Surface | Size | Tooling today |
|---|---|---|
| In-app strings (`Localizable.xcstrings`) | **207 keys, 746 English words, 4,044 chars, 31 with format specifiers**; EN + TR done | `tools/strings/build.py` (TSV → xcstrings, EN+TR only; validates specifier count/order, `**` highlights, brand ban incl. "Maze Out", "Arrow Jam", "Grand Games"), `coverage.py`, `tr_review.py` (fit) |
| Social data | Country names via `Locale.localizedString(forRegionCode:)` (**VERIFIED**, `SocialShells.swift:171`, already localized by iOS); name pools per culture (`given_*.txt`) are not translated (names) | — |
| Local notifications | 2 strings (in the 207) | — |
| Store metadata | name, subtitle, promo, description (~3,000–3,900 chars) × 13 | none in mazeout. Copy the pattern of `apps/conduitbend/tools/{loc.py, meta.py}` (writes URLs **before** the length check) |
| Keywords | 13 × ≤100 chars, **researched per storefront, never translated** | `scripts/asc_keywords.py` + `design/keywords.json` |
| IAP localizations | 12 products × 13 locales × (name ≤35, description ≤55) | the new `asc_consumables.py` (§2.3) |
| Screenshot captions | 5 × 13 (= the locale's first 5 keywords) | `scripts/make_screenshots.py` (per-language fonts) + `design/captions/<loc>.json` |

### 5.2 Pipeline (DECISION)

1. Remove the ad string first (§4.2 step 3).
2. Extend `strings.tsv` from `en<TAB>tr<TAB>context` to 13 language columns plus context. Alternatively use one TSV per language
   (`strings.<lang>.tsv`), which keeps the TR column and its review history intact.
   - `build.py` writes 13 localizations and applies its existing validations to **every** column: specifier types in EN order with
     positional `%1$@` for reordering (memory `reordered-args-need-positional`), balanced `**` markers, and the brand ban.
3. **Translation standard (owner): "dont just chicken translate."**
   - One native-register pass per language, then an adversarial review pass per language, the way `tr_review.py` worked for TR.
   - Slavic plurals (pl/sk/sl): any string with a number (`%lld`) uses a phrasing that survives every case, or an xcstrings plural
     variation.
   - Game jargon stays consistent across all screens: Time Freeze, Hint, Box, Pipe, Door, Key, Elevator, Corner, Linked.
4. **Fit.** Generalise `tr_review.py` to all 13 columns: every string against its measured frame (size, tracking, width, lines) with
   GameText's `minScale` 0.7 (SPEC.md §5.14). German, Polish and French run about 20–35 % longer than English (INFERRED).
   - A row that fails gets a shorter native phrasing, never a smaller floor.
5. **CJK glyphs (P0 for ja/ko/zh-Hans).**
   - `PCDisplay-Black.ttf` (Nunito) has **no Japanese, Korean or Chinese glyphs** (fontTools cmap check: 矢印あア / 화살표 / 箭头 all
     missing; Latin incl. tr/pl/sk/sl/de/fr/es/pt all present, **VERIFIED**).
   - `GameText` takes each run's font from CoreText (`runFont` per run), so today iOS falls back to a system font of whatever weight it
     picks under a 1000-weight outline style (INFERRED look: thin CJK inside thick outlines).
   - **DECISION:** give PC Display a `kCTFontCascadeListAttribute` of the heaviest system CJK faces, chosen by language: Hiragino Sans
     W8 (ja), Apple SD Gothic Neo Heavy (ko), PingFang SC Semibold (zh-Hans). This adds no bundle size.
   - Alternative if they look weak: bundle OFL black CJK fonts (e.g. M PLUS Rounded 1c Black for ja). That is a size cost, and the owner
     weighs in only if the cascade fails the look.
   - `DigitGlyphs` / `SocType` use PC Display only for digits and Latin names, so they are unaffected.
   - The look is judged on renders: art-lane rules, no heavy renders now.
6. **Numbers and units stay 1:1 with v552**: thin-space "1 000", "9h 50m", "∞ 30m". v552 shows these in English UI on a Turkish phone
   (**VERIFIED** research), so every locale keeps the English unit letters.
   - DECISION: keep them as they are. A later polish could localise units with `DateComponentsFormatter(.abbreviated)` if the owner
     wants that.
7. `.xcstrings` compiles to `<lang>.lproj`. Release gate: the built `.app` holds 13 `.lproj` folders and `plutil` passes. Run
   `tools/gen.sh` (the mutex) after any project change, never raw `xcodegen`.
8. **Store metadata.** Add app-local `tools/release/loc.py` + `meta.py` (the conduitbend pattern):
   - limits 30/30/170/4000, checked **after** writing `privacy_url.txt` / `support_url.txt`;
   - `audit()` fails if any locale has a `keywords.txt`;
   - **no `release_notes.txt` for 1.0.0**: memory `keywords-are-user-owned` says `whatsNew` on a first version gives a 409;
   - then `scripts/fill_locale_urls.py --slug mazeout` as a belt-and-braces check.

---

## 6. ASO plan (owner item 11-text; ruling 37a)

### 6.1 Research (curl of the iTunes Search API + App Store autocomplete, US storefront unless noted; **VERIFIED** 2026-09-28)

**Autocomplete** (App Store search hints) shows real search phrases:
- "arrow" → arrows – puzzle escape, **arrow puzzle**, arrows go, arrows, **arrow game**, arrowscapes, **arrow out**, arrow maze …
- "arrow e" → **arrow escape**, arrow escape game, arrow escape: arrows go 3d, arrow escape: arrow out …
- "arrow out" → **arrow out**, arrow out: puzzle game, free arrow out game, arrow out 3d, arrow out no ads, arrow out puzzle …
- "arrow g" / "arrow ga" → arrow game, **arrow game no ads**, hard arrow games, free arrow games …
- "arrow p" → arrow puzzle, arrow puzzle 3d, arrow puzzle escape, **arrow puzzle no ads** …
- "tap ar" → **tap arrows**, tap arrows gallery, **tap arrows: maze out** (!), tap arrow away …
- "tap puz" → … **maze out! - tap puzzle** (!) …

**The competitor's brand is a live search term.** Anything that lets Apple combine words into "maze out" would target it.

**Competitors** (title, ratings):
- Arrows – Puzzle Escape (Lessmore, 461k)
- Color Maze (468k)
- Point Out: Color Escape Puzzle (248k)
- Amaze GO! (211k)
- CubeAway (102k)
- Redirect It! (99k)
- Arrow Puzzle – Tap Away Game (Easybrain, 27k)
- Arrow Fever: Tap Out Puzzle (22k)
- **Arrow Out Puzzle (PIXEL KING, 13k)**

The genre is new (most titles are from 2025–26) and very crowded.

**Titles already using "Arrow Out"** (all taken for exact-name purposes): Arrow Out Puzzle · Cube Jam: Arrow Out · Arrow Out 3D: Tap Away
Game · Arrow Out Cube · Arrow Out: Maze Puzzle · Arrow Out: Tap Arrows Puzzle · Arrow Out – Puzzle Escape · Arrow Out: Brain Puzzle ·
Arrow Out: Logic Puzzles Game · Arrow Out: Puzzle Game · Arrow Out Escape Puzzle Game · Arrow Out Puzzle - Maze Escape · Arrow Out Puzzle
Tap Away · Arrow Out Tap Away 3D Puzzle · **Arrow Escape: Arrow Out** (Huy Huynh) · Jelly Escape: Arrow Out Puzzle · plus about 10
"Arrows Out …" titles.

**Localized autocomplete samples** show that keywords must be researched per storefront, not translated:
- TR: "ok oyunu, ok bulmacası, ok çıkarma oyunu", plus English "arrows puzzle", "arrow out" in the TR store;
- DE: "pfeil spiel, pfeil rätsel, pfeile raus: logik rätsel";
- JA: "矢印ゲーム, 矢印パズル";
- pt-BR: "jogo da flecha, flechas em fuga";
- PL: "gra w strzałki".

Search volume and difficulty are **not** measured: Appfigures is browser-only, and this job's rule is curl only.

### 6.2 Seed keyword and store name (rules: memory `app-naming-keyword-first`, `aso-keywords-and-screenshots-rule`, ROUTINEAPPS rules 1–4)

| Option | Seed (first keyword, verbatim) | Store name (≤30, starts with the seed, keeps "Arrow Out") | Pros / cons |
|---|---|---|---|
| **A (recommended)** | `arrow out` | **Arrow Out: Arrow Escape Puzzle** (30) | The seed is the owner's brand **and** a real autocomplete family (arrow out game / puzzle / no ads / 3d). The name also carries "arrow escape" and "arrow puzzle". Every locale's name can start with the same seed ("Arrow Out: " + a local descriptor). Con: the brand is generic and shared with about 15 titles. |
| B | `arrow escape puzzle` | Arrow Escape Puzzle: Arrow Out (30) | Leads with a descriptive head term. Con: the brand ends up last; "Arrow Escape: Arrow Out" is already taken, so the difference is only the word "Puzzle". |
| C | `arrow puzzle` | Arrow Puzzle - Arrow Out (24) | "arrow puzzle" ranks just above "arrow out" in the "arrow" hints. Con: Lessmore and Easybrain dominate that term. |

- None of the three names appears in the US, TR or GB search results (INFERRED unique). `create_app` is the real test. If a name is
  taken, keep the seed prefix and change only the suffix, e.g. "Arrow Out: Timed Escape Puzzle" (30) or "Arrow Out - Escape Puzzle
  Game" (30).
- **Avoid** in the name: "!" after Arrow Out, and "Tap Puzzle". The original is "Maze Out! - Tap Puzzle" (**VERIFIED**), and echoing
  its punctuation and suffix invites a 4.1 copycat reading.

### 6.3 Subtitle, keywords, promo (en-US, option A)

**Subtitle (≤30).** "**Tap Away, Beat the Clock**" (24). It adds "tap", "away", "beat" and "clock", none of which are in the name.
Alternative: "Timed Tap Away Brain Teaser" (27).

**Keywords (≤100, no spaces after commas, seed first, long-tail, every phrase a VERIFIED autocomplete or its direct variant):**

```
arrow out,arrow escape game,tap arrows puzzle,hard arrow games,arrow game no ads,escape puzzle game
```

99 characters.

**Hard exclusions**, enforced by the `iap.json` / metadata self-check and a pre-upload grep in every locale:
- `maze`: combined with "Out" in the name it matches "maze out";
- `grand`, `jam` (the original's former name "Arrow Jam!", **VERIFIED** web research);
- `arrows puzzle escape` / `arrows – puzzle escape` (Lessmore's exact title);
- `tap away 3d` (Popcore's title). "tap away" alone is used descriptively by dozens of titles; the subtitle uses it, and the owner can
  veto it (§10).

**Promotional text (≤170).** "Free the arrows, beat the clock! Tricky obstacles, weekly events and no ads: just you, the board and the
timer." (111)

**First-version mechanics:**
- The keywords field **must** be set or submit fails with a 409 (memory `new-app-needs-keywords`).
- Write it with `scripts/asc_keywords.py --slug mazeout` from `design/keywords.json`. **Never** use a `keywords.txt` (memories
  `keywords-are-user-owned`, `template-scaffolds-empty-keywords-txt`).
- This is a new app, so this first set is ours to write. After launch, `never-touch-keywords-or-description` applies.

### 6.4 Description angle (≈3,000–3,900 chars, honest; ROUTINEAPPS rule 5)

Structure: hook (3 lines above the fold) → why you'll like it → obstacles → events → how to play → in-app purchases → links.

- **Hook (draft):** "Tap an arrow and it slides out along its path — if nothing is in the way. Clear the whole board before the timer runs out. Plenty
  of moves, not much time."
- **Truthful features:**
  - a timer on every level;
  - hearts: a blocked tap bumps back and costs one;
  - obstacles in the order players meet them: linked arrows, boxes, pipes, elevators, doors & keys, corners (SPEC.md §5.19/§5.26);
  - Hard and Super Hard levels with bigger coin rewards;
  - two boosters (Time Freeze, Hint);
  - weekly events (Streak Race, Rocket Race, Sky Jump, Claw Challenge, Weekly Contest);
  - no ads;
  - no account;
  - play offline;
  - haptic feedback.
- **Must NOT appear** (every locale, grep-gated):
  - "Maze Out", "Grand Games", "Arrow Jam", "maze";
  - any claim of real or online opponents ("compete with players worldwide", "online leaderboard"). The events are an on-device
    simulation (ruling 24's spirit applies to store copy, and a false claim is a 2.3.1 risk);
  - "no network at all": purchases use the network (memory `no-network-claim-is-false`). Say "Play offline — no Wi-Fi needed to
    play";
  - level counts we cannot back: 150 authored plus a generator is fine as "hundreds of levels", but not "10,000 levels";
  - "hand-made" for L151+.
- **Closing lines:**
  - "Optional in-app purchases: coin packs and bundles. Prices are shown in your local currency before you buy."
  - Privacy URL and Terms (Apple standard EULA) per ROUTINEAPPS rule 6.
  - No subscription legalese: there are no subscriptions.

### 6.5 The five screenshots (exactly 5; the caption = keyword N verbatim, title-cased, and nothing else on the image)

All five use the **new** art and palette (items 1/15). Nothing shows the original's characters, colours or logo.

| # | Caption (= keyword N) | Screen (a real, clean in-use capture; memory `screenshots-verify-content-not-count`) |
|---|---|---|
| 1 | **Arrow Out** | Hero: a large silhouette board (heart or crescent) mid-clear. Three to five arrows streaming off with the exit trail; HUD timer, hearts and level tab visible. |
| 2 | **Arrow Escape Game** | Obstacle showcase: a mid-size board with a door + key and a pipe, one arrow mid-exit through the pipe. |
| 3 | **Tap Arrows Puzzle** | The tap: an early-mid level, a finger-tap ripple on the arrow as it starts moving, the board readable at thumbnail size. |
| 4 | **Hard Arrow Games** | A Hard or Super Hard level (red or purple HUD tab), a dense 30×30+ board, the timer low, Time Freeze frost active. |
| 5 | **Arrow Game No Ads** | Home: the new lab scene with the new characters, event badges (Streak/Rocket), the LEVEL plate and Play. No banner anywhere, which is the point of the caption. |

**Pipeline:**
- raw captures at 1179×2556 from the simulator (iPhone 16; captured later, not in this phase) into `shots/final/`;
- `python3 scripts/make_screenshots.py --slug mazeout` (captions from `design/captions/<loc>.json`; its `assert_rendered()` refuses
  flat frames);
- **look at every generated frame in every locale**;
- `python3 scripts/asc_screenshots.py --slug mazeout --version 1.0.0` (deliver cannot upload screenshots on this machine: memory
  `deliver-cannot-upload-screenshots`);
- read back 5/5 per locale **and** open the uploaded images.

Localized sets use each locale's first 5 researched keywords as captions. The raw captures are taken with `-AppleLanguages (<lang>)` so
the in-game text matches.

**iPad.** If the owner chooses universal (§10.3), add a 13-inch iPad set via `--device ipad13` (2064×2752) plus an iPad layout pass.

---

## 7. Privacy nutrition, age rating, compliance, URLs, copyright

| Field | Answer | Basis |
|---|---|---|
| App Privacy: tracking | **No tracking.** No IDFA, no ATT, no ad or analytics SDK. | code grep (**VERIFIED**) |
| App Privacy: data collected | **Purchases → Purchase History**, not linked to identity. Purposes: App Functionality (+ Analytics: DECISION, because in observer mode RC's role is revenue reporting). Nothing else: the username, progress and settings stay on the device, and notifications are local. | template `app_privacy_details.json` (factory standard, 30+ approvals) + RC |
| How it is uploaded | `fastlane upload_privacy` (`upload_app_privacy_details_to_app_store`). It needs the **Apple ID session** (§8 R1) and is **never** skipped on a first version (memories `app-privacy-needs-apple-id`, `empty-env-var-is-truthy`). | no public API (**VERIFIED** spec) |
| Privacy manifest | `App/PrivacyInfo.xcprivacy` (S-5) | §2.5 |
| Age rating | Every answer NONE/false, giving **4+**. `contests: NONE` because the Weekly Contest / events are single-player, have virtual-coin rewards and no entry fee. v552 has the same events and is rated 4+ (**VERIFIED** lookup). Also `lootBox false` (the Claw ladder is deterministic, nothing is paid-random), `gamblingSimulated NONE`, `advertising false` (after item 9), `userGeneratedContent false` (the username is shown to nobody), `messagingAndChat false`, `unrestrictedWebAccess false`, `socialMedia false`, `socialMediaAgeRestricted false`, `kidsAgeBand null` (not "Made for Kids"). | spec v4.5 fields (**VERIFIED**); `contentStatuses` include `CANNOT_SELL_CONTESTS`, so a careless "contests" answer could block storefronts (**VERIFIED** enum) |
| Where the rating is set | `app_rating_config.json` via deliver. The template lacks the new `socialMedia*` keys, so DECISION: `PATCH /v1/ageRatingDeclarations/{id}` by API and read back `appInfos.appStoreAgeRating` == 4+. | |
| Export compliance | `ITSAppUsesNonExemptEncryption = NO` (project.yml, **VERIFIED**). Only Apple/RC HTTPS is used, which is exempt. deliver `export_compliance_uses_encryption: false`. | |
| IDFA | `usesIdfa` false (deliver `add_id_info_uses_idfa: false`). | memory `idfa-declaration-and-invalid-binary` |
| Content rights | `DOES_NOT_USE_THIRD_PARTY_CONTENT` (set automatically by `asc_submit.ensure_submission_prereqs`). Art is ours, audio is synthesised with the factory kit (matchfactory `tools/audio`), the font is OFL. | GAMEPROMPT §558, SPEC §2 |
| Price | Free. `asc_submit.py` always (re)creates the $0 schedule (memory `app-price-schedule-required`). | |
| Category | Primary **GAMES**, subcategories **GAMES_PUZZLE** + **GAMES_CASUAL** (the original: Games/Puzzle/Casual, **VERIFIED**). Deliverfile: `primary_category "GAMES"`, `primary_first_sub_category "GAMES_PUZZLE"`, `primary_second_sub_category "GAMES_CASUAL"` (precedent: partypack, ROUTINEAPPS row 32). | |
| Support URL | https://leomarston.github.io/manycode-legal/support.html (**VERIFIED** 200) | ROUTINEAPPS rule 6 |
| Privacy URL | https://leomarston.github.io/manycode-legal/privacy-arrow-out.html (RFIX 2026-09-29: the Arrow Out page since the Meta SDK; live 200 from 23:24, manycode-legal eaa195f; tools/release/loc.py PRIVACY + the 13 store sources follow it). The shared privacy.html says "no advertising SDKs" and no longer fits this app. | |
| Terms / EULA | Apple standard EULA (linked from the description) | |
| Marketing URL | none (optional) | |
| Copyright | **2026 Manycode Apps** (`fastlane/metadata/copyright.txt`; never the account name) | memory `copyright-and-five-screenshots` |
| Review contact | from .env REVIEW_* (**VERIFIED** set) | |
| Review notes (draft) | "Arrow Out is a free puzzle game. No account or login. All in-app purchases are consumable coin packs/bundles: open the basket (Shop) tab on the home screen. Nothing needs restoring (consumables only). Leaderboards and events run entirely on the device; no personal data leaves the device except the purchase record processed by Apple/RevenueCat." The events sentence is DECISION §10.7. | |
| Availability | Every territory **except China mainland** (DECISION §10.4). A game with IAP there needs a Game Registration Number: the spec's `contentStatuses` include `MISSING_GRN` / `UNVERIFIED_GRN` (**VERIFIED**), and we have none. zh-Hans still ships for Chinese-language users in other storefronts. After setting availability, read `territoryAvailabilities[].contentStatuses` and list any territory that is not AVAILABLE (e.g. BRAZIL_REQUIRED_TAX_ID, TRADER_STATUS_*). Same list for the 12 IAPs. | |

---

## 8. Submit sequence (scripts, gates, and every step that may need the owner)

Legend: [OWNER] needs the owner · [SCRIPT] scripted · Gate = stop if red.

| Step | What | How | Gate / traps |
|---|---|---|---|
| **R0** | Build is feature-complete for publish | Items 1–8, 11–15 done by their lanes; §2.5 S-1…S-8; §4.2 item 9 removal; 13 locales (§5); the real icon (item 11) | Gate: CLAUDE.md gates that fit a coin game: clean build, screenshots looked at, empty states, rating prompt only after a meaningful action (L34, **VERIFIED** PLAN), Contact Support (anycodeapps@gmail.com). The paywall and Restore gates do not apply (§10.6). |
| **R1** [OWNER] | **Renew the Apple web session** | Owner runs `fastlane spaceauth -u esaridogann@gmail.com` (password + 2FA code on their trusted device). Optionally paste `export FASTLANE_SESSION=…` into .env. | Gate: `DES…` cookie `created` < 30 days old. Expired since 2026-09-20 (**VERIFIED**). Needed for R3 and R11. |
| **R2** [SCRIPT] | Scaffold `apps/mazeout/fastlane/` from `template/fastlane` by hand (not `new_app.sh`: it needs ideas.yaml and runs raw xcodegen). Token values: `com.manycode.arrowout`, scheme `ArrowOut`, store name from §6.2, SKU `arrowout-<ts>`, profile `manycode arrowout appstore`. | Fastfile edits: `regenerate_project` → `tools/gen.sh`; delete the template's empty `keywords.txt`; no `release_notes.txt` (1.0.0); Deliverfile categories (§7); `copyright.txt`; review_information from .env. | Gate: `find fastlane -name keywords.txt` finds nothing. The metadata grep for maze/grand/jam comes back empty. |
| **R3** [SCRIPT+OWNER] | Create the app record | `cd apps/mazeout && fastlane create_app` (produce, name = §6.2). Uses the Apple ID session, so R1 comes first (no `POST /v1/apps` exists, **VERIFIED**). | Gate: `GET /v1/apps?filter[bundleId]=com.manycode.arrowout` returns 1. If the name is taken, change only the suffix (§6.2) and update name.txt + Fastfile. |
| **R4** [SCRIPT] | Signing | `python3 scripts/signing_setup.py --slug mazeout --bundle com.manycode.arrowout` (new additive `--bundle` flag) | Gate: `security find-identity -v -p codesigning` shows one identity per name (memory `signing-keychain-shadowing`) |
| **R5** [SCRIPT] | 12 consumables in ASC | `python3 scripts/asc_consumables.py --bundle com.manycode.arrowout --catalog apps/mazeout/design/publish/iap.json --screenshot apps/mazeout/shots/final/shop-review.png` | Gate: 12 × READY_TO_SUBMIT; 13 localizations each; USA price = table; automaticPrices total ≥ 170; TUR = the golden TRY column |
| **R6** [SCRIPT] | RevenueCat | `python3 scripts/rc_consumables.py --bundle com.manycode.arrowout --catalog … --config-file apps/mazeout/App/Shell/Shop/StoreConfig.swift` | Gate: both key flags true; 12 consumable products; the `appl_` key written. Then build + unit tests (StoreKit tests) green. |
| **R7** [SCRIPT] | Archive + upload | `fastlane upload_build` (binary only; unlocks the keychain inside the lane) | Gate: `df -h` first (memory `disk-full-lies`). Poll `/v1/builds` (limit ≥ 10, match the version) until VALID, and **never bump on "already used"** (memory `build-lag-never-bump`). If altool loops on "Checksums do not match", kill it and re-upload the same IPA. **Release gates on the IPA:** no ad strings (§4.2.7), no "Test store", no "maze"/"grand"/"arrowjam"/"simulat" in user-facing strings, 13 `.lproj`, `PrivacyInfo.xcprivacy` present, `plutil -p` on the built Info.plist (portrait; `ITSAppUsesNonExemptEncryption` false). |
| **R8** [SCRIPT] | Text metadata (13 locales) | `tools/release/meta.py` → `fastlane upload_meta_only` (no screenshots, no binary) → `python3 scripts/asc_keywords.py --slug mazeout` | Gate: each locale has name/subtitle/description/promo/supportUrl/privacyPolicyUrl; keywords non-empty in all 13 (read back); copyright "2026 Manycode Apps" |
| **R9** [SCRIPT] | Screenshots | `make_screenshots.py` → **look at all 65** → `asc_screenshots.py --slug mazeout --version 1.0.0` | Gate: 5/5 per locale via the API **and** every uploaded frame opened |
| **R10** [SCRIPT] | App-level settings | age rating PATCH (§7); availability without CHN (`POST /v2/appAvailabilities`) and the same for the IAPs; content rights + free price (inside `asc_submit`) | Gate: `appStoreAgeRating` 4+; no unexpected `contentStatuses` |
| **R11** [SCRIPT+OWNER] | App Privacy | `fastlane upload_privacy` (Apple ID session from R1) | Gate: no `APP_DATA_USAGES_REQUIRED` at R12 |
| **R12** [SCRIPT] | Submit | `python3 scripts/asc_submit.py --slug mazeout --bundle com.manycode.arrowout --uses-idfa` (RFIX 2026-09-29: the Meta SDK ships, so usesIdfa=true is PATCHed and read back BEFORE the review submission is created — deliver ignores add_id_info_*; set once already, 1.0.0 read back true at 23:58; poll the version ≥ 15 min after submitting for INVALID_BINARY; `fastlane upload_privacy` must have published fastlane/metadata/app_privacy_details.json first — Apple ID web session), with two additive changes: the `--bundle` flag, and **IAP items**: for every `/v1/apps/{id}/inAppPurchasesV2` IAP, its editable `/v2/inAppPurchases/{id}/versions` goes in as `inAppPurchaseVersion`. Exit if any of the 12 is not READY_TO_SUBMIT: never submit an app whose shop has nothing reviewable (the mirror of memory `submit-without-subscriptions`). | Gate: Read independently: reviewSubmission WAITING_FOR_REVIEW; version state; `GET /v1/appStoreVersions/{vid}/build` = our build number; all 12 IAP versions WAITING_FOR_REVIEW. **Re-poll for 15 min** (INVALID_BINARY appears asynchronously). |
| **R13** | Bookkeeping | PROJECT_LOG line, memory `arrowout-build-state`, commit (orchestrator) | commit-when-work-is-done |

**Owner touch points, honestly.** Item 10 says "without me touching anything". At minimum there is **one 2FA** (R1, which covers R3 +
R11). There is **one more** if the on-device purchase test uses a sandbox tester (§9), because the public API cannot create sandbox
testers (only list/update, **VERIFIED**: 0 exist). Everything else is scripted. If the session could be renewed without the owner, R1
would go away, but it cannot: the 2FA code arrives on the owner's device.

**Which scripts need changes (summary):**

| Script | Change | Kind |
|---|---|---|
| `asc_submit.py` | `--bundle`; `inAppPurchaseVersion` items; fail if an IAP is not ready | additive; default behaviour unchanged for the other 30+ apps |
| `signing_setup.py` | `--bundle` (default `prefix.slug`) | additive |
| `asc_consumables.py` | new | new file |
| `rc_consumables.py` | new | new file |
| `asc_iap.py`, `rc_setup.py` | not used for this app | — |
| `asc_keywords.py`, `asc_screenshots.py`, `make_screenshots.py`, `fill_locale_urls.py` | work as they are (they read Appfile / project.yml / slug paths) | — |
| `new_app.sh` | not used | — |

---

## 9. What needs the phone (not available now)

1. **Sandbox purchase on the iPhone 15.** Use a Release-signed dev build or a TestFlight build. Never real money: the sandbox charges
   nothing.
   - Buy the Special Offer and one coin pack. Check: the grant arrives once; the Special Offer card disappears; a kill during the
     purchase sheet leads to a grant on relaunch (`Transaction.unfinished`).
   - The RC API shows the transactions on the anonymous customer.
   - Needs **either** a sandbox tester created by the owner in ASC (Users and Access → Sandbox; Region Turkey), signed in under Settings →
     Developer → Sandbox Apple Account, **or** TestFlight internal testing with an ASC user's Apple ID (TestFlight purchases are free).
2. **Local currency on device.** With a TR-region sandbox account the Shop shows "₺…" prices equal to the TRY column. Look at the
   longest tile ("4.999,99 TL"-class) for fit.
3. **Look at the More Lives popup** after the ad row is removed (item 9), on the device, side by side with the Booster Buy popup.
4. **The 2FA code for R1** may arrive on the owner's phone. That is the owner's action, not ours.
5. The owner's acceptance of the release candidate (install over the existing build, keep progress: owner 09-27).

---

## 10. Decisions for the owner

1. **Seed and store name.** Recommended: A, seed `arrow out`, name "Arrow Out: Arrow Escape Puzzle"; alternatives B and C in §6.2.
   Subtitle "Tap Away, Beat the Clock". Keywords as in §6.3. Veto "tap away" if you consider it someone's brand.
2. **13 locales, not 10.** The 2026-09-12 rule added pl/sk/sl; ruling 37 already says 13. Confirm.
3. **iPhone-only 1.0 or universal?**
   - v552 is universal (it ships iPad screenshots, **VERIFIED** research/store/ipad-*.png).
   - Memory `ipad-is-a-review-device` says ship universal, because Apple reviews iPhone apps on an iPad.
   - Universal costs an iPad layout pass, all four iPad orientations in the plist, and 13 × 5 iPad screenshots.
   - Recommended: **iPhone-only 1.0 with a compatibility-mode audit on an iPad simulator** (the layout must hold at the compat-mode
     size), and universal in 1.1.
4. **China mainland.** Exclude it: no Game Registration Number (§7). Recommended: exclude.
5. **"90% OFF" badge on the Special Offer.** 1:1 with v552, but nothing in the shop makes it true: the same 1,000 coins cost $1.99 as a coin pack, so
   the offer is about 50 % off on coins (more counting the boosters and lives), not a documented 90 %. That is an honesty risk under EU
   price-reduction rules.
   - Recommended: replace it with "ONE-TIME" or "STARTER", or keep 1:1 if you accept the risk.
6. **Restore Purchases button.** The factory gate requires one, but every product is consumable and nothing is restorable (Apple does
   not require restore for consumables). Recommended: no button, and the review note explains why.
7. **Review note sentence** "Leaderboards and events run entirely on the device". It is not public, it is true, and it pre-empts a
   5.1.1/2.1 question about player data. It does not say "simulated". Recommended: include it.
8. **Price list.** Keep v552's 12 products and USD points. Apple's automatic prices then reproduce v552's local prices (**VERIFIED**
   for TRY). Confirm, or name the changes.
9. **Purchased coins do not survive a reinstall** (local save, consumables). Accept this (standard for offline games; add one line to
   the support page), or ask for an iCloud key-value backup of the save. That is Apple's service, not a server we run.

---

## 11. Open issues and risks

- **P0, Release sells for free today** (FakeStore in Release). §2.5 S-1…S-3.
- **P0, no `PrivacyInfo.xcprivacy`.** The upload is likely rejected (ITMS-91053) because the app uses UserDefaults and systemUptime.
  §2.5 S-5.
- **P0, the Apple web session has expired** (2026-09-20). R1 needs the owner.
- **P0, no RevenueCat SDK** in project.yml (an orchestrator change). **No consumable tooling** in the factory (§2.3, §2.4, §8).
- **P0 for ja/ko/zh-Hans: the display font has no CJK glyphs** (§5.2 step 5).
- **The app icon is a placeholder** (4.5 KB). Item 11 must land before R7 (memory `never-ship-stand-in-content`).
- **Name risk.**
  - "Arrow Out" is shared by about 15 live titles, and a close brand ("Arrow Out Puzzle", 13k ratings) exists.
  - The name pattern Maze Out! → Arrow Out, combined with 1:1 rules and flows, gives Grand Games grounds for an App Store content
    dispute, or a reviewer grounds for a 4.1 copycat reading. The art/palette/character originality work (items 1, 15) is the
    mitigation.
  - One line per memory `no-clone-apps`: `apps/arrows` (a parked copy of Lessmore's "Arrows", **VERIFIED** not on ASC) must never
    ship on this account next to Arrow Out: that would be two arrow-escape puzzles, a 4.3 spam risk.
- **INFERRED, to confirm on the first run:**
  - IAP localization limits 35/55;
  - v1 vs v2 IAP localization endpoint;
  - RC product `type: consumable`;
  - RC `recordPurchase(_:)` at the pinned version;
  - that `inAppPurchaseVersion` items are accepted together with the version on a brand-new app (the spec lists the relationship;
    Apple's first-IAP rule suggests it is the intended path).
- **The in-app Privacy text** must mention RevenueCat once it ships (S-7). **The hosted support page** answers only subscription
  questions; a consumables FAQ line is optional.
- **The Apple-silicon Mac availability of the iOS app** is not in the public API (only the web UI). It defaults to available (INFERRED).
  A portrait touch game in a Mac window is acceptable but unpolished; the owner can switch it off in the web UI, which is outside our
  browser rules.
- **An equalisation quirk:** in euro storefronts the Mega Bundle and the 50,000-coin pack cost the same (€59.99), from Apple's grid.
  The original has it too.
- **Locale fit:** DE/PL/FR strings may overflow ribbons measured for EN/TR. The fit sweep (§5.2 step 4) may push some rows to shorter
  phrasings.
- `EconomyRules.rewardedAd` removal changes PathCore (not frozen). The orchestrator approves it with the fixture change in the same
  commit (§4.2).
