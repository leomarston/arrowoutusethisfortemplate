# Toasts (`toasts`)

One-at-a-time toast plate over everything (newest replaces), text from the strings table.

ToastCenter.show(_:) - a plate with one or two lines of the toast text role; timings and look in ui.json `toast.*`.

## How the app uses it

```swift
app.toasts.show("Purchase pending")
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab components   (shows a toast)
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show toasts          # files, what it uses, deps, who depends on it
python3 tools/kit.py export toasts --out /tmp/toasts-kit
python3 tools/kit.py add toasts --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
