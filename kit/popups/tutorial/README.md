# In-level tutorial (`tutorial`)

Tutorial steps from Levels/tutorials.json: caption + hand pointer over the board, input gating.

TutorialDirector plays the module's TutorialStep list (trigger / dismiss) through TutorialLayer (caption and hand; ui.json `tutorial.*`).

## How the app uses it

```swift
// installed per Play by GameDirectors.make; the layer sits at z 2 in GameScreen
TutorialLayer(model: app.tutorial)
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab tutorial
-pc.reset 1 -pc.tutorials force
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show tutorial          # files, what it uses, deps, who depends on it
python3 tools/kit.py export tutorial --out /tmp/tutorial-kit
python3 tools/kit.py add tutorial --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
