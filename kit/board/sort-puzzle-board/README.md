# SortPuzzle board (`sort-puzzle-board`)

The tubes board (UIKit + Core Animation, no art files) and the SortPuzzle plugin.

SortPuzzleBoard draws tubes and units from skin tokens (`puzzle.sortBoard.*`) and sort.json `board.*`; SortPuzzlePlugin is the app half of the module, active when ActivePuzzle.entry names SortPuzzleEntry (the PC_PUZZLE_SORT compilation condition). New files in App/Puzzles/SortPuzzle are owned here.

## How the app uses it

```swift
// project.yml: SWIFT_ACTIVE_COMPILATION_CONDITIONS += PC_PUZZLE_SORT
static let entry: PuzzlePluginEntry.Type = SortPuzzleEntry.self
```

## Open it in a Debug build

```
-pc.go level -pc.level 1   (in a PC_PUZZLE_SORT build)
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Names ArrowEscape's FeatureUnlock / SessionPlan and the arrow board's IntroStyle (the game-loop seam).

## Take it

```
python3 tools/kit.py show sort-puzzle-board          # files, what it uses, deps, who depends on it
python3 tools/kit.py export sort-puzzle-board --out /tmp/sort-puzzle-board-kit
python3 tools/kit.py add sort-puzzle-board --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
