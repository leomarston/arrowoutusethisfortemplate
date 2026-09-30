# Lives (`lives`)

The More Lives popup (0 lives at a Play: next-life timer, Refill for coins) over GameCore's lives rules.

GameCore Lives (max, refill seconds, refill price, unlimited windows; rules.json `lives`) and the More Lives popup (NoLivesPopup: the big heart, time to next life, Refill for coins) that LevelFlow opens when a Play finds 0 lives.

## How the app uses it

```swift
_ = await popups.present(Popup<PopupResult>.noLives)   // LevelFlow, at a Play with 0 lives
```

## Open it in a Debug build

```
-pc.go home -pc.lives 0 -pc.livesNextIn 900
-pc.go home -pc.popup noLives
-pc.go home -pc.unlimitedLives 1800
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show lives          # files, what it uses, deps, who depends on it
python3 tools/kit.py export lives --out /tmp/lives-kit
python3 tools/kit.py add lives --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
