# Game config (game.py) (`game-config`)

tools/game.py new / generate / doctor: one game.yml drives identity, store, flags, seeds and ban lists.

The repo-level config tool (docs/TEMPLATE.md): scaffolds apps/<slug>, writes every repeated value, and checks the game.

## How the app uses it

```swift
python3 tools/game.py doctor --game mazeout --quick
```

## Open it in a Debug build

```
python3 tools/game.py doctor --game mazeout --quick
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show game-config          # files, what it uses, deps, who depends on it
python3 tools/kit.py export game-config --out /tmp/game-config-kit
python3 tools/kit.py add game-config --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
