# Claim reward popup (`claim-reward`)

'Congratulations!' - the reward (coins, boosters, unlimited lives) popping in, tap to claim.

ClaimRewardPopup shows a Grant (coins / booster / unlimited lives variants) and answers on tap; used by events and gifts.

## How the app uses it

```swift
let r = await app.popups.present(Popup<PopupResult>.claimReward(.coins(200)))
```

## Open it in a Debug build

```
-pc.go home -pc.popup claim:coins
-pc.go home -pc.popup claim:hint
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show claim-reward          # files, what it uses, deps, who depends on it
python3 tools/kit.py export claim-reward --out /tmp/claim-reward-kit
python3 tools/kit.py add claim-reward --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
