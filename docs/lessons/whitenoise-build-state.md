---
name: whitenoise-build-state
description: WN white noise machine submitted 2026-08-23; synthesised colours + CC0 recordings, and the silent-app bug that nearly shipped
metadata:
  type: project
---

`whitenoise` = "White Noise machine App - WN", ASC app **6804452052**, submitted
2026-08-23 (version 1.0.0 build 1 + weekly/yearly subs all WAITING_FOR_REVIEW).
Built on the user's direct request, not from the ROUTINEAPPS queue.

The design decision worth keeping: **method per sound, stated honestly in the copy.**
The seven noise colours are synthesised live (a colour *is* a spectral slope, so a
"recording of pink noise" is a category error) and verified by `tools/dsp_check.swift`
to within 0.5 dB/oct of theory. Rain/ocean/stream are bundled CC0 1.0 field recordings,
because those are thousands of discrete random events that synthesis only approximates.
Fan/wind stay synthesised. See [[svg-art-pipeline]] for the equivalent art decision.

The user pushed back twice on synthesising everything ("dont be lazy"), and was right —
the nature loops are better as recordings. When they push back a second time on a
judgement call, treat it as a decision, not a question.

Related: [[verify-real-not-mock]], [[no-servers-not-no-libraries]],
[[localize-all-50-locales]], [[audio-apps-must-assert-on-signal]].
