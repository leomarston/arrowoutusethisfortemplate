---
name: idfa-declaration-and-invalid-binary
description: adding an ad SDK needs usesIdfa=true or the version goes INVALID_BINARY with no readable reason; detach/re-attach the build to clear that stuck state
metadata:
  type: reference
---

**Adding the Meta SDK made the version go `INVALID_BINARY` with an `UNRESOLVED_ISSUES` submission
and no readable reason anywhere in the API.** The binary was fine — signed correctly (app AND all
three embedded frameworks with the distribution cert), every privacy manifest present, every
Info.plist key correct, and `altool --validate-app` got all the way to "bundle version already
used", which only happens after every content check passes.

**The cause: `usesIdfa` was `null`.** The factory's `deliver` calls carried
`submission_information: { add_id_info_uses_idfa: false }`, which was true before the SDK and false
after it. Apple's automated check compares that answer against the binary, and an app linking an ad
SDK while answering "no IDFA" is rejected. Nothing says so out loud — the only clue is
`usesIdfa: null` in the appStoreVersion attributes.

Fix in `fastlane/Fastfile`, in EVERY lane that calls deliver:

    submission_information: {
      add_id_info_uses_idfa: true,
      add_id_info_tracks_install: true,     # we attribute installs to ads
      add_id_info_tracks_action: false,
      add_id_info_serves_ads: false,        # no ads shown inside the app
      add_id_info_limits_tracking: true,    # ATT is honoured
      export_compliance_uses_encryption: false
    }

`/v1/idfaDeclarations` is retired (404). Patch the attribute instead:
`PATCH /v1/appStoreVersions/<id>` with `{"attributes": {"usesIdfa": true}}`.

**CORRECTION (2026-09-29, Arrow Out review): the Fastfile hash above does NOTHING.** fastlane 2.240.1's deliver
never reads any add_id_info_* key (grep deliver/lib + spaceship/connect_api: no uses_idfa anywhere; only the retired
tunes AppSubmission class names them), and deliver reads submission_information only when submit_for_review is true,
which the factory lanes never set. The PATCH is the only fix, and it must land BEFORE the review submission is created:
`python3 scripts/asc_submit.py --slug <slug> [--bundle <id>] --uses-idfa` (opt-in flag, PATCH + read-back, exits if not
true). Also: the honest tracks_action answer for an app that sends purchase/level events is YES, not false.

**THE ACTUAL CAUSE, found after three failed builds: `NSPrivacyTracking=true` with an EMPTY
`NSPrivacyTrackingDomains`.** Apple validates the pair — claim tracking and you must name at least
one domain, or it is ITMS-91064 "invalid tracking information" and the build fails as
INVALID_BINARY. I emptied that array deliberately, over-applying Meta's "do not add our domains"
guidance, and it cost builds 6, 7 and a lot of time.

Declare exactly what FBSDKCoreKit declares in its own bundled manifest:

    <key>NSPrivacyTracking</key><true/>
    <key>NSPrivacyTrackingDomains</key>
    <array><string>ep1.facebook.com</string></array>

That changes no runtime behaviour — the SDK already declares that domain, so it is already subject
to Apple's ATT block. What must NOT go there is `graph.facebook.com` or `www.facebook.com`: those
carry the SDK's non-tracking traffic too, and listing them makes iOS block the SDK outright for
everyone who declines. Meta's warning and Apple's rule are both satisfied by naming ep1 only.

**`INVALID_BINARY` is STICKY.** It does not clear by cancelling the submission, by uploading a new
build, or by waiting — I uploaded build 7 and polled for ten minutes with no change. What clears it
is forcing ASC to re-evaluate by detaching and re-attaching the build:

    PATCH /v1/appStoreVersions/<id>/relationships/build   {"data": null}
    PATCH /v1/appStoreVersions/<id>/relationships/build   {"data": {"type":"builds","id":"<id>"}}

State went straight back to `PREPARE_FOR_SUBMISSION` and the next submit held. Much cheaper than
opening a new version record, which was the other option.

**Apple's validation is ASYNCHRONOUS, so checking straight after a submit proves nothing.** Both
failed builds reported `WAITING_FOR_REVIEW` seconds after submitting and only flipped to
INVALID_BINARY minutes later. I reported success twice on that basis and was wrong twice. **Poll
for at least 15 minutes** before believing a submission held — a good build stays put across the
whole window.

Related: [[meta-sdk-wiring]], [[submit-without-subscriptions]] — always re-read state after a
submit rather than trusting the script's own success message.
