# Rocket Race (`rocket-race`)

A timed race against four simulated racers: offer, tutorial, lanes, result, and the bar under the win panel.

GameCore RocketRace (offered after an unlock level, lane roles from the social world) + RocketRaceViews + RaceBar.

## How the app uses it

```swift
_ = await app.popups.present(Popup<PopupResult>.rocketRace(.offer))
app.router.go(.event(.rocketRace))
```

## Open it in a Debug build

```
-pc.go event:rocketRace -pc.socialScenario rocketMid
-pc.go home -pc.popup rocketRace:offer
-pc.go shelllab -pc.lab race
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Shared event helpers live in other events' files: SocInfoTitle / SocTwoLines / SocWarningCard (StreakRaceViews.swift), SocInfoDisc / SocReadyWhen (LeaderboardViews.swift), SocGrantText / SocStageStrip (RocketRaceViews.swift), EventTimerChip (StreakBanner.swift); moving them into SocChrome.swift would let each event stand alone.

## Take it

```
python3 tools/kit.py show rocket-race          # files, what it uses, deps, who depends on it
python3 tools/kit.py export rocket-race --out /tmp/rocket-race-kit
python3 tools/kit.py add rocket-race --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
