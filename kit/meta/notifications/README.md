# Notification prompt and local notifications (`notifications`)

Asks for notification permission once (first launch) and schedules the offline lives / event reminders.

NotificationPrompt asks over Loading on the first launch (game.json `notifications.*`) and schedules local notifications (lives full, the weekly contest ending) from GameCore's EventNotifications planner. No server: everything is local.

## How the app uses it

```swift
// boot: NotificationPrompt.askIfFirstLaunch(app); on background: NotificationPrompt.reschedule(app)
```

## Open it in a Debug build

```
-pc.reset 1
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show notifications          # files, what it uses, deps, who depends on it
python3 tools/kit.py export notifications --out /tmp/notifications-kit
python3 tools/kit.py add notifications --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
