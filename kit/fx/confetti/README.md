# Confetti (`confetti`)

Core Animation confetti: precomputed keyframes on the render server, zero main-thread work while it falls.

FXEffect.confetti(in:) on the FX host; counts, colours and timing in ui.json `fx.confetti`.

## How the app uses it

```swift
app.fx.play(.confetti(in: rect))
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab celebrate:normal
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show confetti          # files, what it uses, deps, who depends on it
python3 tools/kit.py export confetti --out /tmp/confetti-kit
python3 tools/kit.py add confetti --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
