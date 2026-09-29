---
name: apple-session-30-days
description: The Apple web session that create_app needs lasts 30 days; it expired 2026-08-20 19:26 and only spaceauth renews it
metadata:
  node_type: memory
  type: project
  originSessionId: 67834757-7bc9-4e4f-a907-36f39cf8e3e8
  modified: 2026-09-29T21:56:55.010Z
---

`fastlane create_app` is the ONLY way to register an app — and it needs an Apple ID **web
session**, which lasts **30 days** (`DES` cookie, `max_age: 2592000`).

The factory's session was minted **2026-07-21 19:26** and expired **2026-08-20 19:26**, which
is why app creation suddenly broke mid-`hearingtest`. Every app built between those dates rode
that one session.

**Why nothing else works** (all verified, don't re-litigate):
- `POST /v1/apps` → 403 *"The resource 'apps' does not allow 'CREATE'"* — not a permissions
  problem, the REST API simply has no app-creation endpoint.
- `produce` has **no `api_key` option** in fastlane 2.236.
- `POST iris/v1/apps` with the ASC JWT → 401; iris takes only the web-session cookie.

**Renewal (user must do it — password + 2FA on their device):**
```
fastlane spaceauth -u esaridogann@gmail.com
```
It writes `~/.fastlane/spaceship/esaridogann@gmail.com/cookie` itself. It also prints
`export FASTLANE_SESSION='...'` — put that in `.env`, which is what `scripts/routine.sh`
reads for the headless daily run.

**Verify, never infer (2026-09-28 mistake):** the cookie FILE's date proves nothing. The owner ran
spaceauth, it "didn't ask for a code", I read the Sep-14 file date and told him "still valid" — it was
not (the 30-day trust part had expired 09-20; ASC answered 401). The only check that counts:
`fastlane spaceauth -u esaridogann@gmail.com --check_session` → must NOT print "No valid session found",
plus a read-only iris/olympus GET that returns 200. A successful renewal always rewrites the cookie file
and ends with `export FASTLANE_SESSION=...`; if spaceauth asked nothing, it did not renew.

**fastlane 2.240.0 + Ruby 4 (2026-09-28):** spaceauth crashed with `undefined method 'parse' for class CGI
(NoMethodError)` in `fetch_service_key_from_signout` — Ruby 4 dropped `cgi` from the stdlib. Fixed in 2.240.1
("add cgi gem for Ruby 4 std removal"): `/opt/homebrew/bin/brew upgrade fastlane` (the ~/.local/bin/fastlane
wrapper execs the Homebrew one). If a login ever dies with a NoMethodError in spaceship, check the fastlane
version first.

**30 days is the MAXIMUM, not a promise (2026-09-30):** the owner's 09-28 11:22 renewal (2FA, --check_session VALID)
was already "No valid session found" at 09-30 00:55, under 2 days later, with the cookie file untouched. So run
`--check_session` right before every session-needing step (create_app, upload_privacy), and ask the owner for spaceauth
EARLY in a submit run (as soon as the privacy json is final), not at the end, so the 2FA round-trip overlaps the build.
What died was only `myacinfo` (no max_age = a session cookie); the 30-day `DES…` 2FA-trust cookie was still good, so the
owner's re-run logged in with NO password or code prompt (keychain password + DES trust) and DID renew, which is why
"asked nothing = did not renew" below is wrong; judge only by `--check_session` → "Valid session found".
Also: `set -a; . .env` exports a stale FASTLANE_SESSION that beats the fresh cookie file; `unset FASTLANE_SESSION` first.
upload_privacy printing "App data usage is already published" is fine: ASC re-publishes on each usage change
(lastPublished = the upload second); read back with AppDataUsagesPublishState + AppDataUsage.all to prove it.

**How to apply:** when `create_app` (or the privacy-details upload, same auth) returns
**"Unauthorized Access"**, check the cookie's `DES` entry age before debugging anything else —
it is almost always this. Renew ~every 30 days; set a reminder before the next expiry.

Related: [[account-and-no-browser]], [[signing-submit-gotchas]], [[reco-build-state]]
