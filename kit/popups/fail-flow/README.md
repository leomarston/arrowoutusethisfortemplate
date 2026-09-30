# Fail flow (out of time, continue, level failed) (`fail-flow`)

The fail chain: Out of Time! / Out of Lives! offer, Continue? variants, then Level Failed with Try Again.

FailFlowDirector drives the chain from the session's .offer / .lost events (rules.json `failChain`, game.json `fail.*`): OutOfTimePopup (+30 sec for coins; Out of Lives! for hearts), ContinuePopup (streak / token / life / hearts-out variants, pays through the shop when short), LevelFailedPopup (Try Again), OfferPopup (the other genres' fail kinds). Registered by FailFlowRegistration.swift (panels, `-pc.popup` ids, warm-ups). The Streak Race strip under Level Failed and the chips on Continue? are slots (`PanelStrips`, `ContinueChips`) the streak-race component fills: without it they are simply not drawn.

## How the app uses it

```swift
// FailFlowDirector, on the session's .offer:
r = await services.popups.present(Popup<PopupResult>.outOfTime(offer, pay: pay))
// ... and on .lost:
await popups.present(Popup<PopupResult>.levelFailed(levels: levels, reason: reason))
```

## Notes

- Its closure is the game loop (FailFlowDirector is a game director) + ui-chrome: inherent. 29 of its 49 files are Swift; the rest are the sound engine's (9 .wav files and its synthesis tools) that the loop plays.
- Open (not a coupling): the generic offer popup for other genres' fail kinds (OfferPopup.swift: out of moves, stuck; texts in 13 languages) exists; its text fit is still to be measured on the Mac.

## Open it in a Debug build

```
-pc.go level -pc.level 32 -pc.lose timeUp
-pc.go level -pc.popup continue:life
-pc.go level -pc.popup levelFailed
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show fail-flow          # files, what it uses, deps, who depends on it
python3 tools/kit.py export fail-flow --out /tmp/fail-flow-kit
python3 tools/kit.py add fail-flow --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
