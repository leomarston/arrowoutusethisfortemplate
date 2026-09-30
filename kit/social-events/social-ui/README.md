# Social list UI kit (`social-ui`)

Off-main-thread social lists: shaped text, CA rows, the recycling list, event page chrome, the social model.

SocialModel wraps the world + clock for the app (every query off the main thread); SocType shapes the row text with CoreText; SocRows / SocArt / SocList draw the 200-row lists as Core Animation layers; SocChrome holds the shared event chrome; SocialEntry / SocialPopups / SocialFlows plug the event screens and popups into the shell; SocScenario presets states for captures; SocialShells is the leaderboard / event page frame. SocialLab is the debug host.

## How the app uses it

```swift
// SocialEntry.makeEventScreen(.skyJump, app:) builds a full-screen event page;
// SocialPopups.present(request, app:) the event popups.
```

## Open it in a Debug build

```
-pc.go sociallab
-pc.go sociallab -pc.lab scroll:world
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- SocialShells / SocialModel name the home (HomeLive, HomeScene) and the profile (TopCanvas); SocialModel calls SocialFlows' hooks (events-engine, wired).

## Take it

```
python3 tools/kit.py show social-ui          # files, what it uses, deps, who depends on it
python3 tools/kit.py export social-ui --out /tmp/social-ui-kit
python3 tools/kit.py add social-ui --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
