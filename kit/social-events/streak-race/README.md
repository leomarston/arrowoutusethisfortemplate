# Streak Race (`streak-race`)

The daily streak race: 50-row board, the strip under the win / fail panels, the streak chips.

GameCore StreakRace (one race per event day) + StreakRaceViews (the event page and the auto-shown board popup) + StreakBanner (the strip under the win and fail panels, the chip row shared with Continue?).

## How the app uses it

```swift
app.router.go(.event(.streakRace))
_ = await app.popups.present(Popup<PopupResult>.streakRaceBoard)
```

## Open it in a Debug build

```
-pc.go event:streakRace -pc.socialScenario streakList
-pc.go home -pc.popup streakRace
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Shared event helpers live in other events' files: SocInfoTitle / SocTwoLines / SocWarningCard (StreakRaceViews.swift), SocInfoDisc / SocReadyWhen (LeaderboardViews.swift), SocGrantText / SocStageStrip (RocketRaceViews.swift), EventTimerChip (StreakBanner.swift); moving them into SocChrome.swift would let each event stand alone.

## Take it

```
python3 tools/kit.py show streak-race          # files, what it uses, deps, who depends on it
python3 tools/kit.py export streak-race --out /tmp/streak-race-kit
python3 tools/kit.py add streak-race --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
