# Level HUD (`hud`)

The level HUD over the board: coin group, back, the level panel, pause, drop-in intro; reads only HUDModel.

HUDView lays out the HUD from HUDModel (written only by the game loop's HUDWriter) and the puzzle's HUD widgets; HUDIntro is the drop-in motion as pure functions of time; HUDSample holds the fixed states the warm-up renders. The widgets (timer, hearts, coin pill, booster corners) are their own components. New files dropped in App/Shell/HUD/ are owned here unless another component names them.

## How the app uses it

```swift
// GameScreen, z 1 over the board:
HUDView(model: app.hud, actions: actions)
```

## Notes

- Open (not a coupling): the counters other genres need (HUDCounter.swift: moves / progress / goals from PuzzleCapabilities.hud) are not yet proven on a device (docs/ROADMAP.md).
- Its warm-up renders are registered by HUDRegistration.swift; the booster corners and the widgets are its `wires`.

## Open it in a Debug build

```
-pc.go shelllab -pc.lab hud
-pc.go shelllab -pc.lab hud:hard
-pc.go shelllab -pc.lab hudIntro
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show hud          # files, what it uses, deps, who depends on it
python3 tools/kit.py export hud --out /tmp/hud-kit
python3 tools/kit.py add hud --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
