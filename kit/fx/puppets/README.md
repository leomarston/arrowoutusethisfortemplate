# Puppet rigs (`puppets`)

Cut-out character puppets from rig.json: one CALayer per part, looping keyframe motion from ui.json.

PuppetRig loads an art-pipeline rig (Art/<name>/rig.json: layers, pivots, groups); PuppetStage draws it as CALayers and loops the rig's motion (ui.json `puppet.<rig>`). Used by the home scene and the event badges; the rigs themselves are skin slots (skin/art.json `rigs`).

## How the app uses it

```swift
PuppetStage(rig: .homeCharacterMain)   // an ArtRig slot; motion = ui.json puppet.<rig>
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab puppets
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show puppets          # files, what it uses, deps, who depends on it
python3 tools/kit.py export puppets --out /tmp/puppets-kit
python3 tools/kit.py add puppets --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
