---
name: audio-apps-must-assert-on-signal
description: A screenshot cannot prove an audio app makes sound — assert on the measured output level
metadata:
  type: feedback
---

For any app whose output is not pixels, at least one test must assert on the **real
signal**, not on the control's appearance.

**Why:** `whitenoise` ran, showed "Pause", animated its meter, and was completely
silent — the render callback's master gain had been set while `isPlaying` was still
false, so every sample was multiplied by zero. Every screenshot looked correct. A
white-noise app that makes no noise came within one step of being submitted.

**How to apply:** add a DEBUG `-ShowLevel` overlay that renders the engine's measured
output peak, then assert on it — once per distinct code path (synth vs
`AVAudioPlayerNode` playback) plus pause→silence. Set the live gain from exactly one
place and ramp toward a target inside the callback. Verify DSP offline against theory
(vDSP FFT + least-squares slope) so "this is pink noise" is a measurement.

Related: [[verify-real-not-mock]], [[interactive-bug-check]], [[whitenoise-build-state]].
