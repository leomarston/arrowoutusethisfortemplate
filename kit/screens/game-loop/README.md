# Level screen and game loop (`game-loop`)

GameController + LevelFlow + HUDWriter + GameScreen: runs a puzzle session and fans its events out.

One GameController per Play: owns the module's PuzzleSession, is the board's delegate, and fans every output batch out in a fixed order (board, HUD, audio/haptics, directors). LevelFlow runs the start sequence (lives gate, intro), pause / back / quit; HUDWriter is the only writer of HUDModel; GameScreen stacks board, HUD, tutorial layer. The directors (win, fail, boosters, unlocks, tutorial, events) are separate components installed through GameDirectors+G2.

## How the app uses it

```swift
// The router hosts a level through GAME's LevelHosting:
app.router.go(.level(LevelLaunch(session: plan.id, levels: [32])))
// LevelFlow.pause(): the Pause popup, then Quit Level? on Quit
let r = await services.popups.present(Popup<PopupResult>.pause)
```

## Open it in a Debug build

```
-pc.go level -pc.level 32
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- The generic loop still names SessionPlan (ArrowEscape) and IntroStyle (App/Contracts/BoardContract.swift, the arrow board's contract) - docs/ROADMAP.md 'SessionPlan into GameCore'.

## Take it

```
python3 tools/kit.py show game-loop          # files, what it uses, deps, who depends on it
python3 tools/kit.py export game-loop --out /tmp/game-loop-kit
python3 tools/kit.py add game-loop --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
