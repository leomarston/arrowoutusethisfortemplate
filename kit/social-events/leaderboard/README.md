# Leaderboards (`leaderboard`)

The Leaderboard tab: Weekly / World / Country boards with the pinned player row and jump pill.

LeaderboardViews draws the tab bodies inside the page shell (header, tab strip, weekly countdown): the World and Country top lists and the player's weekly group, all from the offline social world.

## How the app uses it

```swift
app.router.go(.home(.normal, tab: .leaderboard))
```

## Open it in a Debug build

```
-pc.go leaderboard:world
-pc.go leaderboard:country -pc.socialCountry TR
-pc.go leaderboard:weekly -pc.socialScenario weeklyPodium
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- LeaderboardViews calls SocialFlows (events-engine), so taking the leaderboard takes the events engine and, through EventsDirector, the game loop. Its page frame (LeaderboardPageShell) is in social-ui.

## Take it

```
python3 tools/kit.py show leaderboard          # files, what it uses, deps, who depends on it
python3 tools/kit.py export leaderboard --out /tmp/leaderboard-kit
python3 tools/kit.py add leaderboard --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
