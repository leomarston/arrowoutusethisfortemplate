# Shop page (`shop`)

The Shop tab / page: special offer, bundles, coin packs, purchase flow with sparkles and toasts.

ShopView lays out the catalogue (1 special offer, bundles, coin packs) with live StoreKit prices, buys through the store service and plays the coin fly / sparkles. Opens as the home's Shop tab (`ShellScreens.registerTabPage(.shop)`) or as a closable page over an offer (`.custom("shop")`); ShopRegistration.swift registers both, the `-pc.popup shop` id, the warm-up and the boot hook (the offers' coin groups open it; the store starts). The economy table (ShellEconomy) is core's; the formats and titles are economy-ui's.

## How the app uses it

```swift
app.router.go(.home(.normal, tab: .shop))
S2Hooks.openShop(app)   // the offers' coin group: the Shop as a closable page
```

## Open it in a Debug build

```
-pc.go shop -pc.fakeStore 1
-pc.go shop -pc.fakeStore 1 -pc.storeRegion TR
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show shop          # files, what it uses, deps, who depends on it
python3 tools/kit.py export shop --out /tmp/shop-kit
python3 tools/kit.py add shop --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
