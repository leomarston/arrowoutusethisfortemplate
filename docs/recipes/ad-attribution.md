# Recipe: adding an ad-attribution SDK to one game

The template ships **no** ad, attribution or tracking SDK (docs/ROADMAP.md D2). When a game runs app-install ads and wants
to measure them (Meta, AppsFlyer, …), add the SDK **to that game only**, from zero, following this checklist. Arrow Out 1.0
shipped with Meta's FacebookCore 18.1.1; that complete, reviewed wiring is on `main` at commit `0f0ef7e`
(`git show 0f0ef7e:<path>`) and is the reference:

| What | Where it was in Arrow Out 1.0 (`0f0ef7e`) |
|---|---|
| SDK adapter, event mapping, live/log-only modes, ATT prompt timing | `apps/mazeout/App/Support/MetaAds.swift` |
| Package + Info.plist keys + token build phases | `apps/mazeout/project.yml` (packages, `info.properties`, pre/postBuildScripts) |
| Client token only in `.env` and the BUILT Info.plist | `apps/mazeout/tools/meta_token.py` |
| Dashboard flags check before a store build | `apps/mazeout/tools/meta_dashboard_check.py` |
| Release gate 8 + string attribution | `apps/mazeout/tools/bench/meta_sdk_check.py`, `release_gates.sh` |
| Privacy manifest, App Privacy label, in-game privacy text, ATT purpose string (13 languages) | `App/PrivacyInfo.xcprivacy`, `fastlane/metadata/app_privacy_details.json`, `App/Shell/Popups/SettingsPopup.swift`, `App/Resources/Strings/infoplist.tsv` |
| Tests | `Tests/AppTests/MetaEventsTests.swift`, `MetaSDKLinkageTests.swift`, `UITests/TrackingPromptUITests.swift` |

## Checklist
1. **Decide and write it down** in the game's plan: which SDK, which events (install, purchase, tutorial, level), whether
   the IDFA is used (then an ATT prompt is required). Never an ad-SERVING SDK unless the game truly shows ads.
2. **Package:** add it to `project.yml` pinned with `exactVersion`, only the product you need.
3. **Adapter:** implement `PurchaseReporting` (`App/Support/Attribution.swift`) and pass it as StoreService's `reporter`
   (`App/Shell/Shop/StoreService.swift`); report only `.production` money as revenue. Add a `GameDirector` for level
   events. Live only in a Release run on a device; simulators, tests and Measure builds must only log.
4. **Secrets:** the SDK's client token goes in `.env` and the BUILT Info.plist only (copy the `meta_token.py` pattern);
   never a tracked file, never a build setting; add its key to the Fastfile's `BUILD_SECRET_KEYS`.
5. **ATT:** one prompt, after the tutorial, on a calm screen, never over a popup; IDFA collection only when authorised.
   Add the `NSUserTrackingUsageDescription` row to `App/Resources/Strings/infoplist.tsv` in all 13 languages.
6. **Privacy, all four together:** `PrivacyInfo.xcprivacy` (tracking true + EXACTLY the SDK's tracking domain; an empty list
   is ITMS-91064), the App Privacy label JSON, the in-game privacy page (say what is sent and how to turn it off), and the
   public privacy policy page. Update `Tests/AppTests/ContractAmend4Tests.swift`'s pins.
7. **Gates:** `ALLOWED_FRAMEWORKS="…" tools/bench/release_gates.sh …` for gate 8; attribute the SDK's own strings in gates
   2 / 2b / 7 / 7c (FB_JSON in `release_gates.sh`).
8. **Submission:** `python3 scripts/asc_submit.py --slug <slug> --bundle <bundle> --uses-idfa` (deliver ignores every
   `add_id_info_*` key; without `usesIdfa=true` Apple marks the build INVALID_BINARY with no reason). Watch the version
   for 15+ minutes. Tell App Review in the notes when and where the ATT prompt appears.

## Lessons already paid for
`docs/lessons/meta-ads-sdk.md`, `meta-sdk-wiring.md`, `idfa-declaration-and-invalid-binary.md`,
`att-prompt-is-one-shot-too.md`.
