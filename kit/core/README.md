# Core (every game has it) (`core`)

App skeleton, contracts, save, tuning, skin runtime, router, popup and FX hosts, and all of GameCore.

What every game built from the template already has and every other component assumes: the composition root (AppModel, GameApp), the frozen contracts (screens, popups, presentation, audio, the puzzle board), launch arguments, logging, the motion clock, the player save (PlayerStore / PlayerState / StateStore), tuning loading, the skin runtime (Tokens, GameText, ArtStore, the generated UIArt / SkinColors / SkinScenes), the router and root view with its transitions, the popup host and its wiring hooks (S2Hooks / S3Hooks, which register the panels of other components), the FX host, GameButton and the whole GameCore target: random, persistence, IDs, motion, the puzzle session contract, meta rules, the generated GameConfig, AND the meta model (economy, lives, boosters, shop catalogue, the events' state machines, the offline social world). GameCore cannot be split by file: PlayerState embeds the events and social state, Events.swift drives every event, Economy reads the events and lives, so the event / economy components list their GameCore files under `related` instead of owning them. Export core only when the target is not template-derived.

## How the app uses it

```swift
// GameApp builds the one AppModel; every screen reads it from the environment.
@Environment(AppModel.self) private var app
let r = await app.popups.present(Popup<PopupResult>.pause)      // PopupHost: push, await the answer, pop
app.router.go(.home(.normal, tab: .home))                       // Router: full-screen states, no NavigationStack
app.fx.play(.sparkles(at: point))                               // FX host: Core Animation effects
app.store.mutate { $0.coins += 100 }                            // PlayerStore: the one save
```

## Wiring

- S2Hooks.swift / S3Hooks.swift / PopupHost `PopupContent` / FXOverlay are the registration points: a component's panel or effect is wired there with one line; removing a component means deleting that line.

## Open it in a Debug build

```
-pc.reset 1
-pc.go home
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- App-side helpers many components share are owned by core until they get a home of their own: Shop/ShopEconomy.swift (ShellEconomy, ShopFormat, ShopTitles), Game/EventRotationPolicy.swift (UpAwayArt), Board/Track.swift (keyframe tracks, used by the puppets), Home/ClawBar.swift (the Treasure Climb bar AND the Countdown / LiveCountdown / CountdownChip / EventWord helpers every event page uses), Components/DebugPlaceholder.swift.
- The hooks (S2Hooks, S3Hooks, SocialPopups, FXOverlay) name concrete panels: removing a component still needs a hand edit there (no registry yet).
- AppModel builds the social world, events and store for every game; a game without events still compiles them.

## Take it

```
python3 tools/kit.py show core          # files, what it uses, deps, who depends on it
python3 tools/kit.py export core --out /tmp/core-kit
python3 tools/kit.py add core --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
