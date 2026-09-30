# Weekly Contest (`weekly-contest`)

A weekly tournament against simulated players: intro, the forced tutorial, standings, result and prizes.

GameCore WeeklyContest (one per event week, from the unlock level) and its screens (WeeklyViews: tutorial, intro, result).

## How the app uses it

```swift
_ = await app.popups.present(Popup<PopupResult>.weeklyContestIntro)
```

## Open it in a Debug build

```
-pc.go leaderboard:weekly -pc.socialScenario weeklyFresh
-pc.go home -pc.popup weeklyIntro
-pc.go home -pc.popup weeklyTutorial
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Shared event helpers live in other events' files: SocInfoTitle / SocTwoLines / SocWarningCard (StreakRaceViews.swift), SocInfoDisc / SocReadyWhen (LeaderboardViews.swift), SocGrantText / SocStageStrip (RocketRaceViews.swift), EventTimerChip (StreakBanner.swift); moving them into SocChrome.swift would let each event stand alone.

## Take it

```
python3 tools/kit.py show weekly-contest          # files, what it uses, deps, who depends on it
python3 tools/kit.py export weekly-contest --out /tmp/weekly-contest-kit
python3 tools/kit.py add weekly-contest --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
