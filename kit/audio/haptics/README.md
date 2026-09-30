# Haptics (`haptics`)

Haptic patterns as data (audio.json haptics + priority) with a one-per-frame arbiter.

Haptics plays a Haptic case with the style / intensity of Tuning/audio.json `haptics.<case>`; the arbiter keeps one per frame.

## How the app uses it

```swift
app.haptics.play(.button)
```

## Open it in a Debug build

```
-pc.go soundboard -pc.hapticLog 1
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show haptics          # files, what it uses, deps, who depends on it
python3 tools/kit.py export haptics --out /tmp/haptics-kit
python3 tools/kit.py add haptics --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
