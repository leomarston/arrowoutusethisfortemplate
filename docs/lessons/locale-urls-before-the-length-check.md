---
name: locale-urls-before-the-length-check
description: "tools/loc.py wrote privacy/support URLs after the char-limit check, so one over-long subtitle silently cost a locale both URLs and 409'd the submission"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-08-28T23:11:21.147Z
---

`tools/loc.py write()` validated the 30/30/170/4000 character limits and returned early on a
failure — **before** writing `privacy_url.txt` and `support_url.txt`. On `podfind` the Finnish
subtitle came out 31 chars; `fi` therefore shipped with no URLs, and nothing said so.

**Why it matters:** the damage surfaces only at the very end. `asc_submit.py` fails with
`STATE_ERROR.ENTITY_STATE_INVALID` and an `associatedErrors` block naming
`ENTITY_ERROR.ATTRIBUTE.REQUIRED` on `supportUrl` and `privacyPolicyUrl` — by *localization id*,
not by locale. Every locale needs its own copy of both; there is no inheritance.

**How to apply:** write the two URLs (and release notes) **first**, then report the length
failure and return False. Before submitting, also run the cheap direct check:

```bash
for d in fastlane/metadata/*/; do l=$(basename $d); [ "$l" = review_information ] && continue
  [ -f "$d/privacy_url.txt" ] || echo "MISSING privacy_url: $l"
  [ -f "$d/support_url.txt" ] || echo "MISSING support_url: $l"; done
```

If it has already reached ASC, patch the offenders in place: PATCH
`/v1/appStoreVersionLocalizations/{id}` with `supportUrl`, and
`/v1/appInfoLocalizations/{id}` with `privacyPolicyUrl` (they live on different resources).

Found shipping [[podfind-build-state]]. Related: [[localize-all-50-locales]].
