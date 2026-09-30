# Treasure Climb (claw challenge) (`claw-challenge`)

The weekly points ladder (Treasure Climb): its page and (i) overlay; the home bar is in core for now.

GameCore ClawChallenge (weekly ladder, rules.json `claw`) + ClawScreen (page + (i) overlay) + ClawBar (the home bar).

## How the app uses it

```swift
app.router.go(.event(.claw))
_ = await app.popups.present(Popup<PopupResult>.clawInfo)
```

## Open it in a Debug build

```
-pc.go event:claw -pc.socialScenario clawStep
-pc.go home -pc.popup clawInfo
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Its home bar (App/Shell/Home/ClawBar.swift) is owned by core: the same file holds the Countdown helpers every event uses. Split Countdown out, then move the bar here.
- Shared event helpers live in other events' files: SocInfoTitle / SocTwoLines / SocWarningCard (StreakRaceViews.swift), SocInfoDisc / SocReadyWhen (LeaderboardViews.swift), SocGrantText / SocStageStrip (RocketRaceViews.swift), EventTimerChip (StreakBanner.swift); moving them into SocChrome.swift would let each event stand alone.

## Take it

```
python3 tools/kit.py show claw-challenge          # files, what it uses, deps, who depends on it
python3 tools/kit.py export claw-challenge --out /tmp/claw-challenge-kit
python3 tools/kit.py add claw-challenge --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
