# Core (every game has it) (`core`)

App skeleton, contracts, save, tuning, skin runtime, router, popup and FX hosts, and all of GameCore.

What every game built from the template already has and every other component assumes: the composition root (AppModel, GameApp) and the game's component list (GameComponents.swift: one `<Name>Registration.register()` line per component), the frozen contracts (screens, popups, presentation, audio, the puzzle board, IntroStyle), launch arguments, logging, the motion clock, the player save (PlayerStore / PlayerState / StateStore), tuning loading, the skin runtime (Tokens, GameText, ArtStore and its DEBUG-only missing-art stand-in DebugPlaceholder, the generated UIArt / SkinColors / SkinScenes, Up & Away's slot table UpAwayArt), the router and root view with their transitions, the popup host, the FX host, and the registries they ask instead of naming other components (ShellRegistry.swift: popup panels, `-pc.popup` launchers, Loading warm-up items and boot work, panel strips and slots, screens and tab pages, kept / preloaded art, the home screen's hooks; FXOverlayView.swift `FXEffects`: effect handlers and layer builders), S2Hooks (the app reference, the offers' Shop route), the economy table (ShellEconomy) and the event names / outcome log lines, GameButton, and the whole GameCore target: random, persistence, IDs, motion, the puzzle session contract (incl. SessionPlan and FeatureUnlock), meta rules, the generated GameConfig, AND the meta model (economy, lives, boosters, shop catalogue, the events' state machines, the offline social world). GameCore cannot be split by file: PlayerState embeds the events and social state, Events.swift drives every event, Economy reads the events and lives, so the event / economy components list their GameCore files under `related` instead of owning them. Export core only when the target is not template-derived.

## How the app uses it

```swift
// GameApp builds the one AppModel; every screen reads it from the environment.
@Environment(AppModel.self) private var app
let r = await app.popups.present(Popup<PopupResult>.pause)      // PopupHost: push, await the answer, pop
app.router.go(.home(.normal, tab: .home))                       // Router: full-screen states, no NavigationStack
app.fx.play(.sparkles(at: point))                               // FX host: Core Animation effects
app.store.mutate { $0.coins += 100 }                            // PlayerStore: the one save
```

## Notes

- Kit decoupling step (docs/ROADMAP.md): PopupHost, RootView, the router, the FX host and S2Hooks name no panel, screen or effect of another component any more: each component registers itself (its `<Name>Registration.swift`), and GameComponents.swift lists them. `kit.py rdeps <id>` / `show <id>` print that one line (plus any wiring by other components).
- Moved out of core in that step: ClawBar.swift (to claw-challenge; its shared chrome to home's EventBarChrome.swift, the countdowns to social-ui's Countdown.swift), the shop formats (economy-ui), Board/Track.swift (the arrow board's), S3Hooks.swift (split into the components' registrations).

## Open it in a Debug build

```
-pc.reset 1
-pc.go home
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- AppModel (the composition root) builds the social world, the events and the store for every game, and picks the puzzle module (ActivePuzzle in Contracts/PuzzleBoardContract.swift names ArrowEscapeEntry / SortPuzzleEntry; AppModel names the arrow board's BoardEngine for its warm-up): a game without events still compiles them.
- The debug harness is named directly inside `#if DEBUG || PC_MEASURE` (Router: GlitchRun; FXOverlayView: FrameWatch; ShellContract: DebugScreens), and RasterCache.swift names ui-chrome's PanelButtonStyleColors (its warm-up key).
- ShellEconomy (Shop/ShopEconomy.swift, the economy table) and UpAwayArt (Components/UpAwayArt.swift, one event's slot ids) stay in core: the shell's own event-art and rotation policies read them, and several components name them.

## Take it

```
python3 tools/kit.py show core          # files, what it uses, deps, who depends on it
python3 tools/kit.py export core --out /tmp/core-kit
python3 tools/kit.py add core --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
