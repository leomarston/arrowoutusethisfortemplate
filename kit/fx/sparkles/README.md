# Sparkles (`sparkles`)

A burst of four-point twinkle stars around a point (rewards, unlock icons, coin pill).

FXEffect.sparkles(at:); count / radius / duration / size in ui.json `fx.sparkles`.

## How the app uses it

```swift
app.fx.play(.sparkles(at: point))
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab homeReturn
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show sparkles          # files, what it uses, deps, who depends on it
python3 tools/kit.py export sparkles --out /tmp/sparkles-kit
python3 tools/kit.py add sparkles --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
