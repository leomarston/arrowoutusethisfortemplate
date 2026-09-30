# SortPuzzle puzzle (rules) (`sort-puzzle`)

The second module (colour sorting): level model, seeded generator, solver, session, module. GameCore only.

Packages/PathCore/Sources/SortPuzzle, pinned to the Python reference (tools/sortpuzzle/ref.py goldens).

## How the app uses it

```swift
let module = SortPuzzleModule(tuning: sort)
```

## Open it in a Debug build

```
python3 apps/mazeout/tools/sortpuzzle/ref.py --check
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show sort-puzzle          # files, what it uses, deps, who depends on it
python3 tools/kit.py export sort-puzzle --out /tmp/sort-puzzle-kit
python3 tools/kit.py add sort-puzzle --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
