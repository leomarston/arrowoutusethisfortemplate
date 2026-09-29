---
name: support-mail-button
description: "Every factory app must have an in-app Contact Support button that opens the user's default mail app to anycodeapps@gmail.com"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

The user requires (2026-07-23) that **every app from now on** has an in-app **Contact Support** button in Settings that opens the user's chosen/default mail app addressed to **anycodeapps@gmail.com**.

**Why:** users need a direct support channel; it also helps App Review (a reachable support contact) and reduces bad reviews (people email instead of 1-starring).

**How to apply:** baked into the **template** — `Config.supportEmail = "anycodeapps@gmail.com"` + `Config.supportMailURL` (a `mailto:` URL with the app name/version/OS pre-filled in subject+body), and a "Help" section in `template/App/Settings/SettingsView.swift` with a `Contact Support` row (accessibilityIdentifier `settings.support`). New apps get it automatically via `new_app.sh`; if a per-app SettingsView is rewritten, KEEP the Help/Contact Support section. Applied retroactively to **bluetoothmic** (the last submitted app) and resubmitted. NOT retroactively added to pomodoro/wifispeed/reco unless the user asks. Use a `mailto:` link (not a hardcoded Mail.app deep link) so it honors the user's default mail app. Related: [[app-price-schedule-required]], [[copyright-and-five-screenshots]].
