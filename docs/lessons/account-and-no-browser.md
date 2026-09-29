---
name: account-and-no-browser
description: HARD RULE — never use Claude in Chrome in this project; only the esaridogann@gmail.com Apple + RevenueCat account
metadata:
  type: feedback
---

Two strict rules for the app factory:

1. **Browser automation (`mcp__claude-in-chrome__*`) is limited to an allow-list.** Set
   2026-08-20 after an attempt to read Resolution Center in ASC via the browser.
   **Allowed, and nothing else:**
   - **Appfigures** (appfigures.com) — ASO keyword research. Granted 2026-08-20.
   - **Meta ads** — developers.facebook.com, business.facebook.com,
     facebook.com/ads/library. Granted 2026-09-05: *"you can open the browser for
     appfigures and metaads only, now open the browser."*
   **Still forbidden:** App Store Connect, any Apple site, and every other page. Rejection
   reasons in ASC Resolution Center must still be pasted in by the user.
2. **Only the `esaridogann@gmail.com` Apple + RevenueCat account may be used.** That is what
   `.env` holds (TEAM_ID `GDU77F3MXL`, DEV_NAME "Emine Saridogan", ASC key `B46H6FGV43`,
   RC project `proj5f4f704a`). Never operate on any other Apple/RC account.

**Why:** the browser session and other Apple IDs belong to different, unrelated accounts —
touching them risks acting on the wrong developer account entirely.

**How to apply:** do all App Store Connect work through the REST API with the `.env` key
(`scripts/asc_*.py`) and fastlane. If something is only reachable in the ASC web UI (e.g.
**App Review Resolution Center rejection messages**), ASK THE USER to read it out — do not
open a browser. Note the connected Gmail MCP is a *different* account
(yagizsaridogan@gmail.com), so Apple review emails for the factory are NOT visible there.

Related: [[app-factory-setup-state]], [[one-app-per-task]]
