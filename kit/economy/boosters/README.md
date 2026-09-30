# Boosters (`boosters`)

Booster table, the two HUD booster corners, the buy popup at 0 stock and the freeze effect.

GameCore Boosters (what each does, start stock, price; rules.json `boosters`) and BoosterDirector (slots from the puzzle's BoosterSpecs; tap -> use, or BoosterBuyPopup at 0 stock). BoosterCorner draws the corner trays with count badges; HUDFreeze is the time-freeze booster's HUD effect (ui.json `freeze.*`).

## How the app uses it

```swift
let r = await popups.present(Popup<PopupResult>.boosterBuy(.hint))
app.fx.play(.custom(id: "freeze", params: ["seconds": 10]))
```

## Notes

- Kit decoupling step: the borrowed helpers moved to ui-chrome (SocTwoLines, SunburstRays) and economy-ui (CoinPillDisplay); the Time Freeze runs on the FX host as FreezeFX (HUDFreeze.swift), registered by BoostersRegistration.swift with the buy popup.

## Open it in a Debug build

```
-pc.go level -pc.level 32 -pc.boosters freeze=0,hint=0
-pc.go level -pc.popup boosterBuy:hint
-pc.go shelllab -pc.lab freeze
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- Booster ids are still the reference's (freeze, hint) in BoosterID; booster ids from config are open (docs/ROADMAP.md phase 1).

## Take it

```
python3 tools/kit.py show boosters          # files, what it uses, deps, who depends on it
python3 tools/kit.py export boosters --out /tmp/boosters-kit
python3 tools/kit.py add boosters --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
