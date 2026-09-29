---
name: ipad-needs-all-four-orientations
description: A universal app must declare all four iPad orientations or the upload is rejected 409 for multitasking
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f36d1ca2-433b-47f8-a91f-5ad7182f767a
  modified: 2026-08-31T09:02:59.255Z
---

Any app with `TARGETED_DEVICE_FAMILY: "1,2"` must list **all four** orientations for iPad, even when
the app is portrait-only by design. Otherwise `altool` rejects the upload:

    Validation failed (409) Invalid bundle. The "UIInterfaceOrientationPortrait" orientations were
    provided for the UISupportedInterfaceOrientations Info.plist key ... but you need to include all
    of the "...Portrait,...PortraitUpsideDown,...LandscapeLeft,...LandscapeRight" orientations to
    support iPad multitasking.

**How to apply** — in `project.yml`, keep the iPhone key portrait-only and give the iPad key all four
as a space-separated string (xcodegen splits it into the array):

    INFOPLIST_KEY_UISupportedInterfaceOrientations: UIInterfaceOrientationPortrait
    INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad: "UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight"

Note the key is `_iPad` with ONE underscore. Verify with `plutil -p` on the BUILT Info.plist, not the
project file — see [[infoplist-array-keys-need-a-base-plist]] for the related trap where an array-valued
`INFOPLIST_KEY_*` is silently dropped. This costs a full archive+upload cycle when missed, because it
only surfaces at the very end of the upload. Related: [[ipad-is-a-review-device]].
