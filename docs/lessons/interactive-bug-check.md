---
name: interactive-bug-check
description: "After building every app, run a real interactive bug check of every feature and button in the simulator before submit"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

After building each app — and before submitting — run a genuine **interactive bug check of every feature and every button** in the newest iPhone Pro simulator, not just a screenshot pass.

**Why:** The user caught a paywall bug (the Yearly plan card wasn't tappable) that a screenshot-only check missed. They want real interaction exercised each build.

**How to apply (automated harness — built 2026-07-22):** run `python3 scripts/bug_check.py --slug <slug>`. It runs an **XCUITest** suite (`apps/<slug>/UITests/FactoryUITests.swift`) on the newest iPhone Pro sim in **light + dark** with real taps, and exits 1 on any failure (gates submit). The reusable base (in `template/UITests/`) tests the universal contract — paywall (both plan cards selectable, delayed X appears + dismisses, Restore) and Settings (Restore + Upgrade→paywall). **Per app you MUST add** the onboarding→home test (matching that app's flow) and the core-feature tests, giving feature buttons accessibility identifiers and filling the stubs.

Mechanics that make it work: standard accessibility IDs live in the template's common views (`onboarding.primary`, `home.settings`, `paywall.plan.weekly`/`.yearly`, `paywall.cta`, `paywall.restore`, `paywall.close`); the `-DemoPaywall` launch arg renders the paywall with the factory's standard prices so the test is deterministic (StoreKit config isn't applied via `simctl`/xcodebuild-test reliably, and network offerings are flaky); `-ForceOnboarding` resets `hasOnboarded` (doesn't pin it) so the onboarding button can advance; the UI test target + scheme test action are in `project.yml`. `simctl` alone can't tap — that's why XCUITest, not a screenshot pass. Pomodoro's suite (5 tests) passes green.

Note: the `-DemoPaywall` capture route renders the paywall with real prices in the sim (StoreKit config isn't applied via `simctl launch`, so the real paywall shows "could not load plans" there) — keep those demo cards interactive so plan selection is testable.
