---
name: one-app-per-task
description: "HARD RULE: a task touches ONE app only — never fan a fix out to other apps unless the user explicitly says so"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: af304055-c323-4932-95ec-dca1c6b99b7b
  modified: 2026-08-08T14:17:23.342Z
---

**When building a new app or changing one app, do not touch any other app.** Not the code,
not its builds, not its App Store Connect state. If another app gets rejected, or the user
removed it, or it shares the same bug — **don't care, don't act.** Just do the task asked.

**Why:** the user owns portfolio-level decisions. On 2026-08-07 a single 3.1.2(c) rejection on
`bracketmaker` (a paywall free-trial toggle inherited from `template/`) turned into pulling,
rebuilding and resubmitting **9 other apps** that were sitting in review — every one of them
lost its queue position. That fan-out was requested at the time ("make sure you fix them and
send to submit again"), but the rule set the next day is that it must NEVER be the default:
a shared root cause is NOT a licence to go edit the rest of the portfolio.

**How to apply:**
- Scope every change to `apps/<the-one-slug>/`. Fixing `template/` is fine (it affects only
  FUTURE apps) but does not license retrofitting existing ones.
- Never run builds/uploads/`asc_submit.py` for an app the user didn't name.
- Another app being REJECTED, DEVELOPER_REJECTED, removed, or stale is **not** a reason to act,
  raise a blocking question, or stall the current task.
- You MAY mention an observation in one line ("note: X has the same issue") and then move on.
  Only act on it if the user explicitly asks.
- Explicit override looks like the user naming the apps or saying "fix them all" — until then,
  one app.

Related: [[no-free-trial-toggle]] (the incident), [[no-clone-apps]].
