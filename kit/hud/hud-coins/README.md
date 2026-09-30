# HUD coin pill (`hud-coins`)

The level's coin group: coin icon over a recessed pill with the balance.

CoinPillHUD shows HUDModel.coins beside the Dynamic Island; tapping it opens the Shop over the level.

## How the app uses it

```swift
CoinPillHUD(coins: model.coins)   // inside HUDView
```

## Open it in a Debug build

```
-pc.go level -pc.level 32 -pc.coins 2240
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show hud-coins          # files, what it uses, deps, who depends on it
python3 tools/kit.py export hud-coins --out /tmp/hud-coins-kit
python3 tools/kit.py add hud-coins --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
