# Win flow and win panel (`win-flow`)

WinDirector banks the win at the last move, plays the celebration, then the win panel (normal / Hard / Super Hard).

At the winning move the win is banked at once (Economy.finishAttempt), the board's clear wave and the celebration play, then WinPanel shows the reward (tier colours) with the event strips under it (streak-race banner / rocket-race bar). Continue -> home with the payout queue.

## How the app uses it

```swift
celebration = services.fx.play(.celebration(result.tag))
let answer = await services.popups.present(Popup<PopupResult>.winPanel(summary))
```

## Open it in a Debug build

```
-pc.go level -pc.level 32 -pc.win normal
-pc.go level -pc.level 36 -pc.win hard
-pc.go level -pc.popup win
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- WinPanel names EventsDirector (events-engine) and PanelLabel (LevelFailedPopup.swift, fail-flow); the event strips under the panel are wired (streak / rocket / balloon).

## Take it

```
python3 tools/kit.py show win-flow          # files, what it uses, deps, who depends on it
python3 tools/kit.py export win-flow --out /tmp/win-flow-kit
python3 tools/kit.py add win-flow --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
