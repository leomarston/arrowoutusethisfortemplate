# Pause menu (`pause-menu`)

The in-level Pause popup: Sound and Haptic toggles, Resume, Quit, X.

PausePopup answers .primary (Resume), .secondary (Quit: the game then asks Quit Level?) or .close. The toggles write PlayerState.settings through PlayerStore and apply at once to the audio bus and haptics. Also defines SettingRow and PanelPairButton (reused by other popups).

## How the app uses it

```swift
// LevelFlow.pause() (the HUD pause button):
let r = await services.popups.present(Popup<PopupResult>.pause)
if r == .secondary { await confirmQuit() }   // Quit -> the quit-level popup
```

## Open it in a Debug build

```
-pc.go level -pc.level 5 -pc.popup pause
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show pause-menu          # files, what it uses, deps, who depends on it
python3 tools/kit.py export pause-menu --out /tmp/pause-menu-kit
python3 tools/kit.py add pause-menu --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
