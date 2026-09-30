# Quit Level? popup (`quit-level`)

'Quit Level?' band popup: 'You will lose a life!', Quit, X.

The band popup of the Continue? family asked by HUD back and by Pause -> Quit; Quit -> .lost(.quit).

## How the app uses it

```swift
let r = await services.popups.present(Popup<PopupResult>.quitLevel)
if r == .primary { game.fanOut(session.quit(), origin: .director) }
```

## Open it in a Debug build

```
-pc.go level -pc.level 5 -pc.popup quitLevel
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show quit-level          # files, what it uses, deps, who depends on it
python3 tools/kit.py export quit-level --out /tmp/quit-level-kit
python3 tools/kit.py add quit-level --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
