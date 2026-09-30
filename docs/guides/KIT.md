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
`skin/colors.json`), its direct and transitive dependencies, who depends on it, where other code **wires it in**, its
totals (own files, with deps, with deps excluding core), how to open it (`-pc.*` launch arguments for
`apps/<slug>/tools/run.sh`) and its known gaps.

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

## 3. What the dependencies mean
- `depends` = component ids whose types the component's sources name (plus `core`). `tools/kit.py scan <id>` computes
  them from the Swift (top-level types, per file owner); check warns when a source names a component outside its
  dependency closure. Export and `add` take the transitive closure.
- `wires` = components named **only to register or present them**: the game loop installs the directors (win, fail,
  boosters, tutorial, unlocks, FTUE, events), the home hosts the Shop and Leaderboard tabs, the events engine presents
  every event page. Without this, the graph would be one knot; with it, removing a piece means editing the wiring lines
  that `rdeps` / `show` print (and `CHECKLIST.md` lists).
- `core` is what every template-derived game already has: the app skeleton, the frozen contracts, Support, the router,
  the popup and FX hosts and their hook files (S2Hooks / S3Hooks), the skin runtime, the generated skin Swift, and the
  **whole GameCore target** (economy, lives, boosters, shop catalogue, the events' state machines, the offline social
  world). GameCore cannot be split by file: PlayerState embeds the events and social state, Events.swift drives every
  event, Economy reads the events and lives. Event and economy components name their GameCore files under `related`.
- `gaps` (with `status: needs-work`) records every coupling that makes a piece heavier than its name, with the fix that
  would cut it: e.g. the fail flow draws the Streak Race strip (StreakBanner.swift), the event pages share helpers that
  live in each other's files, the claw bar and the Countdown helpers share ClawBar.swift (in core for now).

## 4. Add or change a component
1. Pick the category and an id (kebab-case): `kit/<category>/<id>/component.json` + `README.md` (what it is, a usage
   snippet from the real call site, the launch arguments). Copy a neighbour as the pattern.
2. `files`: repo paths or globs. Every Swift file under `apps/<game>/App`, `apps/<game>/Packages/*/Sources` and
   `apps/<game>/art/ui/code` must belong to exactly one component or to core. **An explicit path beats a glob**: a
   component that owns a folder (`App/Board/**`, `App/Shell/HUD/*.swift`, `App/Game/*.swift`, `App/Shell/Home/*.swift`,
   `App/Puzzles/SortPuzzle/**`) automatically owns a new file dropped there, and another component can take one file out
   of that folder by naming it. Two explicit claims, or two glob claims without an explicit one, fail. A new Swift file in
   a shared folder (`App/Shell/Popups`, `App/Shell/Components`, `App/Shell/Social`) fails `check` until you give it a home.
3. `python3 tools/kit.py scan <id>` shows what the sources use and which components they reference;
   `scan <id> --write` adds the missing `uses` entries (`--prune` also drops stale ones). Add `depends` / `wires` by hand
   from its "references" lines, and `uses.tuning` keys the scanner cannot see (typed Codable access, e.g.
   `rules.json:lives`).
4. `python3 tools/kit.py catalog`, then `python3 tools/kit.py check -v` (errors fail; warnings list undeclared uses,
   references outside the closure and stale `wires`; `--strict` makes warnings fail too).

## 5. What CI checks (`.github/workflows/ci.yml`, Linux job)
`python3 tools/kit.py check` fails on: a schema error (required keys, known keys only, kebab-case id, category, folder
= `kit/<category>/<id>`, status, `needs-work` without `gaps`, a README missing); a file, test or `related` path / glob that
matches nothing, a secret path listed; a preview outside `apps/<game>/art/` or the component's `preview/`; an art slot,
rig, SoundID (+ its wav), cue, string key, tuning key or token prefix that does not exist; an unknown or self dependency,
a dependency cycle, a closure that does not reach core, core with dependencies; an unknown `wires` id or one that is
also a dependency; an unowned or double-owned Swift file; a stale `kit/CATALOG.md` or `kit/catalog.html`.
`python3 tools/kit.py check --selftest` plants each failure and proves `check` catches it, and exports a component to a
folder and a zip.

## 6. Rules the kit keeps
- No backend, no network: the kit is files and a stdlib script.
- Previews are **our own** images: existing renders under `apps/<game>/art/` (listed by path, never copied into `kit/`), or
  screenshots of our own builds in `kit/<category>/<id>/preview/`. Never another game's captures, art, audio or levels
  (CLAUDE.md).
- The kit is genre-agnostic where the code is: a puzzle's pieces are the `puzzle` / `board` components; everything a
  component still names of the reference puzzle is written in its `gaps`.
