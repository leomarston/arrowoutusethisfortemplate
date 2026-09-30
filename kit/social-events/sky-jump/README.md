# Sky Jump (`sky-jump`)

A 24 h stage climb with a shared prize pool: offer, matching, tutorial, map progress, win.

GameCore SkyJump (stages, pools, the 24 h run) + SkyJumpViews (offer, matching, tutorial, progress map, win).

## How the app uses it

```swift
_ = await app.popups.present(Popup<PopupResult>.skyJump(.offer))
app.router.go(.event(.skyJump))
```

## Open it in a Debug build

```
-pc.go event:skyJump -pc.socialScenario skyStep2
-pc.go home -pc.popup skyJump:offer
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Shared event helpers live in other events' files: SocInfoTitle / SocTwoLines / SocWarningCard (StreakRaceViews.swift), SocInfoDisc / SocReadyWhen (LeaderboardViews.swift), SocGrantText / SocStageStrip (RocketRaceViews.swift), EventTimerChip (StreakBanner.swift); moving them into SocChrome.swift would let each event stand alone.

## Take it

```
python3 tools/kit.py show sky-jump          # files, what it uses, deps, who depends on it
python3 tools/kit.py export sky-jump --out /tmp/sky-jump-kit
python3 tools/kit.py add sky-jump --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
