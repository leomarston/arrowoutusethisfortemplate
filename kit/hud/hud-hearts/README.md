# HUD hearts row (`hud-hearts`)

Three heart slots; the rightmost full heart breaks on a mistake (right to left).

HeartsRow draws HUDModel.hearts (full / lost / empty) with the break animation; used by a hearts fail rule.

## How the app uses it

```swift
HeartsRow(slots: model.hearts)   // inside HUDView
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab hud:hearts1
-pc.go shelllab -pc.lab hudBreak
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show hud-hearts          # files, what it uses, deps, who depends on it
python3 tools/kit.py export hud-hearts --out /tmp/hud-hearts-kit
python3 tools/kit.py add hud-hearts --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
