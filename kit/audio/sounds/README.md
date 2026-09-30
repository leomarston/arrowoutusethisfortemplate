# Sounds (audio engine) (`sounds`)

The audio engine: one-shot SFX by SoundID, the cue map (moment -> sound) and gains as data, music player.

AudioEngine (AVAudioEngine voices), SoundBank (the Sounds/<id>.wav files), AudioCues (Tuning/audio.json `cues` / `gain` into typed tables), MusicPlayer (music bus, off by default). Our sounds are synthesised by apps/mazeout/tools/audio (never recorded from another game). SoundBoard is the debug host.

## How the app uses it

```swift
if let cue = app.tuning.audio.cue("uiButton") { app.audio.play(cue, gain: Float(app.tuning.audio.gain(cue))) }
app.audio.play(.coinCollect, gain: 1)
```

## Open it in a Debug build

```
-pc.go soundboard
```

(`apps/mazeout/tools/run.sh` passes launch arguments; see `App/Support/LaunchArgs.swift`.)

## Known gaps

- The cue key `cues.arrowTap` is the reference puzzle's name; a generic move cue is open (docs/ROADMAP.md).

## Take it

```
python3 tools/kit.py show sounds          # files, what it uses, deps, who depends on it
python3 tools/kit.py export sounds --out /tmp/sounds-kit
python3 tools/kit.py add sounds --game <slug>   # dry run: what apps/<slug> lacks
```

`component.json` is the source of truth (files, uses, depends); `tools/kit.py check` verifies it in CI.
