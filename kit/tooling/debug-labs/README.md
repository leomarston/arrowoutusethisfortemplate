# Debug labs (ShellLab and friends) (`debug-labs`)

The Debug-only hosts: ShellLab pages (text, components, puppets, HUD, win, unlock...), glitch runs, frame watch.

Compiled only into Debug / Measure (`#if DEBUG || PC_MEASURE`, tools/harness_gate.py): ShellLab and its popup pages, the placeholder view, the GlitchRun stress path and FrameWatch. Each page writes Documents/lab-ready.json for captures.

## How the app uses it

```swift
// -pc.go shelllab -pc.lab <page>  ->  ShellDebugScreens.make("shelllab", app:)
```

## Open it in a Debug build

```
-pc.go shelllab -pc.lab text
-pc.go shelllab -pc.lab components
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show debug-labs          # files, what it uses, deps, who depends on it
python3 tools/kit.py export debug-labs --out /tmp/debug-labs-kit
python3 tools/kit.py add debug-labs --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
