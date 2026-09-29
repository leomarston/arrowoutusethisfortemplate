---
name: signing-keychain-shadowing
description: errSecInternalComponent is usually a SECOND keychain in the search list holding a duplicate Distribution cert whose ACL denies codesign
metadata:
  type: project
---

`exportArchive codesign command failed ... errSecInternalComponent` during
`fastlane release` is most often **not** a missing partition-list. Diagnose it as:

```
security find-identity -v -p codesigning        # >1 identity with the SAME name = the bug
security list-keychains -d user                 # which keychain comes FIRST
```

A stale `manycode-build.keychain-db` held a copy of the same
`Apple Distribution: ...` certificate whose private-key ACL does not grant codesign
access. Sitting **earlier in the search list**, that copy is what codesign resolves to,
so signing fails. Pinning the identity by SHA-1 does **not** help — the hash matches
both copies.

Fix (now automatic in `scripts/signing_setup.py`): rewrite the search list to exactly
`[manycode-signing, login]` on every run instead of the old "append if missing", which
never evicted the shadow. Verify with:
`codesign --force --sign <SHA1> /tmp/Some.app` — it must print only "replacing existing
signature".

Also patched all `apps/*/fastlane/Fastfile` + `template`: `signingCertificate` is now
`dist_cert_sha1`, read from `keys/signing/dist.cer`, instead of the ambiguous string
"Apple Distribution". Found on rfdetector 2026-08-03. See [[signing-submit-gotchas]].
