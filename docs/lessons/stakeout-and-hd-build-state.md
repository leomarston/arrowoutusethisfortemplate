---
name: stakeout-and-hd-build-state
description: Bug Detector - Stakeout (LIVE) and Hidden Device Detector - HD (in review), built 2026-08-26; one sensor each
metadata:
  type: project
---

Two detector apps built to submitted in one run, on the user's direct request.

- **`bugdetector` — "Bug Detector - Stakeout"**, ASC 6805516131. **APPROVED and LIVE
  2026-08-26.** Microphone ONLY. Leave the phone listening; come back to a timestamped tape
  of steady near-ultrasonic tones (15-22 kHz). Deliberately no live spectrum, no waterfall,
  no dB meter, no hero numeral — that rule is the separation from `soundanalyzer`. Aubergine
  #1A1024 / bone #F6EFE4 / SF Mono.
- **`hiddendevice` — "Hidden Device Detector - HD"**, ASC 6805518063, WAITING_FOR_REVIEW.
  Magnetometer ONLY. A strip-chart recorder whose paper advances only while your hand moves,
  so a spike marks a PLACE, and nothing is readable standing still. The factory's first
  LIGHT-locked app: cream chart paper #F4EFE2, sprocket margin, plotter magenta #B0176B.

**The design lesson worth keeping.** The first drafts of both were rejected by three
independent referees as too similar — to each other and to the four detector apps already on
the account. Both had picked near-identical limes 5° apart, HD's torch-glint was camdetect's
shipped code, Bug's Bonjour lane was listendetect's. What fixed it: **one sensor per app, no
sensor shared, no artifact shared**, and a split on VALUE (one thumbnail ~85% pale, the other
~85% deep) rather than on hue. Hue-splitting alone does not separate apps at thumbnail size.

**ASO:** "bug detector" is contaminated by INSECT-identifier apps (bug identifier pop 51;
Picture Insect and BugID are the top competitors), so every locale's subtitle disambiguates
to counter-surveillance in the first two words — German especially, where "Wanze" means both.
Deliberately NO camera keyword in any Bug locale despite that being the highest-traffic
anchor in the space: the app has no camera, and buying that traffic is a 2.3.1 overclaim.

Related: [[no-clone-apps]], [[distinctive-ui-not-slop]], [[localize-all-50-locales]],
[[revenuecat-cancel-does-not-throw]].
