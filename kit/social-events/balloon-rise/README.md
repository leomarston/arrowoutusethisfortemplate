# Up & Away (balloon rise) (`balloon-rise`)

The alternate weekly ladder: a streak tower you climb and fall down, with its home bar.

GameCore BalloonRise + BalloonViews (the tower page, info, fall page) + BalloonBar (the home bar in an Up & Away week).

## How the app uses it

```swift
app.router.go(.event(.balloonRise))
```

## Open it in a Debug build

```
-pc.go event:balloonRise -pc.socialScenario rotationBalloon
-pc.go home -pc.popup balloonInfo
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Shared event helpers live in other events' files: SocInfoTitle / SocTwoLines / SocWarningCard (StreakRaceViews.swift), SocInfoDisc / SocReadyWhen (LeaderboardViews.swift), SocGrantText / SocStageStrip (RocketRaceViews.swift), EventTimerChip (StreakBanner.swift); moving them into SocChrome.swift would let each event stand alone.

## Take it

```
python3 tools/kit.py show balloon-rise          # files, what it uses, deps, who depends on it
python3 tools/kit.py export balloon-rise --out /tmp/balloon-rise-kit
python3 tools/kit.py add balloon-rise --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
