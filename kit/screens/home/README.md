# Home (main menu) (`home`)

The main menu: scene, top bar (avatar, coins, lives, gear), level plate, Play button and the 3-tab nav bar.

HomeView composes the home in SPEC-ui's z-order: the scene (backdrop + puppets, skin/scenes.json), the top bar (avatar -> Profile, coin pill -> Shop, lives pill, gear -> Settings), the LEVEL caption and plate, the Play button (normal / Hard / Super Hard looks) and the bottom nav (Shop / Home / Leaderboard tabs), and the home-return payout queue after a win (PayoutSequence: the ladder event's token, the streak step, coins flying into the pill; ui.json `homeReturn.*`). The event layer (badges, ladder bars), the Shop tab and the Leaderboard tab are other components wired in here. New files in App/Shell/Home are owned here unless another component names them.

## How the app uses it

```swift
// Router: the home is a Screen with a selected tab.
app.router.go(.home(.normal, tab: .home))
app.router.go(.home(.afterWin(summary), tab: .home))   // + the payout queue on arrival
```

## Open it in a Debug build

```
-pc.go home
-pc.go home -pc.level 40
-pc.go shelllab -pc.lab tabTour
-pc.go shelllab -pc.lab homeReturn
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show home          # files, what it uses, deps, who depends on it
python3 tools/kit.py export home --out /tmp/home-kit
python3 tools/kit.py add home --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
