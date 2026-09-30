# Rating prompt (`rating-prompt`)

Asks for an App Store rating once, on the home after a chosen level (game.json rating.afterLevel).

RatingDirector: once per install (flags.ratingPromptShown saved first), AppStore.requestReview(in:).

## How the app uses it

```swift
RatingDirector.maybeAsk(app)   // on home arrival
```

## Open it in a Debug build

```
-pc.go home -pc.level 35
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show rating-prompt          # files, what it uses, deps, who depends on it
python3 tools/kit.py export rating-prompt --out /tmp/rating-prompt-kit
python3 tools/kit.py add rating-prompt --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
