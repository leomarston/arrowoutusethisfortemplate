---
name: vincam-build-state
description: "VinCam (vintage camera) submitted 2026-07-31 — sibling to ProCam, deliberately distinct to dodge 4.3"
metadata: 
  node_type: memory
  type: project
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

VinCam = "Vintage Camera - VinCam", com.manycode.vincam, ASC app 6796673130, accent #F5731F (date-stamp orange). **SUBMITTED 2026-07-31** (reviewSubmission 0d5ea8c2): version 1.0.0 + weekly($3.99,3d trial) + yearly($17.99) all WAITING_FOR_REVIEW. First-try submit (ProCam learnings applied: pre-set keywords via PATCH since keywords.txt removed per [[keywords-are-user-owned]]; ran asc_review_assets.py for the sub review screenshots BEFORE submit so subs weren't stuck MISSING_METADATA).

**Deliberately distinct from ProCam (anti-4.3, see [[no-clone-apps]]):** ProCam = manual pro instrument (RAW, histograms, sliders, dark cine blue). VinCam = point-and-shoot NOSTALGIA — NO manual controls; you point, press, and the shot "develops" (signature reveal) with grain/halation/date-stamp. Warm analog camera-body UI, orange+Kodak-yellow. Core metaphor = FILM ROLLS (shots organized into rolls, each carrying a film stock), vs ProCam's flat Photos save.

**Premium (all real Core Image/CoreGraphics, sim-testable on demo scene):** Free = point-shoot + develop, Classic & B&W stocks, import, film rolls, save to Photos. Pro = full film pack (10 stocks: sunny70/poolside/disposable/camcorder/expired/noir/golden/faded + free classic/mono), light leaks + halation, film-print/negative export borders, date-stamp styles, unlimited rolls, Face ID private roll.

**Engine files:** FilmStocks.swift (stock recipes + FilmProcessor: mono/temp/sat/contrast/fade/split-tone/halation/vignette/grain/leak). FilmFinish.swift (burned-in orange LCD date stamp + print/negative sprocket borders). FilmRollStore.swift (rolls = Documents/Rolls/<id>/ jpgs + UserDefaults metadata; RollLock biometric). HomeView (viewfinder), DevelopView (reveal), RollsView, ImportEditView, StockStrip. Icon: tools/make_icon.py (PIL vintage camera, no Gemini). Demo scene: tools/make_scene.py (bright beach — distinct from ProCam dusk).

**Bug fixed:** halation blew full-res images to WHITE — its Gaussian blur radius scaled linearly with image size (huge at full res vs tiny in 120px thumbnail). Fix: isolate true highlights (bias -0.6 + CIColorClamp) + CAP blur radius at min(maxDim*0.006, 18). Any size-proportional CI blur needs a cap.

**REDESIGN (2026-07-31, after user "AI slop" feedback ×2):** User rejected both the icon and the flat dark-SwiftUI UI as slop. Redesigned:
- **Icon** → real 35mm film frame (sprocket holes, grainy warm sunset exposure, halation, burned-in orange date stamp). tools/make_icon.py. NOT the flat camera-on-gradient cliché.
- **UI** → TACTILE plastic point-and-shoot (user picked this direction over "bold retro-print"). New App/DesignSystem/Materials.swift: `Mat` palette, `PlasticSurface` (warm gradient + sheen), `recessed()`/`raisedPlastic()` modifiers (inner-shadow/emboss), `ShutterButton` (glossy orange dome), `LCDReadout` (segmented mint counter + ghost 88), `ThumbWheel`. Applied across home/develop/import/rolls/onboarding/paywall/settings. Home = molded body + recessed viewfinder faceplate + film-box stock tabs + glossy shutter + film-advance wheel. Develop = instant-print white mat, tilted, on darkroom bg w/ red safelight.
- **GOTCHAS burned:** (1) greedy `scaledToFill` noise image inside PlasticSurface broke WHOLE-screen layout → see [[swiftui-greedy-scaledtofill-gotcha]]. (2) plastic micro-noise texture read as ugly "snowstorm"/static on large flat bgs (paywall) → removed noise entirely, plastic feel from gradients+shadows only.
- 6/6 interactive tests still pass both modes. Resubmitting build 2 (canceled review submission 0d5ea8c2 → version DEVELOPER_REJECTED → new build + screenshots + asc_submit).

Both ProCam ([[procam-premium-scope]]) and VinCam submitted; ProCam still has the flat UI (user may want same tactile pass later). Remember reco 3.1.2(b) reviewer reply still pending for the user.

**1.0.1 build 7 submitted 2026-09-10** — the film look is LIVE in the finder now (AVCaptureVideoDataOutput into a Metal CIContext running the same recipe as develop), plus pinch zoom, lens stops, front camera and flash. Three engine bugs fixed by measuring: `CIRandomGenerator` randomises ALPHA and colour is premultiplied, so grain BRIGHTENED a frame by up to 164 levels and a full-res photo developed to white while its thumbnail looked fine; `splitTone` used `CIAdditionCompositing` (sums alpha) and Camcorder 90s developed at a tenth of its brightness; dust was sized in pixels, which is what made the vignette look orientation-dependent. Then the grain had to be LOOKED at — a flat 8-octave ladder out to 128px cells is scale-invariant but reads as mould-stained paper, and `grainSD` is blind to a blob that wide. Ladder truncated at 32. 41 tests, 1 failure: 4 of 10 stock thumbnails still mispredict the save. See [[coreimage-noise-and-cube-traps]], [[swiftui-no-a11y-tree-in-unit-tests]].
