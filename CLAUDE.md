# Game Template — working rules

This repo is a **template for mobile puzzle games**. One shared system (home, HUD, popups, shop, lives, coins, boosters,
events and tournaments, the offline "online-looking" leaderboards, store and release tooling) + a **puzzle module** you
plug in + a **skin** (characters, colours, art, sounds, texts) + a **config** (identity, economy, events, IAPs) = a game.

- **Reference game:** `apps/mazeout/` = *Arrow Out* (shipped 2026-09-30). It is the working example and the regression
  fixture while the template is extracted from it: it must keep building and passing its tests after every change.
- **Where the template work stands:** `docs/ROADMAP.md` (phases, decisions, what is done / next). Read it first in a new
  session and update it when a step lands. It replaces the factory's `PROJECT_LOG.md`, which is not in this repo.
- **How things work:** `README.md` (map, build/run, rename checklist, store pipeline) and `docs/lessons/README.md`
  (117 notes of pitfalls already paid for; check the matching group before any store, signing, payment, simulator or
  phone step).
- **Cloning / researching an original game:** `GAMEPROMPT.md` (Workflow tool) or `GAMEPROMPTMAX.md` (subagents).

## Hard rules
- **No backend.** Nothing we must run or maintain (no own API, Firebase/Supabase, analytics backend, AI API). The game
  plays offline; all player data is local (`Application Support/Save/player.json`). Network only for StoreKit/RevenueCat
  and, only if a specific game opts in, an ad-attribution SDK (off by default; added per game, never in the template).
- **Online features are a local simulation** (leaderboards, rivals, races): deterministic from a world seed + the clock,
  identical on every device, rewind-safe. Never add a server for them.
- **Real, never mock:** no placeholder/Lorem/stand-in content or debug art in a Release build (release gates check it).
- **Every visible number and colour comes from data** (tuning JSON, skin tokens, config), not new literals in Swift.
- **The template stays genre-agnostic:** nothing outside a puzzle module may assume arrows, tiles, coins or any
  specific mechanic.
- **Never weaken a failing test** to get green; fix the cause. Report honestly: say what was verified and what was not.
- **Secrets** live only in `.env` and `keys/` (git-ignored); this Mac's simulator/phone ids in `machine.env`
  (git-ignored). Never commit them, never print them.
- **Copy the category's conventions, never an original's assets**: no extracted art, audio, screenshots or levels of
  another game in shipped files or in git.

## Working here
- **Build / test (macOS only):** `apps/<slug>/tools/{gen,build,run,test,core}.sh` (see README §3). A cloud session has
  no Xcode: push to a `claude/**` branch and read GitHub Actions (`.github/workflows/ci.yml`: Linux content checks,
  core `swift test`, app build + unit tests on an iOS simulator).
- **Linux-runnable checks:** `python3 apps/mazeout/tools/strings/build.py --check`, `tools/release/meta.py audit`,
  `meta.py iap-check`, `tools/levels/bundle_check.py --publish`, `design/tools/validate_levels.py`.
- **Machine limits (16 GB Mac):** at most two builds at once, keep 15 GB free, one simulator per agent
  (`docs/lessons/max-two-parallel-builds.md`).
- **Store work** follows README §6 in order; run every script with `--dry-run` first and read results back.
- **If stuck:** write what was tried and the exact error into `docs/ROADMAP.md` (Blocked) and tell the owner; never
  fake success.

The earlier subscription-app factory rules (paywall, Restore gates, `ideas.yaml` queue, the `app-factory` skill) are
archived in `docs/archive/` and do **not** apply to games.
