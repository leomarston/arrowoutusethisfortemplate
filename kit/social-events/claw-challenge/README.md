# Treasure Climb (claw challenge) (`claw-challenge`)

The weekly points ladder (Treasure Climb): its page, (i) overlay and home bar.

GameCore ClawChallenge (weekly ladder, rules.json `claw`) + ClawScreen (page + (i) overlay) + ClawBar (the home bar; its frame, fill, token and flame are the home's shared event-bar chrome, EventBarChrome.swift, which Up & Away's bar and the payout draw too).

## How the app uses it

```swift
app.router.go(.event(.claw))
_ = await app.popups.present(Popup<PopupResult>.clawInfo)
```

## Notes

- Kit decoupling step: the helpers every event shares are social-ui's (SocEventChrome.swift, Countdown.swift) or ui-chrome's (SocTwoLines); its closure is the events engine (inherent: its pages run the engine's flows, announcements and finish states) + social-ui + ui-chrome.

## Open it in a Debug build

```
-pc.go event:claw -pc.socialScenario clawStep
-pc.go home -pc.popup clawInfo
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show claw-challenge          # files, what it uses, deps, who depends on it
python3 tools/kit.py export claw-challenge --out /tmp/claw-challenge-kit
python3 tools/kit.py add claw-challenge --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
