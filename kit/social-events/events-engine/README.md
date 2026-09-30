# Events engine and weekly rotation (`events-engine`)

The events' state machines, schedule, finished states, the weekly rotation, the director, badges, announcements.

GameCore Events (join / progress / claim state machines over PlayerState.events, the calendar on the world clock, the finished-event state, the featured-events rotation), the win-streak multiplier, the app's EventsDirector (hooks after win / loss, the home auto-sequence), EventRotationPolicy, the week-start announcements and the home event badges. The individual events are separate components.

## How the app uses it

```swift
// after a win / loss (GameCore hooks), then the home queue:
Events.onWin(&state, at: now, world: world)
app.router.go(.event(.claw))
```

## Notes

- Kit decoupling step: it registers itself (EventsEngineRegistration.swift: the event popups in the popup host, their `-pc.popup` ids and warm-ups, and `SocialEvents.engine` for the social pages). Its closure (the game loop, the home, the tutorial, social-ui) is inherent: EventsDirector is a game director and the events live on the home.

## Open it in a Debug build

```
-pc.go home -pc.socialScenario rotation
-pc.go sociallab -pc.lab weeks
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- The event pages and popups are still wired in the engine's own hubs (SocialPopups, SocialEntry.makeEventScreen, EventBadges, EventsDirector: `kit.py rdeps <event>` prints the lines); a per-event registration like the shell's (ShellRegistry.swift) is the next step.

## Take it

```
python3 tools/kit.py show events-engine          # files, what it uses, deps, who depends on it
python3 tools/kit.py export events-engine --out /tmp/events-engine-kit
python3 tools/kit.py add events-engine --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
