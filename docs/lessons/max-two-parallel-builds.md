---
name: max-two-parallel-builds
description: "This Mac (16 GB, 8 cores) thrashes with 5 parallel xcodebuild agents + 3 sims — 17 GB swap, all agents stalled, disk filled; cap at 2"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 0c154f3b-15af-44af-adf5-6b546962dd29
  modified: 2026-09-23T20:52:04.800Z
---

On 2026-09-23 an arrows build workflow ran 5 agents at once, each building its own scratch Xcode project and
3 of them booting their own simulator. The Mac (16 GB RAM, 8 cores, with the user's VS Code, Brave, several old
`claude` sessions and a 2 GB CursorUIViewService already resident) went to **17 GB of swap**. Every agent then
"stalled on all 6 attempts (no progress for 180 s)" after ~2 h, the workflow crashed, and the swap files ate the
disk (12 GB → 4.8 GB free). Files the agents had written survived, so the work was resumable.

**Why:** swap thrashing makes every tool call crawl, so agents look stalled; macOS swap files live on the boot disk.

**How to apply:**
- In workflows here, at most **2 agents that compile/boot simulators** at a time; non-build agents (research,
  Python, SwiftPM-on-macOS tests) can run alongside.
- Tell build agents: one xcodebuild at a time, `-jobs 4 -quiet`, each command < 3 min, one simulator, shut it down after.
- Before a big run: `df -h /`, `sysctl vm.swapusage`. Safe space to reclaim: `~/Library/Developer/Xcode/DerivedData`,
  Xcode Previews sims (`xcrun simctl --set previews delete all`, was 8 GB), scratch DerivedData, erased harness sims.
  Never delete other apps' capture sims.
- Workflow scripts must `.filter(Boolean)` parallel results — a null from a dead agent crashed the integration stage.

Related: [[parallel-agents-and-simulators]], [[disk-fills-fast-clean-archives]], [[disk-full-lies]]
