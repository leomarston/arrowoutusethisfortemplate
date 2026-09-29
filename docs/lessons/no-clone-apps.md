---
name: no-clone-apps
description: "Before building any new app, screen it against shipped/queued apps for App Store 4.3 spam/clone risk; user \"do it\" overrides"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

User directive (2026-07-27): **Do NOT build a bunch of clones/near-duplicates of our own apps** — Apple Guideline 4.3 (Spam) flags a developer who ships multiple apps with the same core function/UX, and can reject or remove them.

**Why:** all our apps ship under one developer account (Emine Saridogan, GDU77F3MXL). Several similar apps = spam flag risk across the whole account, not just one app.

**How to apply — CHECK BEFORE BUILDING (Faz 0 of every build):**
- Before scaffolding a new idea, compare it against the already-shipped apps and the rest of the queue (`ideas.yaml` + `ROUTINEAPPS.MD`). If the new app's CORE function + category substantially overlaps an existing one (not just a shared framework), STOP and flag it to the user before building.
- Known clone-risk clusters in the current queue to watch: the three data-transfer apps (`iostoandroid`, `movetoandroid`, `movetoios`) are near-duplicates of each other; `contactbackup` + `addressbook` are both contacts apps. Building 2+ of a cluster is the exact 4.3 pattern.
- Diversity is fine: our shipped set (pomodoro/wifispeed/bluetoothmic/reco/partylights/teleprompter) spans distinct functions — that's NOT clone risk.
- **Override:** if the user explicitly says "do it" / "build it anyway", build it regardless — this is advisory, the user has final say.

Related: [[app-naming-keyword-first]], [[daily-routine]] (the 5AM auto-build must apply this screen too).
