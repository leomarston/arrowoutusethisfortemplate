---
name: gameprompt
description: "GAMEPROMPT.md (ultracode) and GAMEPROMPTMAX.md (/effort max, subagents) are the owner's reusable \"make a 1:1 puzzle-game copy on your own\" manuals; on build/matchfactory, not main"
metadata:
  node_type: memory
  type: reference
  originSessionId: 0c154f3b-15af-44af-adf5-6b546962dd29
  modified: 2026-09-24T19:54:09.196Z
---

`GAMEPROMPT.md` (repo root, commit 94a0c32, 2026-09-24) is the owner's reusable prompt. They start a new chat with:
"Read GAMEPROMPT.md and make <game>. ultracode ultrathink", then go to sleep.

- **What it contains:** the whole Arrows + Match Factory method — owner pre-flight, precedence over the store-pipeline rules,
  kickoff with an agent smoke test, W-phone/W-desk research, the four specs plus a consistency pass, art lanes, the build DAG,
  D1 on the phone, a 24 h watchdog, 18 genre playbooks, pitfalls and the definition of done.
- **Where it lives:** only on `build/matchfactory`. It sits there with `tools/phonedriver`, `tools/gameprompt/{workflows,snippets}`
  and the exemplars `apps/{arrows,matchfactory}`, NOT on `main`. A new chat must branch from that HEAD, never from main.
- **Permissions:** the two narrow rules (`tools/phonedriver/phone:*`, `tools/phonedriver/start-runner:*`, absolute paths) are
  in `.claude/settings.local.json` (gitignored) since 2026-09-24. If they are missing on another machine, re-add them there.
- **Max-mode twin:** `GAMEPROMPTMAX.md` (commit a059759, 2026-09-27) is the same manual for `/effort max` without ultracode:
  the chat manages background Agent-tool subagents (briefs in `apps/<slug>/briefs/`, a REPORT block per agent,
  `TEAM-LEDGER.md`, SendMessage for fix rounds) and never calls the Workflow tool. Sentence: "Read GAMEPROMPTMAX.md and make
  <game>. Use parallel subagents for every phase." Switching a chat to /effort max turns ultracode off (seen 2026-09-25).
- **Updating it:** when a GAMEPROMPT run teaches something new, update GAMEPROMPT.md (a pitfall in §13, or a genre entry in §10),
  and the same section of GAMEPROMPTMAX.md: only the orchestration sections differ between the two.

Related: [[phone-driver]], [[max-two-parallel-builds]], [[copycat-the-category]]
