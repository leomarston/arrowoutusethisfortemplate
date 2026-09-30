# Settings page (`settings`)

The Settings page: notifications, sound / music / haptic toggles, links, and the Terms / Privacy info pages.

A full page opened by the home gear (PopupID.settings): the Notifications card, three square toggles (Sound / Music / Haptic) that write PlayerState.settings and apply at once, the support / Terms / Privacy links (InfoPage) and the version line. Links in ui.json `settings.links`.

## How the app uses it

```swift
_ = await app.popups.present(Popup<PopupResult>.settings)
```

## Open it in a Debug build

```
-pc.go settings
-pc.go home -pc.popup settings
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show settings          # files, what it uses, deps, who depends on it
python3 tools/kit.py export settings --out /tmp/settings-kit
python3 tools/kit.py add settings --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
