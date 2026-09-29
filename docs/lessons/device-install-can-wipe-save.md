---
name: device-install-can-wipe-save
description: "devicectl install over an existing dev build gave a FRESH data container — the owner's progress was lost; back up the save first"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 67834757-7bc9-4e4f-a907-36f39cf8e3e8
  modified: 2026-09-28T01:00:08.420Z
---

2026-09-28 (mazeout / Arrow Out): I promised the owner "install over, your progress is kept", ran
`xcrun devicectl device install app` over the dev build installed the evening before (same bundle id,
same team), and the app came up with a brand-new data container (container metadata + Library/Application
Support/Save created at the install minute; the iOS notification prompt appeared again). The owner's
progress from the previous build was gone.

**Why:** a reinstall of a development-signed app is not guaranteed to keep its container (profile /
installer differences can make iOS treat it as a fresh install). I assumed App-Store-update semantics.

**How to apply:** before ANY device install over an app the owner has used:
1. `xcrun devicectl device copy from --device <id> --domain-type appDataContainer --domain-identifier <bundle>
   --source "Library/Application Support" --destination <backup dir>` (and Documents / Library/Preferences if the
   app uses them);
2. install;
3. `devicectl device info files … --domain-type appDataContainer` — if the container is new, copy the backup back
   with `device copy to` BEFORE the first launch;
4. never tell the owner "progress is kept" until step 3 proved it.
Related: [[phone-driver]], [[finish-the-whole-pipeline]].
