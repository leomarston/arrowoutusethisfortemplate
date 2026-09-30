# Win celebration (logo sequence) (`win-celebration`)

The Core Animation win celebration: logo letters, confetti, fireworks, tier looks, skippable.

WinLogoSequence plays `.celebration(tag)` on the FX host: the logo parts (skin slots logo.part.*, ui.json `win.logo`) with letter beats, fireworks and confetti, pre-built behind Loading. Timings ui.json `win.*`.

## How the app uses it

```swift
let h = app.fx.play(.celebration(.hard))
await app.fx.finished(h)
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab celebrate:normal
-pc.go shelllab -pc.lab celebrate:superHard
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show win-celebration          # files, what it uses, deps, who depends on it
python3 tools/kit.py export win-celebration --out /tmp/win-celebration-kit
python3 tools/kit.py add win-celebration --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
