---
name: infoplist-array-keys-need-a-base-plist
description: "INFOPLIST_KEY_UIBackgroundModes is not a real build setting — array plist keys need an xcodegen info: base plist"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-08-28T23:11:01.241Z
---

`INFOPLIST_KEY_UIBackgroundModes: location` in project.yml is **silently dropped**. Array-valued
Info.plist keys have no `INFOPLIST_KEY_` equivalent at all; only scalars do. The app builds, the
setting looks present in project.yml, and the shipped bundle simply has no `UIBackgroundModes`.

**Why:** this is the same class of failure as `INFOPLIST_KEY_UISupportedInterfaceOrientations__iPad`
(double underscore) — Xcode ignores what it does not recognise, so project.yml is never evidence.

**How to apply:** give the target an xcodegen base plist and put the array there. Xcode still
merges the scalar `INFOPLIST_KEY_*` settings into it, so keep those where they are:

```yaml
    sources:
      - path: App
    info:
      path: App/Info.plist
      properties:
        UIBackgroundModes: [location]
```

Then **verify on the BUILT plist, never on project.yml**:
`plutil -p build/.../MyApp.app/Info.plist | grep -A3 UIBackgroundModes`.

Found shipping [[podfind-build-state]]. Related: [[ipad-is-a-review-device]].
