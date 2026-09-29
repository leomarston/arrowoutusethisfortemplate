---
name: env-dependent-tests-assert-all-outcomes
description: A test that depends on the real LAN/network must assert every honest outcome, or it passes in one appearance and fails in the other
metadata:
  type: feedback
---

camdetect's free network test asserted "locked results OR nothing answered".
The view actually settles on THREE cards: locked, empty, and blocked ("the
probes never left the phone"). On a busy machine the LAN sometimes did not
answer, so the same commit passed in dark mode and failed in light mode.

Two separate traps in that one test:
- **Local Network is the one permission `simctl privacy` cannot pre-grant**
  (`grant`/`reset user-tracking` return "Operation not permitted"), and the scan
  that RAISES the prompt is already recorded as blocked by the time it is
  answered. There is no rescan control, so answering mid-test cannot rescue that
  run — prime it on a throwaway launch first ([[permission-prompt-is-one-shot]]).
- Asserting a subset of the terminal states makes the network the test oracle.

**Why:** a flaky gate costs a 15-minute cycle each time and trains you to ignore
red.

**How to apply:** assert the screen settled on ONE OF its honest terminal states,
then run the real assertions (the Pro gate) only in the branch where there was
something to gate. Say out loud in the log when the environment skipped it.
