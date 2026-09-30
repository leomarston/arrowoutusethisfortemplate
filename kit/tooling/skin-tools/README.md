# Skin tools (`skin-tools`)

Colour tokens, fonts, names, art slots, scenes and skin variants: build, check, recolour.

apps/<slug>/tools/skin (build.py, art.py, recolor.py, variant.py, codemod.py) + tools/uiart_gen.py over skin/*.json -> the generated Swift (SkinColors, SkinData, UIArt, SkinScenes) and Tuning/ui-colors.json.

## How the app uses it

```swift
python3 apps/mazeout/tools/skin/build.py --check && python3 apps/mazeout/tools/skin/art.py --check
```

## Open it in a Debug build

```
python3 apps/mazeout/tools/skin/build.py --check
python3 apps/mazeout/tools/skin/art.py --check
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Take it

```
python3 tools/kit.py show skin-tools          # files, what it uses, deps, who depends on it
python3 tools/kit.py export skin-tools --out /tmp/skin-tools-kit
python3 tools/kit.py add skin-tools --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
