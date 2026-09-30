# The component kit: take any piece of the template

The kit (`kit/`) is the template's internal asset store: the pause menu, the home, the Shop, the leaderboards, the sounds,
the win celebration, each event, the HUD pieces, the puzzle modules and the tools are each a **component** you can look
up, open in a Debug build, and take into another game (or another project) with everything it needs. The code does not
move: a component is a `component.json` that points at files where they already live, so Arrow Out (`apps/mazeout`) keeps
building and every check that scans `App/` keeps working.

One tool drives it, from the repo root, Python 3 stdlib only: `python3 tools/kit.py <command>`.

## 1. Find a piece
| You want | Run |
|---|---|
| everything, or one category | `list`, `list --category popups` |
| search by words (id, title, text, files, strings, slots) | `search leaderboard`, `search pause` |
| the whole story of one component | `show pause-menu` |
| what it needs | `deps shop` (a tree) |
| what breaks if you remove it | `rdeps sounds` (dependents + the registration lines that name it) |
| a visual browse | open `kit/catalog.html` in a browser (search, filters, previews, dependency graph, export command) |

`show` prints: the files it owns (globs expanded), its tests, what it **uses** (art slots of `skin/art.json`, rig slots,
`SoundID` sounds, `audio.json` cues, strings keys, tuning keys as `file.json:key.path`, colour-token prefixes of
`skin/colors.json`), its direct and transitive dependencies, who depends on it, where other code **wires it in** (usually
one line: its `register()` call in `GameComponents.swift`), its totals (own files, with deps, with deps excluding core), its
closure budget (`maxClosure`, §3), how to open it (`-pc.*` launch arguments for `apps/<slug>/tools/run.sh`), its notes and
its known gaps.

## 2. Take a piece
**Into a game made from the template** (`apps/<slug>`, made by `tools/game.py new`): most pieces are already there.
```
python3 tools/kit.py add shop --game <slug>            # dry run (the default): COPY / ADD entry / DIFFERS / present
python3 tools/kit.py add shop --game <slug> --apply    # copies missing files, merges missing entries
```
`add` never overwrites a file that differs (it reports it). It merges a missing art slot, colour token, tuning key or
string row only when the JSON file round-trips byte for byte (so it never reformats a file); anything else goes to
`apps/<slug>/kit-pending.json` with its value, to merge by hand. String rows are appended to strings.tsv and to each l10n
table that lacks them. Afterwards run the skin and strings builds and `tools/game.py doctor` (the tool prints the commands).

**Anywhere else** (another repo, a review, a new project):
```
python3 tools/kit.py export pause-menu leaderboard shop --out /tmp/kit-out       # a folder
python3 tools/kit.py export pause-menu --out /tmp/pause.zip                     # a zip
python3 tools/kit.py export pause-menu --without core --out /tmp/pause-only     # the target has its own core
```
The export holds:
- `files/<repo path>`: the Swift of the component and of every transitive dependency, their tests, the tools they own,
  the art files of their slots (our own renders under `apps/<game>/art/`) and their sounds, plus each component's
  `component.json` + `README.md`;
- `data/`: only the entries the components use: `skin/art.json` (slots and rigs) + their manifest entries,
  `skin/colors.json` (tokens by prefix, the ui colour ids the tuning subset references, the palette entries they name),
  `tuning/<file>.json` (only the used keys), `tuning/audio.cues.json`, `strings/` (the rows of strings.tsv, keys.tsv and
  every l10n table);
- `MANIFEST.md` (components, files, assets, what they use, known gaps, anything skipped) and `CHECKLIST.md` (what the
  target must provide, the wiring lines that name each component and whether they came along, the data merges and
  regeneration commands, the launch arguments to verify each piece);
- `kit.json` (the same, machine-readable).

Never exported: `.env`, `keys/`, `machine.env`, signing files (`*.p8`, `*.p12`, `*.cer`, `*.key`, `*.mobileprovision`)
and anything `.gitignore` ignores (checked with `git check-ignore`).

**Out of a game** (the reference keeps everything; a new game may not want an event, the Shop, the celebration …):
1. `python3 tools/kit.py rdeps <id>`: who depends on it (take those out too, or keep it) and the lines that wire it in.
2. Delete its files (`show <id>` lists them) and its line in `apps/<slug>/App/GameComponents.swift`
   (`<Name>Registration.register()`), plus any other wiring line `rdeps` printed (a game director in
   `GameDirectors+G2.swift`, an event page in the events engine's `SocialPopups` / `SocialEntry`).
3. Nothing in core names it: its popup answers its fallback (Release) or shows the DEBUG pending panel, its screen / tab /
   strip / chip row is not drawn, its FX effect finishes at once with a log line, its warm-up items are skipped.
   Then remove it from `kit/` (or keep the folder for the next game) and run `python3 tools/kit.py check`.

## 3. What the dependencies mean
- `depends` = component ids whose types the component's sources name (plus `core`). `tools/kit.py scan <id>` computes
  them from the Swift (top-level types, per file owner); check warns when a source names a component outside its
  dependency closure. Export and `add` take the transitive closure.
- `wires` = components named **only to register or present them**: the game loop installs the directors (win, fail,
  boosters, tutorial, unlocks, FTUE, events), the events engine presents every event page and places the event bars.
  Removing a piece means editing the wiring lines that `rdeps` / `show` print (and `CHECKLIST.md` lists).
- **Registries, not hubs.** The shell's hubs (PopupHost, RootView, the router, the FX host, S2Hooks) name no panel,
  screen or effect of another component. They ask small registries in core (`App/Shell/ShellRegistry.swift`,
  `App/FX/FXOverlayView.swift` `FXEffects`), and each component registers itself from its own
  `<Name>Registration.swift` (`register()`); the game lists its components in ONE file, `App/GameComponents.swift`
  (core), installed lazily on the first question (`ComponentRegistry.installOnce`), so boot, tests and previews never
  depend on the order. What can be registered:

  | Registry | What a component gives | Who asks |
  |---|---|---|
  | `PopupPanels` | a `PopupPanelProvider`: which `PopupRequest`s it draws, which are full pages, the view, its `popup.variant` | PopupHost (`PopupContent`) |
  | `DebugPopups` | a `-pc.popup <id>` launcher (true = its id) | the router's `DebugPopupLauncher` |
  | `ShellPrewarmItems` | Loading warm-up renders, with an `order` (the reference list: S3 100-160, SOC2 200, S1 300-320, S2 400-460) | RootView `PopupPrewarm` |
  | `ShellWarmUps` | boot work behind Loading, ordered (the logo split, the Shop's store start) | RootView `PopupPrewarm` |
  | `ShellScreens` | the Loading screen + its art's lifetime, the home screen + `HomeScreenHooks` (its parked state for the router), Profile, the toast layer, home tab pages | RootView, the router, social-ui, the Shop |
  | `ShellArt` | art never released (`kept`) / decoded ahead (`preload`, ordered) | RootView `EventArtPolicy`, `HomeArtPreload` |
  | `PanelStrips` | a strip under the win panel / Level Failed, ordered (Rocket bar 10, Up & Away 20, Streak Race 30: the first that draws wins) | WinPanel, LevelFailedPopup |
  | `ContinueChips` | the multiplier chip row on Continue? | ContinuePopup |
  | `FXEffects` | an `FXEffectHandler` (celebration, Time Freeze, confetti, fireworks) or a layer builder (sparkles) | the FX host |
  | `SocialEvents` (social-ui) | the events engine behind `SocialEventsEngine` (joins, upkeep) | the leaderboard, the social model |

  A slot nobody fills is simply empty: that is how the fail flow draws Continue? and Level Failed without the Streak Race,
  and the win panel without any event.
- `core` is what every template-derived game already has: the app skeleton and its component list, the frozen contracts,
  Support, the router, the popup and FX hosts and the registries, the skin runtime (incl. the DEBUG-only missing-art
  stand-in `DebugPlaceholder` and Up & Away's slot table `UpAwayArt`), the generated skin Swift, the economy table
  (`ShellEconomy`), and the **whole GameCore target** (economy, lives, boosters, shop catalogue, the events' state
  machines, the offline social world, the session types incl. `SessionPlan` / `FeatureUnlock`). GameCore cannot be split
  by file: PlayerState embeds the events and social state, Events.swift drives every event, Economy reads the events and
  lives. Event and economy components name their GameCore files under `related`.
- `gaps` (with `status: needs-work`) records every coupling that makes a piece heavier than its name, and everything it
  still names of the reference puzzle, with the fix that would cut it (e.g. the booster ids are still `freeze` / `hint`;
  the events engine still wires each event page in its own hubs). Open items that are not couplings (a text fit to measure
  on the Mac) and the reasons a closure is what it is are `notes`.
- `maxClosure` = the budget of a component's closure: the files it and its transitive dependencies own, excluding core
  (the "with deps excluding core" total of `show`). `check` fails when a **stable** component exceeds the budget it
  declares (a needs-work component may declare one; it is enforced once the component is stable). The cleaned pieces
  carry today's count rounded up to the next 5, so a new coupling shows up in CI instead of in the next export: cut it, or
  raise the budget in `component.json` and say why. Where the rest is inherent it is written in `notes` (the fail flow
  runs inside the game loop, which plays sounds; an event page runs on the events engine).

## 4. Add or change a component
1. Pick the category and an id (kebab-case): `kit/<category>/<id>/component.json` + `README.md` (what it is, a usage
   snippet from the real call site, the launch arguments). Copy a neighbour as the pattern.
2. `files`: repo paths or globs (including its `<Name>Registration.swift`). Every Swift file under `apps/<game>/App`,
   `apps/<game>/Packages/*/Sources` and `apps/<game>/art/ui/code` must belong to exactly one component or to core. **An explicit path beats a glob**: a
   component that owns a folder (`App/Board/**`, `App/Shell/HUD/*.swift`, `App/Game/*.swift`, `App/Shell/Home/*.swift`,
   `App/Puzzles/SortPuzzle/**`) automatically owns a new file dropped there, and another component can take one file out
   of that folder by naming it. Two explicit claims, or two glob claims without an explicit one, fail. A new Swift file in
   a shared folder (`App/Shell/Popups`, `App/Shell/Components`, `App/Shell/Social`) fails `check` until you give it a home.
3. `python3 tools/kit.py scan <id>` shows what the sources use and which components they reference;
   `scan <id> --write` adds the missing `uses` entries (`--prune` also drops stale ones). Add `depends` / `wires` by hand
   from its "references" lines, and `uses.tuning` keys the scanner cannot see (typed Codable access, e.g.
   `rules.json:lives`).
4. If the shell must draw or run something of it (a popup panel, a screen or tab page, a warm-up render, an FX effect, a
   strip in another panel): write `<Name>Registration.swift` with `@MainActor enum <Name>Registration { static func
   register() { … } }` against the registries of §3, and add its line to `apps/<slug>/App/GameComponents.swift`. Never
   name the component from core, and prefer a registry slot to naming it from another component.
5. Declare `maxClosure` once it is clean (today's closure, rounded up to the next 5).
6. `python3 tools/kit.py catalog`, then `python3 tools/kit.py check -v` (errors fail; warnings list undeclared uses,
   references outside the closure and stale `wires`; `--strict` makes warnings fail too).

## 5. What CI checks (`.github/workflows/ci.yml`, Linux job)
`python3 tools/kit.py check` fails on: a schema error (required keys, known keys only, kebab-case id, category, folder
= `kit/<category>/<id>`, status, `needs-work` without `gaps`, a README missing); a file, test or `related` path / glob that
matches nothing, a secret path listed; a preview outside `apps/<game>/art/` or the component's `preview/`; an art slot,
rig, SoundID (+ its wav), cue, string key, tuning key or token prefix that does not exist; an unknown or self dependency,
a dependency cycle, a closure that does not reach core, core with dependencies; an unknown `wires` id or one that is
also a dependency; a stable component whose closure (excluding core) exceeds its `maxClosure`, or a `maxClosure` that is
not a whole number ≥ 1; an unowned or double-owned Swift file; a stale `kit/CATALOG.md` or `kit/catalog.html`.
`python3 tools/kit.py check --selftest` plants each failure and proves `check` catches it, and exports a component to a
folder and a zip.

## 6. Rules the kit keeps
- No backend, no network: the kit is files and a stdlib script.
- Previews are **our own** images: existing renders under `apps/<game>/art/` (listed by path, never copied into `kit/`), or
  screenshots of our own builds in `kit/<category>/<id>/preview/`. Never another game's captures, art, audio or levels
  (CLAUDE.md).
- The kit is genre-agnostic where the code is: a puzzle's pieces are the `puzzle` / `board` components; everything a
  component still names of the reference puzzle is written in its `gaps`.
