---
name: app-naming-keyword-first
description: "App Store name MUST start with the exact seed keyword, verbatim — never drop/reorder words like 'app'"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

Every routine app's App Store **name must START WITH the exact seed keyword, verbatim** (title-cased), then an optional " - descriptor", ≤30 chars. Seed "app pomodoro" → **"App Pomodoro - Focus Timer"**, NOT "Pomodoro - Focus Timer".

**Why:** The user picks each app around a target keyword and relies on that keyword being at the very front of the store name (Apple weights the name heavily for ranking). I dropped the word "app" from "app pomodoro" (thinking it was ASO-dead filler) and named it "Pomodoro - Focus Timer" — the user was furious twice: *"IT IS CLEAR IN THE INSTRUCTIONS THAT YOU SHOULD HAVE THE AIMED KEYWORD IN THE BEGINNING"* and *"make sure you dont make this mistake on the next apps, SERIOUSLY."*

**How to apply:** Take the seed keyword exactly as given, title-case it, put it at the start of the store name. Do not drop, add, or reorder its words. App Store names are globally unique — if taken, KEEP the seed prefix and vary only the suffix (e.g. "App Pomodoro - Study Timer"). Create the app record with `fastlane create_app` (the Fastfile lane — NOT the `produce` CLI, whose --app_name arg parsing is broken and silently uses the wrong name). name.txt, ideas.yaml store_name, and the ASC record must all match.

**Source of truth = the ROUTINEAPPS.MD queue `Store name` column.** Each autonomous/daily run gets store_name from `scripts/routine_next.py` (which reads that column) and must use it **verbatim** — do NOT re-derive the name. The names in the queue are pre-vetted; just verify each still leads with its exact seed before building.

**create_app uses STORE name, not display name (fixed 2026-07-22):** `idea.py get` now emits `STORE_NAME` (= ideas.yaml `store_name`, falls back to `name`); `new_app.sh` substitutes `__STORE_NAME__`; the template Fastfile `create_app` lane uses `app_name: "__STORE_NAME__"`. Before this, create_app used the short display `name` (e.g. "WiFi Speed") for the ASC record instead of the seed-leading store name — a silent version of the exact mistake. `name` = short on-device label; `store_name` = App Store listing name that leads with the seed.

**Name globally unique — taken → append a suffix, keep the seed prefix (hit 2026-07-22 on `wifispeed`):** `create_app` for "Speed Test WiFi Tester" returned "The App Name you entered is already being used." Fix: keep the full seed prefix and add a short suffix → "Speed Test WiFi Tester Net" (still leads with the exact seed, ≤30). Update name.txt + ideas.yaml store_name + ROUTINEAPPS.MD queue + the Fastfile to the final unique name.

**Dash gotcha (caught 2026-07-22 on `wifispeed`):** a " - " should only ever precede a NON-seed descriptor (e.g. "App Pomodoro **- Focus Timer**", where "Focus Timer" is extra). If a seed's own last word lands after the dash, that's WRONG — it mislabels a seed word as a descriptor. Seed "speed test wi fi tester" → "Speed Test WiFi Tester" (full seed contiguous), NOT "Speed Test WiFi **- Tester**". Also render multi-token terms naturally ("wi fi" → "WiFi") without dropping content. Rule is written into ROUTINEAPPS.MD rule #2, the queue note, AND the cron/routine build prompt. Related: [[daily-routine]], [[keywords-are-user-owned]].
