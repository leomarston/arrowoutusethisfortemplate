# Profile page (`profile`)

The Profile page (avatar, name, stats) with the Edit Profile (avatar grid) and Username popups.

Screen.profile, opened by the home avatar: the page header, the player card (avatar -> Edit Profile, the name -> Username), the stats. EditProfilePopup writes the avatar, UsernamePopup validates and writes the name (3-16 characters, blocklists), both through PlayerStore.

## How the app uses it

```swift
app.router.go(.profile)
let r = await app.popups.present(Popup<EditProfileResult>(.editProfile, style: PopupStyle(dim: .overPage), fallback: .close))
```

## Open it in a Debug build

```
-pc.go profile
-pc.go profile -pc.popup editProfile
-pc.go profile -pc.popup username
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show profile          # files, what it uses, deps, who depends on it
python3 tools/kit.py export profile --out /tmp/profile-kit
python3 tools/kit.py add profile --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
