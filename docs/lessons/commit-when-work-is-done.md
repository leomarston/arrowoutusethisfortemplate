---
name: commit-when-work-is-done
description: HARD RULE — commit finished work without being asked; "complete it" includes committing, and leaving a dirty tree is not acceptable
metadata:
  type: feedback
---

**Commit as part of finishing.** Do not end a piece of work — an app, a fix, a doc — with an
uncommitted working tree, and do not ask permission first. The user, after a full app was built and
submitted with everything left unstaged: *"BRO WHY NOTHING IS FUCKING COMMMITTED, WHY. FUCKING
COMPLETE IT AND SUBMIT"*.

**Why:** in this repo "done" means committed. `PROJECT_LOG.md` had already recorded months of work
sitting uncommitted on `build/procam`, so leaving more is actively harmful — it compounds a problem
the user has been bitten by before. Waiting to be asked reads as leaving the job half-finished.

**How to apply:** commit at the end of each app (and at meaningful checkpoints during long runs),
on the current branch. Keep commits separated by authorship of the work: your app in one commit,
another session's stray files in their own, clearly labelled. Never stage `.env`, `keys/`, or build
artifacts — add an ignore rule instead of checking them in. Push only if asked.
Related: [[finish-the-whole-pipeline]].
