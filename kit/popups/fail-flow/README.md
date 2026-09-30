# Fail flow (out of time, continue, level failed) (`fail-flow`)

The fail chain: Out of Time! / Out of Lives! offer, Continue? variants, then Level Failed with Try Again.

FailFlowDirector drives the chain from the session's .offer / .lost events (rules.json `failChain`, game.json `fail.*`): OutOfTimePopup (+30 sec for coins; Out of Lives! for hearts), ContinuePopup (streak / token / life / hearts-out variants, pays through the shop when short), LevelFailedPopup (Try Again). The streak strip under the panels is the streak-race component's.

## How the app uses it

```swift
// FailFlowDirector, on the session's .offer:
r = await services.popups.present(Popup<PopupResult>.outOfTime(offer, pay: pay))
// ... and on .lost:
await popups.present(Popup<PopupResult>.levelFailed(levels: levels, reason: reason))
```

## Open it in a Debug build

```
-pc.go level -pc.level 32 -pc.lose timeUp
-pc.go level -pc.popup continue:life
-pc.go level -pc.popup levelFailed
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Continue? and Level Failed draw the Streak Race strip and chips (StreakBanner.swift), so the fail flow depends on streak-race and, through it, on the events engine.
- The generic offer popup for other genres' fail kinds (OfferPopup.swift: out of moves, stuck; texts in 13 languages) exists; its text fit is still to be measured on the Mac.

## Take it

```
python3 tools/kit.py show fail-flow          # files, what it uses, deps, who depends on it
python3 tools/kit.py export fail-flow --out /tmp/fail-flow-kit
python3 tools/kit.py add fail-flow --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
