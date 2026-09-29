---
name: camera-and-payment-testing
description: How to build/verify camera apps and payments when the Simulator has no camera and RC+StoreKit-Testing is flaky
metadata: 
  node_type: memory
  type: project
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

Learned shipping Tail (teleprompter, 2026-07-27):

- **The iOS Simulator has NO camera.** For camera apps, make the capture screen degrade gracefully (show a clean placeholder/gradient when `AVCaptureDevice.default(...)` is nil, gated by `#if targetEnvironment(simulator)` or an `isAvailable` flag) so screenshots + bug_check work on non-camera surfaces. The real capture code (AVCaptureSession + AVCaptureMovieFileOutput → PHPhotoLibrary) is verified by review + on-device, not in the sim. Needs `NSCameraUsageDescription` + `NSMicrophoneUsageDescription` + `NSPhotoLibraryAddUsageDescription` in project.yml.
- **Testing payments in the sim:** a `.storekit` config wired via xcodegen `schemes.<X>.run.storeKitConfiguration` lets StoreKit serve products locally, BUT RevenueCat's `offerings()` frequently THROWS under sim StoreKit-Testing ("Could not load plans"), so a full in-sim purchase test is unreliable — don't block submit on it. Instead VERIFY THE CONNECTION via the RC v2 API (RC_SECRET_KEY + RC_PROJECT_ID): confirm the offering has packages wired to active products with the right `store_identifier` and the entitlement exists. That + `rc_setup.py` green + the `-DemoPaywall` bug_check tests = sufficient "payments connected"; the real charge is validated in sandbox/Apple review (proven by the live apps). Keep the paywall/bug_check on `-DemoPaywall` (hardcoded prices, no network) for reliable green gates.
- **ultracode multi-agent review is high-value before submit.** A 4-dimension review (correctness / App-Store-rejection-risk / payments / design) with adversarial verification caught REAL rejection blockers on Tail: the paywall + description advertised "custom color, fonts, themes" that didn't exist and text-size was free → 2.3.1 metadata-mismatch rejection. Fix pattern: either implement the advertised feature for real (I added a Pro text-color picker, gated on RENDER not just the toggle) or delete the claim from BOTH PaywallView benefits and description.txt. It also caught a dead upsell (a paywall set on HomeView can't present over an active `fullScreenCover` — present it from within the covering view via local `@State`).

Related: [[signing-submit-gotchas]], [[interactive-bug-check]], [[revenuecat-asc-key-required]].
