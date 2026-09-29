---
name: screenshots-verify-content-not-count
description: HARD — a blank launch-screen capture shipped to all 50 storefronts and Apple approved it; count-based verification is not verification
metadata:
  type: feedback
---

**2026-09-07: camdetect shipped a flat WHITE screenshot as frame 1 to all 50 storefronts, and
Apple approved it.** The user found it, not me.

**What happened.** After reordering the rack I re-captured `rack.png` with a fixed 5-second
sleep after a cold `simctl launch`, and caught the launch screen before SwiftUI rendered. The
PNG had the right dimensions and a normal file size. `make_screenshots.py` built all 250
frames from it without complaint. My verification then counted `appScreenshots` per set and
asserted 5 per locale — which was true, and completely useless.

**The rule: never verify a screenshot by counting it.** Look at the pixels, and look at the
generated frame with your own eyes before upload — not just the raw capture, and not only the
one or two you happen to be curious about. I had viewed frames 1, 2 and 5 of an EARLIER build
and never looked at the regenerated set at all.

**Two guards now in place, keep them:**
- `scripts/make_screenshots.py` → `assert_rendered()` refuses any raw shot that is more than
  88% a single flat tone (launch screen, crashed view, empty state). Verified both directions.
- Capture loops should retry until the frame's mean luminance matches the app (a dark app
  averaging 250/255 is the launch screen), rather than trusting a fixed sleep.

Related: [[deliver-cannot-upload-screenshots]], [[copyright-and-five-screenshots]],
[[interactive-bug-check]].
