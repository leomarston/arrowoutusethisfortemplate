# Avatars (`avatars`)

The avatar set (a default silhouette + 8 portraits) as skin slots, drawn in their frame.

AvatarArt maps an avatar index to its art slot (`avatar.<n>`) and draws the framed tile; used by the profile, the home top bar and the leaderboard rows (the simulated players' avatars).

## How the app uses it

```swift
AvatarTile(index: app.store.state.profile.avatar)   // see AvatarArt.swift for the view names
```

## Open it in a Debug build

```
-pc.go profile -pc.popup editProfile
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show avatars          # files, what it uses, deps, who depends on it
python3 tools/kit.py export avatars --out /tmp/avatars-kit
python3 tools/kit.py add avatars --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
