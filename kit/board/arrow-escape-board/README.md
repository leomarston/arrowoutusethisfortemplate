# ArrowEscape board (`arrow-escape-board`)

The arrow board view: UIKit + Core Animation engine, obstacles, exits, bumps, hints, the ArrowEscape plugin.

App/Board: BoardEngine (layers, input, animations; acknowledges beats back to the session), every obstacle layer, exit / bump movers, clear wave, stage transitions, hint highlight, warm-up; ArrowEscapePlugin adapts it to the generic PuzzleBoard contract; BoardLab is its debug host. New files in App/Board are owned here automatically.

## How the app uses it

```swift
// ActivePuzzle.entry names the module's plugin (one line):
static let entry: PuzzlePluginEntry.Type = ArrowEscapeEntry.self
```

## Open it in a Debug build

```
-pc.go boardlab
-pc.go level -pc.level 32
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- App/Board/DigitGlyphs.swift spells the font name "PCDisplay-Black" (not yet skin data).

## Take it

```
python3 tools/kit.py show arrow-escape-board          # files, what it uses, deps, who depends on it
python3 tools/kit.py export arrow-escape-board --out /tmp/arrow-escape-board-kit
python3 tools/kit.py add arrow-escape-board --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
