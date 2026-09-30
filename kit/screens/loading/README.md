# Loading screen (`loading`)

The boot cover: the skin's Loading scene (backdrop, logo, cast) and the animated 'Loading...' label.

Shown from the first frame while AppModel.boot() and the warm-ups run; its layers are data (skin/scenes.json `loading` -> SkinScenes). Timings in ui.json `loading.*`, the cross-fades out in `transition.*`.

## How the app uses it

```swift
// Router: Screen.loading is the first state; boot() then calls go(first).
case .loading: LoadingScreen()
```

## Open it in a Debug build

```
-pc.reset 1  (the Loading screen shows during boot)
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show loading          # files, what it uses, deps, who depends on it
python3 tools/kit.py export loading --out /tmp/loading-kit
python3 tools/kit.py add loading --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
