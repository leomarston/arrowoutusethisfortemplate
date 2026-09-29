---
name: app-factory-setup-state
description: "Setup state of the app-factory repo — toolchain installed, .env filled + validated, only GEMINI_API_KEY pending"
metadata:
  node_type: memory
  type: project
  originSessionId: 87e7b984-7325-418d-a99f-5b3b60862a71
---

App-factory repo (~/Downloads/app-factory). Toolchain complete (2026-07-02): Xcode 26.0.1 + iOS 26 sims, Homebrew at /opt/homebrew, fastlane 2.236.1 + xcodegen 2.45.4 exposed via exec-wrapper scripts in ~/.local/bin (NOT symlinks — symlinked xcodegen loses SettingPresets), gh CLI authed as `leomarston`, Python deps incl. pillow/pyjwt/cryptography/certifi, both Adam Lyttle skills in ~/.claude/skills, SF Pro fonts, XcodeBuildMCP connected. Note: Python has no system SSL certs — use `certifi.where()` for a CA bundle when making HTTPS calls from scripts.

Account owner: **Emine Sarıdoğan** (Apple ID / account holder: esaridogann@gmail.com). Brand: **Manycode**, bundle prefix **com.manycode**. (NOT Ahmet Yagiz, NOT anycode — those were template placeholders the user corrected.)

**.env now FILLED and each credential VALIDATED LIVE (2026-07-15):**
- Apple: ASC API key (App Manager) validated against api.appstoreconnect.apple.com → HTTP 200. Account is a clean slate (0 apps/bundleIds/certs). APPLE_ID esaridogann@gmail.com was auto-derived from /v1/users (ACCOUNT_HOLDER). TEAM_ID GDU77F3MXL — valid format, could NOT be cross-checked (empty account) so it gets confirmed at first signing. .p8 lives in ~/keys/ (moved out of repo; *.p8 added to .gitignore).
- RevenueCat: secret key validated against api.revenuecat.com/v2/projects → HTTP 200. RC_PROJECT_ID proj5f4f704a MATCHES. NOTE: this is a pre-existing project named "Recortar Audio - Reco" with a leftover "Test Store" app — user chose to reuse it rather than make a dedicated one; harmless (RC holds many apps per project, each app uses its own lookup-key offering).
- Privacy/Support URLs: built a GitHub Pages site — repo leomarston/manycode-legal (public), live at https://leomarston.github.io/manycode-legal/ (index/privacy/terms/support, all HTTP 200). Copy is offline/local-data-accurate (no tracking, RevenueCat for purchases). Source files in ~/manycode-legal/.

**Only remaining .env blocker: GEMINI_API_KEY** (still XXXX) — needed at Faz 8 (screenshot skill, Nano Banana Pro). Everything else can run without it.

Next mechanical steps: re-run `./setup.sh` (registers RevenueCat + Gemini MCPs now that keys exist — Gemini MCP only registers once GEMINI_API_KEY is set), then `./factory.sh fastclock` for the first app. factory.sh preflight no longer aborts (.env differs from .env.example). First run is the "break-in": expect live debugging on scripts/asc_iap.py (ASC subscription API schema) and scripts/rc_setup.py (RC v2 fields). Also: upload_app_privacy_details_to_app_store uses Apple ID *session* auth (no api_key) → may prompt 2FA in terminal on first release.
