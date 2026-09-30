# Fireworks (`fireworks`)

Core Animation fireworks: rockets and bursts with precomputed keyframes.

FXEffect.fireworks(in:) on the FX host; ui.json `fx.firework`.

## How the app uses it

```swift
app.fx.play(.fireworks(in: rect))
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab celebrate:hard
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show fireworks          # files, what it uses, deps, who depends on it
python3 tools/kit.py export fireworks --out /tmp/fireworks-kit
python3 tools/kit.py add fireworks --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
