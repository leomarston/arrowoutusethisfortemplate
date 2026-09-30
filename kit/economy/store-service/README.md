# Store service (StoreKit 2 purchases) (`store-service`)

The purchase engine: StoreKit 2 StoreService, the Debug FakeStore, the RevenueCat observer, the .storekit file.

StoreService is the real store of every Release build (prices only from StoreKit's displayPrice; never finishes a transaction whose grant failed to save). FakeStore serves tests and captures; RevenueCatObserver only observes (no backend of ours); the product table is GameCore's ShopCatalog (core, rules.json `shop`); Attribution's PurchaseReporting is the hook for an optional per-game ad-attribution SDK (off).

## How the app uses it

```swift
let outcome = await app.shop.purchase(productID)   // StorePurchasing: grants, saves, then finishes
```

## Wiring

- IAP catalogue == rules.json shop == .storekit: python3 apps/<slug>/tools/release/meta.py iap-check.

## Open it in a Debug build

```
-pc.go shop -pc.fakeStore 1
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show store-service          # files, what it uses, deps, who depends on it
python3 tools/kit.py export store-service --out /tmp/store-service-kit
python3 tools/kit.py add store-service --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
