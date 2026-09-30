# Feature unlock cards (`unlock-cards`)

A feature's first appearance: staggered icon / title / 'Unlocked!' / card over the level, tap to dismiss.

UnlockDirector opens UnlockOverlay on the Play of a level whose Levels/unlocks.json feature is not yet in PlayerState.unlocksSeen; beats in ui.json `unlock.*` (UnlockBeats). The card texts come from the puzzle module's unlock data.

## How the app uses it

```swift
let r = await popups.present(Popup<PopupResult>.unlockOverlay(feature))
```

## Notes

- FeatureUnlock is GameCore's now (Session/FeatureUnlock.swift; the bundle's list reader stays in ArrowEscape). Registered by UnlockCardsRegistration.swift.

## Open it in a Debug build

```
-pc.go shelllab -pc.lab unlock:pipe
-pc.go level -pc.level 21 -pc.unlocks force
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show unlock-cards          # files, what it uses, deps, who depends on it
python3 tools/kit.py export unlock-cards --out /tmp/unlock-cards-kit
python3 tools/kit.py add unlock-cards --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
