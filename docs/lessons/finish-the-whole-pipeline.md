---
name: finish-the-whole-pipeline
description: HARD — when told to build an app, run Faz 0-11 to submission without stopping to check in
metadata:
  type: feedback
---

When the user says to build an app, **build it all the way to submitted**. Do not stop at a
phase boundary to report progress, ask which option they prefer, or wait on a
nice-to-have blocker. Set 2026-08-20, after stopping twice mid-`hearingtest`
("WHY DONT YOU FUCKING COMPLETE IT AND WHY DO YOU STOP BEFORE COMPLETING IT").

**Why:** the app-factory skill already defines every phase and its done-criterion. A
checkpoint mid-pipeline is not new information for the user — it is just an unfinished app.

**How to apply:** run Faz 0-11 continuously. Flags, deviations and blocked side-quests
(e.g. an un-logged-in Appfigures, an exhausted Gemini quota) go in the FINAL report, not in a
mid-run pause — work around them and keep going. Only genuinely stop for: a hard blocker with
no workaround (then write `BLOCKED.md`), or a rule that mandates asking (the 4.3 clone screen
for a NEW idea, which is about what to build next, not about finishing the current one).

Related: [[one-app-per-task]], [[no-clone-apps]]
