# Coin fly (`coin-fly`)

The coin payout: '+N' label and coins flying into the coin pill, as Core Animation layers.

FXEffect.coinFly(amount:coins:from:to:) on the FX host (timing = motion spec, look = UI spec).

## How the app uses it

```swift
app.fx.play(.coinFly(amount: 120, coins: balance, from: winTotal, to: coinPill))
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab homeReturn
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show coin-fly          # files, what it uses, deps, who depends on it
python3 tools/kit.py export coin-fly --out /tmp/coin-fly-kit
python3 tools/kit.py add coin-fly --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
