# Rocket Race (`rocket-race`)

A timed race against four simulated racers: offer, tutorial, lanes, result, and the bar under the win panel.

GameCore RocketRace (offered after an unlock level, lane roles from the social world) + RocketRaceViews + RaceBar (the bar under the win panel: `PanelStrips` order 10, RocketRaceRegistration.swift).

## How the app uses it

```swift
_ = await app.popups.present(Popup<PopupResult>.rocketRace(.offer))
app.router.go(.event(.rocketRace))
```

## Notes

- Kit decoupling step: the helpers every event shares are social-ui's (SocEventChrome.swift, Countdown.swift) or ui-chrome's (SocTwoLines); its closure is the events engine (inherent: its pages run the engine's flows, announcements and finish states) + social-ui + ui-chrome.

## Open it in a Debug build

```
-pc.go event:rocketRace -pc.socialScenario rocketMid
-pc.go home -pc.popup rocketRace:offer
-pc.go shelllab -pc.lab race
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show rocket-race          # files, what it uses, deps, who depends on it
python3 tools/kit.py export rocket-race --out /tmp/rocket-race-kit
python3 tools/kit.py add rocket-race --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
