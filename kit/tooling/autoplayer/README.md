# AutoPlayer bot (`autoplayer`)

`-pc.autoplay 1`: a bot that plays through the game via the puzzle's bot, for soaks and captures.

Debug / Measure only. Plays each stage through the module's bot, answers popups, loops the game (game.json `autoplay.*`).

## How the app uses it

```swift
-pc.autoplay 1 -pc.autoplayRate 0.4
```

## Open it in a Debug build

```
-pc.go level -pc.level 1 -pc.autoplay 1
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show autoplayer          # files, what it uses, deps, who depends on it
python3 tools/kit.py export autoplayer --out /tmp/autoplayer-kit
python3 tools/kit.py add autoplayer --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
