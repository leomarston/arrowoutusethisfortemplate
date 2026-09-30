# ArrowEscape puzzle (rules) (`arrow-escape`)

The reference puzzle: grid, level model and JSON, rules, solver, generator, validator, the session + module.

Packages/PathCore/Sources/ArrowEscape (depends on GameCore only): arrows leave the board along their path; obstacles (tape, pipe, box, elevator, door, corner), the level session, the solver / hint, the seeded generator and validator, ArrowEscapeModule (the PuzzleModule), plus pclevels (the content CLI) and the authored levels.

## How the app uses it

```swift
let module = ArrowEscapeModule(rules: rules)
let session = module.makeSession(stage: stage, seed: seed)   // GameCore PuzzleSession
```

## Open it in a Debug build

```
python3 apps/mazeout/tools/levels/bundle_check.py --publish
python3 apps/mazeout/design/tools/validate_levels.py
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show arrow-escape          # files, what it uses, deps, who depends on it
python3 tools/kit.py export arrow-escape --out /tmp/arrow-escape-kit
python3 tools/kit.py add arrow-escape --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
