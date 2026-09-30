# HUD timer pill (`hud-timer`)

The stopwatch + m:ss pill, red alert beats, the '+30 sec' pop; frozen look while a freeze runs.

TimerPill draws HUDModel's timer text; shown when the puzzle's capabilities include a timer fail rule.

## How the app uses it

```swift
TimerPill(text: model.timerText, frozen: model.timerFrozen)   // inside HUDView
```

## Open it in a Debug build

```
-pc.go level -pc.level 32 -pc.timer 12
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show hud-timer          # files, what it uses, deps, who depends on it
python3 tools/kit.py export hud-timer --out /tmp/hud-timer-kit
python3 tools/kit.py add hud-timer --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
