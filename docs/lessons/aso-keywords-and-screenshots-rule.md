---
name: aso-keywords-and-screenshots-rule
description: "HARD RULE — keywords must be long-tail with the seed keyword first, and the 5 screenshots must use those keywords in order"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

**HARD ASO RULE. Never skip this on any app.**

1. **Keywords must be LONG-TAIL PHRASES, not generic single words.** Never ship lists like `kitten,laser pointer,catnip,pet,interactive,feline,paw,hunt,claw,bird,bug,fun` — that is exactly the junk the user rejected.
2. **The FIRST keyword must be the app's SEED KEYWORD verbatim** — the same phrase the store name leads with. For "Game For Cats - Kitz" the first keyword is `game for cats`.
3. **The remaining keywords are long-tail variants** — multi-word search phrases a real person types, each one relevant to the app's actual features.
4. **The 5 App Store screenshots must use the keywords IN ORDER — screenshot N shows keyword N.** Screenshot 1 = keyword 1 (the seed), screenshot 2 = keyword 2, etc.
4b. **ONLY THE KEYWORD IS WRITTEN ON THE IMAGE — no subline, no tagline, no extra copy of any kind.** Just the keyword phrase (title-cased), centered near the top. `make_screenshots.py` now ignores `subline` entirely; caption JSONs keep `"subline": ""`.
5. Keywords field is **max 100 characters**, comma-separated, no space after commas (spaces waste characters).

**Why:** the user's ASO strategy is keyword-first — the store name, the keyword field and the screenshot captions all have to reinforce the same ranked phrases. Generic one-word keywords rank for nothing, and screenshots that don't echo the keywords waste the strongest conversion surface.

**How to apply:** derive keywords from `ideas.yaml` `seed_keyword` + the app's real features → write captions in `apps/<slug>/design/captions/en-US.json` in the SAME ORDER → regenerate with `scripts/make_screenshots.py` → upload. Set the keywords field via a targeted PATCH to `/v1/appStoreVersionLocalizations/{id}` (see [[keywords-are-user-owned]] — that rule was about never CLOBBERING user-tuned keywords; this rule defines what we write when we do set them, and the user has explicitly ordered this structure).

Applies to EVERY app, including ones already submitted — go back and fix them.

**Audit done 2026-08-01 across all 9 submitted apps.** pomodoro / wifispeed / partylights / teleprompter / bluetoothmic were already compliant (their captions ARE the keyword list in order — that's the pattern to copy). procam / vincam / kitz were broken (generic one-word keywords, captions unrelated) — fixed: keywords rewritten seed-first + long-tail, captions rewritten to contain keyword N in shot N, screenshots regenerated, all 3 resubmitted. Caption JSONs are now checked in at `apps/<slug>/design/captions/en-US.json` for every app so this stays auditable.

**2026-08-02 pass:** stripped ALL sublines so every image carries only its keyword; regenerated + reuploaded + resubmitted 7 apps (kitz, procam, vincam, pomodoro, wifispeed, teleprompter, bluetoothmic) — all verified WAITING_FOR_REVIEW with 5 shots and the seed keyword first. **partylights is BLOCKED:** its ASC record has NO iOS version at all — only a `MAC_OS` version (with `01_mac.png` APP_DESKTOP screenshots), and it is not on the store. `fastlane upload_shots` fails there with "Failed verification of all screenshots deleted". Needs the user to decide (recreate the iOS version / fix the app record).

**Mechanics learned:** screenshots CANNOT be replaced while the version is WAITING_FOR_REVIEW → cancel the reviewSubmission (async; wait for state `DEVELOPER_REJECTED`), run `fastlane upload_shots` (screenshot-only, cannot touch metadata/keywords), then `scripts/asc_submit.py`. The `upload_shots` lane was missing `precheck_include_in_app_purchases: false` and failed with "Precheck cannot check In-app purchases with the App Store Connect API Key" — added to every app + `template/fastlane/Fastfile`. Keywords are set with a targeted PATCH to `/v1/appStoreVersionLocalizations/{id}` (ASK THE USER FIRST — see [[keywords-are-user-owned]]; they rejected an unapproved write).
