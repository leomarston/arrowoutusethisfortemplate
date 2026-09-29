# Lessons (hard-won pitfalls)

These are the notes Claude kept while the factory shipped ~30 iOS apps and the Arrow Out game (July to September 2026):
each one is a mistake that already cost time, a rejection, or money once, and the rule that prevents it. They were
Claude Code's auto-memory for the factory repo (`~/.claude/projects/-Users-yago-Downloads-app-factory/memory/`), copied here
so they travel with the template.

How to use them:
- Before a phase, read its group below (signing before the first archive, localisation before strings, and so on).
- Newer rules win. Where two notes disagree, the later date wins; the superseded ones say so (e.g. the 50-locale and
  10-locale rules are replaced by `localize-top-13-locales.md`).
- `[[some-name]]` inside a note points at `some-name.md` in this folder. A few point at per-app notes of the factory's
  utility apps (camdetect, twocam, noisemeter, hearup, ...); those notes were left out of this repo on purpose because
  they only described that app's state, and their general rules have their own files here.
- Several notes name the factory's own apps, bundle ids, the owner's accounts and absolute paths
  (`/Users/yago/Downloads/app-factory`). Read those as examples; the rules are what matters.
- `MEMORY.md` is the original flat index in Claude Code's auto-memory format (only the lines for files kept here). To give a
  new machine's Claude the same memory, copy this folder's `.md` files into
  `~/.claude/projects/<the repo path with / replaced by ->/memory/` (optional; this README works without it).

Arrow Out's own decisions and history are not here: they are in `apps/mazeout/PLAN.md`, `apps/mazeout/SPEC.md` and
`apps/mazeout/design/publish/release-plan.md`.

## Store & submission (App Store Connect, fastlane, review rules)

- [apple-session-30-days.md](apple-session-30-days.md) — create_app/upload_privacy need a web session; 30 days is the MAX (one died in 2 days, 09-30); check_session right before, ask for spaceauth early
- [app-privacy-needs-apple-id.md](app-privacy-needs-apple-id.md) — data usages aren't in the public ASC API; SKIP_PRIVACY leaves a NEW app unsubmittable
- [app-price-schedule-required.md](app-price-schedule-required.md) — submit needs a VALID free app price schedule; an empty/invalid one returns GET 200 and got skipped → APP_PRICING_REQUIRED 409; asc_submit.py now always (re)sets it + attach build to version first
- [new-app-needs-keywords.md](new-app-needs-keywords.md) — a first version wont submit with empty keywords; PATCH it, never create keywords.txt
- [asc-subscription-submission.md](asc-subscription-submission.md) — first-version + new sub group needs version + subscriptionGroupVersion + subscriptionVersion items in ONE review submission; scripts/asc_submit.py
- [asc-version-platform-filter.md](asc-version-platform-filter.md) — a stray macOS version record breaks submit; filter by platform and read `platform` before renaming
- [asc-token-20min-cap.md](asc-token-20min-cap.md) — deliver can't finish a 50-locale screenshot upload; PATCH whatsNew directly for notes-only changes
- [build-lag-never-bump.md](build-lag-never-bump.md) — /v1/builds lags after upload; "cfBundleVersion already used" PROVES the upload worked — wait, don't bump
- [altool-checksum-wedge.md](altool-checksum-wedge.md) — altool can retry one part forever; kill it and re-upload the same IPA instead of waiting or re-archiving
- [resubmit-update-checklist.md](resubmit-update-checklist.md) — updates need a new version record + a signing refresh; the builds API is not date-ordered
- [ipad-is-a-review-device.md](ipad-is-a-review-device.md) — Apple reviews iPhone-only apps ON an iPad; ship universal + audit there before submit
- [ipad-needs-all-four-orientations.md](ipad-needs-all-four-orientations.md) — a universal app is rejected 409 at upload unless the iPad key lists all four
- [empty-env-var-is-truthy.md](empty-env-var-is-truthy.md) — SKIP_PRIVACY= still skips; new app then blocked by APP_DATA_USAGES_REQUIRED
- [permission-button-must-not-direct.md](permission-button-must-not-direct.md) — HARD: use Continue/Next, never "Allow X access"; 5.1.1(iv) rejected storagecleaner build 8
- [vpn-word-triggers-rejection.md](vpn-word-triggers-rejection.md) — 2.1.0 "VPN functionality" from the WORD in honesty copy; prove the negative with otool/entitlements/PlugIns, then delete the word

## Signing

- [signing-submit-gotchas.md](signing-submit-gotchas.md) — Faz 11: codesign needs set-key-partition-list (else errSecInternalComponent); asc_submit auto-attaches build + deletes stale-submission items; sub review screenshot required; create_app needs NO session
- [signing-keychain-shadowing.md](signing-keychain-shadowing.md) — errSecInternalComponent = a 2nd keychain with a duplicate cert winning the search list; fixed in signing_setup.py
- [signing-keychain-relocks.md](signing-keychain-relocks.md) — errSecInternalComponent at EXPORT = locked keychain; unlock inside the lane

## Payments (RevenueCat, StoreKit, paywalls, pricing)

- [revenuecat-one-project.md](revenuecat-one-project.md) — factory uses ONE RC project for all apps by user's choice; RC can't create projects via API anyway
- [revenuecat-asc-key-required.md](revenuecat-asc-key-required.md) — RC needs the ASC In-App Purchase Key per app or offerings are empty; rc_setup.py now automates it
- [revenuecat-cancel-does-not-throw.md](revenuecat-cancel-does-not-throw.md) — StoreKit 2 cancellation RETURNS with userCancelled=true; caused a 2.1(b) rejection
- [camera-and-payment-testing.md](camera-and-payment-testing.md) — sim has no camera (graceful placeholder + on-device only); RC offerings() throws under sim StoreKit-Testing so verify payments via RC API not in-sim purchase; ultracode review catches real 2.3.1 rejection blockers (advertised features must exist)
- [submit-without-subscriptions.md](submit-without-subscriptions.md) — post-cancel sub states lag; asc_submit could ship an app with an empty paywall (fixed + verify after every submit)
- [trial-claim-vs-config-drift.md](trial-claim-vs-config-drift.md) — a missing weekly_trial_days ships a listing promising a trial that does not exist; offers are per-territory (expect 175)
- [subscription-grace-period.md](subscription-grace-period.md) — every app gets a 3-day billing grace period (prod + sandbox); automated in asc_iap.py
- [standard-price-3-99-17-99.md](standard-price-3-99-17-99.md) — HARD default 3.99wk/17.99yr; storagecleaner is a deliberate exception at the leader's 7.99/29.99 + 7d annual trial
- [paywall-billed-amount-dominant.md](paywall-billed-amount-dominant.md) — 3.1.2: price must out-shout the trial + per-week maths; fixed template + 4 apps 2026-08-21
- [no-free-trial-toggle.md](no-free-trial-toggle.md) — Apple 3.1.2(c) rejected bracketmaker for a trial on/off switch; template fixed, plan cards state their own terms
- [free-tier-copies-the-leader.md](free-tier-copies-the-leader.md) — copycat the PAYWALL SHAPE too; in cleaners the delete button is the product they sell
- [pair-free-press-paid.md](pair-free-press-paid.md) — tvremote's free tier: pairing one TV is free, every command is Pro; one gate, and rewrite every 'buttons are free' claim
- [monetisation-change-is-a-copy-change.md](monetisation-change-is-a-copy-change.md) — a new gate falsifies store copy in every locale; budget chars first, most have <40 free

## Meta ads SDK (install attribution, ATT, IDFA)

- [meta-ads-sdk.md](meta-ads-sdk.md) — built opt-in per app; blocked on a Meta App ID + Client Token and a Page on the ad account
- [meta-sdk-wiring.md](meta-sdk-wiring.md) — the ep1.facebook.com tracking-domain trap, proving the SDK is really linked, and the copy it makes false
- [idfa-declaration-and-invalid-binary.md](idfa-declaration-and-invalid-binary.md) — an ad SDK needs usesIdfa=true; detach/re-attach the build to clear the stuck state
- [att-prompt-is-one-shot-too.md](att-prompt-is-one-shot-too.md) — never assert the ATT alert appears; an earlier test in the run consumes it

## Localisation

- [localize-top-13-locales.md](localize-top-13-locales.md) — HARD RULE (2026-09-12): the 10 plus pl/sk/sl-SI; store uses sl-SI but .lproj is sl
- [localize-top-10-locales.md](localize-top-10-locales.md) — HARD RULE (2026-09-05): top 10 App Store locales only, done properly; SUPERSEDES the 50-locale rule
- [localize-all-50-locales.md](localize-all-50-locales.md) — SUPERSEDED by [[localize-top-10-locales]]; kept for history
- [localizedstringkey-not-string.md](localizedstringkey-not-string.md) — helpers typed `String` silently skip the strings table; labels must be LocalizedStringKey
- [localization-extractor-hides-single-words.md](localization-extractor-hides-single-words.md) — "week"/"day" look like identifiers, so the paywall price suffix ships untranslated
- [strings-escape-decode.md](strings-escape-decode.md) — extract.py must decode Swift escapes or multi-line strings ship untranslated everywhere
- [reordered-args-need-positional.md](reordered-args-need-positional.md) — a translation that reorders %@/%lld must use %1$@ or Swift prints the wrong value; check ORDER not the set
- [locale-urls-before-the-length-check.md](locale-urls-before-the-length-check.md) — one over-long subtitle cost a locale both URLs and 409'd the submit

## Screenshots & ASO

- [aso-keywords-and-screenshots-rule.md](aso-keywords-and-screenshots-rule.md) — HARD RULE: long-tail keywords, seed keyword first, 5 screenshots use them in order
- [app-naming-keyword-first.md](app-naming-keyword-first.md) — store name MUST start with the exact seed keyword verbatim (incl. 'app'); never drop/reorder
- [keywords-are-user-owned.md](keywords-are-user-owned.md) — NEVER upload the App Store keywords field; sync it down from ASC, never up
- [never-touch-keywords-or-description.md](never-touch-keywords-or-description.md) — HARD: both are tuned ranking assets on a live app; ask before changing a single word
- [template-scaffolds-empty-keywords-txt.md](template-scaffolds-empty-keywords-txt.md) — deliver would upload it and wipe researched keywords
- [copyright-and-five-screenshots.md](copyright-and-five-screenshots.md) — copyright is '2026 Manycode Apps'; exactly 5 screenshots, dedup any extras
- [screenshots-verify-content-not-count.md](screenshots-verify-content-not-count.md) — a blank launch-screen frame shipped to 50 storefronts; look at the pixels
- [deliver-cannot-upload-screenshots.md](deliver-cannot-upload-screenshots.md) — SSL_read errors on every call; use scripts/asc_screenshots.py + split lanes
- [deliver-force-appends-screenshots.md](deliver-force-appends-screenshots.md) — a redesign leaves 10 per set; dedupe on ASC by fileSize and assert 5/5
- [ipad-capture-gotchas.md](ipad-capture-gotchas.md) — screenshot size is in points, iOS 26 tab bar is Cells, sim needs its own locale
- [capture-doubles-neutral-identity.md](capture-doubles-neutral-identity.md) — App Store shots must not show 127.0.0.1, a test port or a real model string; LAN + real ports + control-endpoint override
- [fixture-photography.md](fixture-photography.md) — store frames need CC0 photos of PEOPLE from Openverse at 4032px; and ls order != Python sorted order

## Simulator & phone

- [simctl-launch-args-gotcha.md](simctl-launch-args-gotcha.md) — simctl launch drops args if app already running; cold-start/two-step for captures
- [simctl-photos-grant-is-a-lie.md](simctl-photos-grant-is-a-lie.md) — it sets TCC but PhotoKit stays undetermined; tap the alert in XCUITest once, or copy the auth_reason=2 row to another sim
- [simulator-inherits-mac-region.md](simulator-inherits-mac-region.md) — en_TR put comma decimals into en-US screenshots
- [permission-prompt-is-one-shot.md](permission-prompt-is-one-shot.md) — a killed test run consumes it; uninstall before re-running or no alert ever appears
- [parallel-agents-and-simulators.md](parallel-agents-and-simulators.md) — delegating long multi-app work is welcome, but give each side its own simulator or captures get the wrong app
- [phone-driver.md](phone-driver.md) — tools/phonedriver controls the owner's USB iPhone 15 (tap/swipe/shot/launch); needs Dev Mode + UI Automation + Auto-Lock Never
- [device-install-can-wipe-save.md](device-install-can-wipe-save.md) — devicectl install over a dev build gave a fresh container (owner progress lost 09-28); back up the save, verify, restore

## Disk & machine

- [disk-full-lies.md](disk-full-lies.md) — a full disk surfaces as codesign/gym errors that never mention space; df -h first
- [disk-fills-fast-clean-archives.md](disk-fills-fast-clean-archives.md) — sims, Archives, sim Dead copies, xctrace temp; runaway RAM hides in compressed memory (use top MEM); other apps' caches only harmless parts
- [max-two-parallel-builds.md](max-two-parallel-builds.md) — 5 build agents + 3 sims on this 16 GB Mac = 17 GB swap, all stalled, disk full; cap build agents at 2
- [app-factory-setup-state.md](app-factory-setup-state.md) — .env filled + all creds validated live (2026-07-15); only building apps left

## Game-specific (GAMEPROMPT, Arrow Out)

- [gameprompt.md](gameprompt.md) — reusable "make a 1:1 puzzle game on your own" manual (+ GAMEPROMPTMAX.md for /effort max, subagents); on build/matchfactory; phone rules in settings.local.json
- [kitz-build-state.md](kitz-build-state.md) — Game For Cats SpriteKit prey-hunt; aggressive monetization; competitor-matched real SVG art
- [svg-art-pipeline.md](svg-art-pipeline.md) — real crafted art: study competitor screenshots, generate SVG via multi-agent, rasterize with scripts/svg2png.swift (WebKit)

## SwiftUI, Xcode & testing gotchas

- [appstorage-in-observableobject.md](appstorage-in-observableobject.md) — no objectWillChange; app could stick on onboarding (fixed template + all apps)
- [appstorage-raw-write-gotcha.md](appstorage-raw-write-gotcha.md) — raw UserDefaults.set is invisible to a cached @AppStorage; broke kitz -ForceOnboarding tests (+ sim prefs survive uninstall)
- [swiftui-greedy-scaledtofill-gotcha.md](swiftui-greedy-scaledtofill-gotcha.md) — a scaledToFill image inside a .background view breaks whole-screen layout
- [swiftui-container-identifier-swallows-children.md](swiftui-container-identifier-swallows-children.md) — a bare .accessibilityIdentifier on a container overwrites every child's identifier
- [swiftui-navigation-and-funnel-traps.md](swiftui-navigation-and-funnel-traps.md) — a dropped NavigationStack push, a paywall wedged by a stale screen enum, order-dependent UI tests
- [swiftui-no-a11y-tree-in-unit-tests.md](swiftui-no-a11y-tree-in-unit-tests.md) — SwiftUI exposes 0 identifiers in a unit-test host; measure pixels, and mount in a scene for animations
- [xcuitest-hittable-lies.md](xcuitest-hittable-lies.md) — an element under a safeAreaInset bar reports hittable; dump debugDescription instead of guessing
- [xcuitest-predicates-must-anchor.md](xcuitest-predicates-must-anchor.md) — a loose CONTAINS matches the app's own copy, so the test goes green asserting nothing
- [env-dependent-tests-assert-all-outcomes.md](env-dependent-tests-assert-all-outcomes.md) — assert every honest terminal state, or it passes in dark and fails in light
- [test-delete-alert-wedges-suite.md](test-delete-alert-wedges-suite.md) — deleteAssets raises a springboard alert no test can answer; the run hangs silently
- [interactive-bug-check.md](interactive-bug-check.md) — after every build, really tap through every feature/button in the sim (not just screenshots) before submit
- [infoplist-array-keys-need-a-base-plist.md](infoplist-array-keys-need-a-base-plist.md) — INFOPLIST_KEY_UIBackgroundModes is silently dropped
- [audio-apps-must-assert-on-signal.md](audio-apps-must-assert-on-signal.md) — a screenshot can't prove an audio app makes sound; test the measured output level
- [camera-device-only-bug-classes.md](camera-device-only-bug-classes.md) — 5 failure classes the Simulator can never catch; audit every AVFoundation app against them
- [coreimage-noise-and-cube-traps.md](coreimage-noise-and-cube-traps.md) — CIRandomGenerator randomises ALPHA and a .cube needs CIColorCubeWithColorSpace; both silently wreck the picture

## Honesty, product & design rules

- [verify-real-not-mock.md](verify-real-not-mock.md) — before submit run the REAL path and prove Release contains no demo data; watch for inflated counts too
- [never-ship-stand-in-content.md](never-ship-stand-in-content.md) — HARD: a bundled photo/fake meter for live sensor data must be simulator-gated; twocam shipped a JPEG as the camera
- [honesty-copy-no-vendor-impossibility.md](honesty-copy-no-vendor-impossibility.md) — never claim another company's protocol makes something impossible; it goes false when you build it
- [no-network-claim-is-false.md](no-network-claim-is-false.md) — RevenueCat's subscription check IS a network call; never say "no network at all"
- [no-clone-apps.md](no-clone-apps.md) — screen every new idea vs shipped/queued apps for Apple 4.3 spam/clone risk BEFORE building; flag overlap; user "do it" overrides
- [copycat-the-category.md](copycat-the-category.md) — HARD: in a crowded category, copy the leaders' UI/colour/icon conventions; measure their pixels, don't eyeball
- [distinctive-ui-not-slop.md](distinctive-ui-not-slop.md) — default grey-SwiftUI look reads as "AI slop"; give each app a subject-specific identity (custom palette/type + one signature) via the frontend-design skill; redesign before submit
- [support-mail-button.md](support-mail-button.md) — every app needs an in-app Contact Support button (Settings) opening mailto anycodeapps@gmail.com; baked into template
- [no-servers-not-no-libraries.md](no-servers-not-no-libraries.md) — user's rule is no backend to run; bundled offline client libs (e.g. LAME) are fine

## Working with the owner (process rules)

- [account-and-no-browser.md](account-and-no-browser.md) — HARD: browser only for Appfigures + Meta ads (never ASC); only the esaridogann@gmail.com Apple/RC account
- [commit-when-work-is-done.md](commit-when-work-is-done.md) — HARD: commit finished work unasked; a dirty tree is not "done"
- [finish-the-whole-pipeline.md](finish-the-whole-pipeline.md) — HARD: build to submitted, never stop at a phase boundary to check in
- [one-app-per-task.md](one-app-per-task.md) — HARD RULE: touch ONLY the app you were asked about; other apps rejected/removed = not your problem
- [daily-routine.md](daily-routine.md) — 5AM-Turkey launchd job builds one ROUTINEAPPS.MD app/day; needs pmset wake + fastlane spaceauth for full autonomy
- [new-app-inherits-template-at-scaffold.md](new-app-inherits-template-at-scaffold.md) — fixing template later does NOT fix already-scaffolded apps; always backport + re-shoot paywall images

## Market research

- [funnel-baseline-2026-09-05.md](funnel-baseline-2026-09-05.md) — measured: 1,023 installs → 4.1% trial → 14% paid → $0.036 proceeds/install; onboarding paywall is the only surface; ASC key 403 on analytics
- [utility-apps-win-on-aso.md](utility-apps-win-on-aso.md) — top-grossing utilities barely touch Meta; $1.67/download vs $2-6 CPI is why
- [ad-library-media-filter.md](ad-library-media-filter.md) — the competitive-research toolkit: Meta static share, CTA histogram, iTunes earnings, Google's ad library, shippable-shape test
- [static-ad-niche-verdict.md](static-ad-niche-verdict.md) — 4 picks rejected, TV remote stands; owner relaxed the 4.3 and no-server rules
- [family-locator-ruled-out.md](family-locator-ruled-out.md) — needs a relay; Find My has no API, CloudKit needs a one-time dashboard token the owner declined; do not rebuild

## Earlier apps: state notes kept for the lessons inside them

- [reco-build-state.md](reco-build-state.md) — Faz 0-6 + icon done on build/reco; blocked on one-time fastlane create_app session auth
- [storagecleaner-build-state.md](storagecleaner-build-state.md) — FreeUp id 6808934868, 1.1.0/build 10 submitted 2026-09-12 with 14 locales; the engine is calibrated, don't disturb it
- [tvremote-build-state.md](tvremote-build-state.md) — Couch build 2 resubmitted 2026-09-07; NINE TV platforms + plain-language UI; first funnel-designed app; protocol doubles instead of hardware
- [mater-build-state.md](mater-build-state.md) — Ruler Measuring Tape: 1:1 Tape Measure copycat submitted 2026-09-09; 4 submit blockers documented; AR unverified on hardware
- [ledbanner-build-state.md](ledbanner-build-state.md) — one texel = one lamp; SwiftUI shader traps + the 4.3 line vs partylights/strobelight/teleprompter
- [vincam-build-state.md](vincam-build-state.md) — vintage point-shoot camera submitted 2026-07-31; distinct from ProCam; halation blur-cap fix
- [rfdetector-build-state.md](rfdetector-build-state.md) — Sweep submitted 2026-08-03; only BLE RSSI + magnetometer + Bonjour, no fake RF claims
- [stopdog-build-state.md](stopdog-build-state.md) — Dog Whistle submitted 2026-08-03; cue-list UX + honesty rewrite (no fake frequency claims)
- [stakeout-and-hd-build-state.md](stakeout-and-hd-build-state.md) — two detector apps shipped 2026-08-26; one sensor each, split on value not hue
- [spinwheel-build-state.md](spinwheel-build-state.md) — sealed-draw picker submitted 2026-09-02; winner chosen FIRST by CSPRNG, wheel animated onto it
- [podfind-build-state.md](podfind-build-state.md) — Earbud Finder submitted 2026-08-29; Apple marks confined to the keyword field
- [whitenoise-build-state.md](whitenoise-build-state.md) — White Noise machine submitted 2026-08-23; synthesised colours + CC0 recordings, near-miss silent-app bug

**Added 2026-09-30:** [arrowout-build-state.md](arrowout-build-state.md) — the Arrow Out submission itself: ids, monetisation, Meta SDK, what is open after approval.
