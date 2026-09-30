# The component kit

An internal "asset store" for the template: every piece of the reference game you might want in another game (the pause
menu, the home, the shop, the leaderboards, the sounds, the win celebration, an event, a puzzle module, a tool) is listed
here as a **component** you can look up, preview and take, without moving any code.

- **The code stays where it is** (`apps/mazeout/App`, `Packages/PathCore/Sources`, the tools). Arrow Out keeps building
  and its checks keep scanning the same folders. The kit is a catalog layer on top.
- **Browse:** open [`catalog.html`](catalog.html) in a browser (search, category filters, previews, dependency graph,
  a copy-able export command), or read [`CATALOG.md`](CATALOG.md). Both are generated; never edit them by hand.
- **Guide:** [`docs/guides/KIT.md`](../docs/guides/KIT.md) (taking a piece, adding a component, the rules CI checks).

## Layout

```
kit/
  README.md            this file
  CATALOG.md           generated: one table per category
  catalog.html         generated: the browsable page (plain HTML/CSS/JS, no external files)
  core/                what every template-derived game already has (component.json + README.md)
  <category>/<id>/     one folder per component
    component.json     id, title, category, summary, description, files (paths or globs), tests, related,
                       depends, wires, uses (art slots, rigs, sounds, cues, strings, tuning keys, skin token
                       prefixes), launchArgs, status (stable / needs-work) + gaps, preview, notes,
                       maxClosure (the closure budget CI enforces on stable components)
    README.md          what it is, how the app uses it (a Swift snippet), how to open it in a Debug build
    preview/           optional: OUR OWN screenshots only (or list existing images under apps/<game>/art/ in
                       component.json `preview`); never another game's captures
```

Categories: screens, popups, hud, meta, social-events, economy, audio, fx, board, puzzle, tooling.

## Take a piece

```
python3 tools/kit.py list                      # every component
python3 tools/kit.py search leaderboard        # find one
python3 tools/kit.py show pause-menu           # files, what it uses, deps, who uses it, where it is wired in
python3 tools/kit.py deps shop                 # what it needs (tree)
python3 tools/kit.py rdeps sounds              # what breaks if you remove it (+ the registration lines to edit)
python3 tools/kit.py export pause-menu --out /tmp/pause-kit          # a folder, or --out /tmp/pause.zip
python3 tools/kit.py export pause-menu --without core --out /tmp/p   # the target already has core
python3 tools/kit.py add shop --game <slug>    # dry run: what apps/<slug> lacks; --apply to copy / merge it
```

An export holds `files/` (the Swift, tests, tools and our own art / sound files, at their repo paths), `data/` (only the
skin art slots, colour tokens, tuning keys, strings rows and audio cues the components use), `MANIFEST.md` (what is in it)
and `CHECKLIST.md` (what the target must provide, where the pieces are wired in, how to verify). Secrets (`.env`, `keys/`,
`machine.env`, signing files) and git-ignored files are never exported.

## Honest dependencies

`depends` is what a component's sources really name (the scanner in `tools/kit.py scan` reads them), so taking a piece
takes what it needs. The shell's hubs (the popup host, the root view, the router, the FX host) name no component: each
component registers its panels, screens, warm-ups, effects and strips itself (`<Name>Registration.swift`), and a game lists
its components in one file, `apps/<game>/App/GameComponents.swift`. Panels that show another component's piece do it
through a slot (the Streak Race strip under Level Failed, the event strips under the win panel), so the fail flow needs no
event and the leaderboard no events engine. What still couples a piece more than its name suggests is written in its
`gaps` (with the fix that would cut it); what is inherent (the fail flow runs inside the game loop) in its `notes`.
`wires` lists components a piece names only to register or present them (the game loop installs the directors, the events
engine presents the event pages): those are the lines to edit when you remove one, and `show` / `rdeps` print them.

Each cleaned component declares `maxClosure`, the number of files its closure may hold (excluding core): a stable
component over its budget fails `check`, so a new coupling shows up in CI (docs/guides/KIT.md §3).

`python3 tools/kit.py check` (CI) keeps all of this true: every Swift file belongs to exactly one component or to core,
every referenced file / slot / sound / string / tuning key / token exists, the dependency graph is acyclic and closed,
every stable component is within its closure budget, and the generated catalog is fresh.
