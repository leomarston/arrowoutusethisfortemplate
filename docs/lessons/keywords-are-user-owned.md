---
name: keywords-are-user-owned
description: NEVER write App Store keywords — the user maintains them by hand in App Store Connect; ASC is the source of truth
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

**Never write the App Store `keywords` field.** The user researches and edits their keyword list by hand directly in the App Store Connect web UI. Treat ASC as the source of truth and sync keywords DOWN to `fastlane/metadata/<locale>/keywords.txt`, never up.

**Why:** Running `fastlane deliver` (the `upload_meta` lane) uploads every metadata file including `keywords.txt`, which silently overwrote a keyword list the user had spent significant effort on and had not saved anywhere else. It was unrecoverable — it had never passed through git. The user was (rightly) furious: *"DONT YOU FUCKING TOUCH THE KEYWORDS SECITON EVER AGAIN."*

**How to apply:**
- Before ANY metadata upload, GET the live keywords per locale and write them to disk first, so a subsequent deliver run is a no-op for that field.
- To change other store text, PATCH specific fields via `/v1/appStoreVersionLocalizations/{id}` with only those attributes (e.g. `description`, `promotionalText`) — omitting `keywords` from the payload means it cannot be touched. Verify keywords are unchanged in the PATCH response.
- Screenshot-only uploads must use the `upload_shots` lane (`skip_metadata: true`) added to both the app and template Fastfile — it cannot reach metadata at all.
- Gotchas learned alongside this: `whatsNew` must be OMITTED on a first version (else 409 STATE_ERROR); a 409 can also mean the user is editing the same field in the ASC UI concurrently — retry.
- Same principle generalizes: anything the user hand-authored in an external dashboard is theirs. Pull, don't push. Related: [[reco-build-state]].

EXTENDED 2026-09-10 to the DESCRIPTION as well — see [[never-touch-keywords-or-description]].
