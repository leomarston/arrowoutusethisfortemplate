# Release gates and store metadata (`release-gates`)

Store texts / keywords / IAP audits, the release gates (brand bans, SDK allow-list, Release strip), fastlane.

apps/<slug>/tools/release (meta.py audit / iap-check / selftest, loc.py), tools/bench/release_gates.sh, the fastlane lanes; README §6 is the order. Run every store script with --dry-run first.

## How the app uses it

```swift
python3 apps/mazeout/tools/release/meta.py audit && python3 apps/mazeout/tools/release/meta.py iap-check
```

## Open it in a Debug build

```
python3 apps/mazeout/tools/release/meta.py audit
python3 apps/mazeout/tools/release/meta.py iap-check
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show release-gates          # files, what it uses, deps, who depends on it
python3 tools/kit.py export release-gates --out /tmp/release-gates-kit
python3 tools/kit.py add release-gates --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
