# First-time user experience (`ftue`)

The first run: Loading -> the first board with the tutorial -> the first home (+coins) without a menu first.

FTUEDirector chains the first sessions until game.json `ftue.chainUntilLevel`, with the notification prompt over Loading.

## How the app uses it

```swift
// AppModel.boot(): a fresh install (no launch arguments) starts the FTUE chain
-pc.reset 1
```

## Open it in a Debug build

```
-pc.reset 1
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show ftue          # files, what it uses, deps, who depends on it
python3 tools/kit.py export ftue --out /tmp/ftue-kit
python3 tools/kit.py add ftue --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
