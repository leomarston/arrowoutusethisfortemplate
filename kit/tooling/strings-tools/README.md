# Strings pipeline (`strings-tools`)

strings.tsv + 11 l10n tables -> Localizable.xcstrings, coverage (spec, data, code), self-tests, reviews.

apps/<slug>/tools/strings: build.py (--check in CI), coverage.py, selftest.py, the l10n / tr reviews.

## How the app uses it

```swift
python3 apps/mazeout/tools/strings/build.py --check
```

## Open it in a Debug build

```
python3 apps/mazeout/tools/strings/build.py --check
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show strings-tools          # files, what it uses, deps, who depends on it
python3 tools/kit.py export strings-tools --out /tmp/strings-tools-kit
python3 tools/kit.py add strings-tools --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
