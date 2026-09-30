# Up & Away (balloon rise) (`balloon-rise`)

The alternate weekly ladder: a streak tower you climb and fall down, with its home bar.

GameCore BalloonRise + BalloonViews (the tower page, info, fall page) + BalloonBar (the home bar in an Up & Away week).

## How the app uses it

```swift
app.router.go(.event(.balloonRise))
```

## Notes

- Kit decoupling step: the helpers every event shares are social-ui's (SocEventChrome.swift, Countdown.swift) or ui-chrome's (SocTwoLines); its closure is the events engine (inherent: its pages run the engine's flows, announcements and finish states) + social-ui + ui-chrome.
- Its art slots (`UpAwayArt`, `UpAwayArtImage`) are core's (Components/UpAwayArt.swift): the rotation policy, the social preload list, the announcements and the Profile stat name them. Its win-panel strip is a slot (`PanelStrips` order 20, BalloonRiseRegistration.swift).

## Open it in a Debug build

```
-pc.go event:balloonRise -pc.socialScenario rotationBalloon
-pc.go home -pc.popup balloonInfo
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show balloon-rise          # files, what it uses, deps, who depends on it
python3 tools/kit.py export balloon-rise --out /tmp/balloon-rise-kit
python3 tools/kit.py add balloon-rise --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
