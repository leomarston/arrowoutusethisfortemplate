---
name: parallel-agents-and-simulators
description: Delegate long mechanical app work to a subagent, but give it its own simulator — they collide otherwise
metadata:
  type: feedback
---

The user is happy for long, mechanical, multi-app work to run in a **subagent** while the main
session builds something else — they said so directly on 2026-08-21 ("you can use another agent
for this while you are working on the new apps"). It worked well: one agent rebuilt and
resubmitted four apps (and found a real bug) while the main session shipped two new ones.

**But a subagent and the main session share the machine's simulators.** On 2026-08-21 the agent
launched `bluetoothmic` on the same simulator the main session was screenshotting, and a hearUP
capture silently recorded **bluetoothmic's paywall** instead. Nothing errors — you just get the
wrong app in a marketing screenshot.

**How to apply:** before delegating, create a dedicated simulator for whichever side is taking
screenshots:
```
xcrun simctl create "<Name> Capture" com.apple.CoreSimulator.SimDeviceType.iPhone-17-Pro <runtime>
```
and point that app's `tools/capture.sh` UDID at it. Use the SAME device type so all five
marketing frames share one geometry. Always LOOK at a capture before shipping it.

Give the agent exact commands, the known traps, and an explicit "verify against the API and
report a table" step — and tell it never to weaken a failing test to make it pass.

Related: [[interactive-bug-check]], [[simctl-launch-args-gotcha]], [[one-app-per-task]]
