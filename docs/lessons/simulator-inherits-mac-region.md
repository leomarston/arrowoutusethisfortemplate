---
name: simulator-inherits-mac-region
description: Simulators default to the Mac's region (en_TR here), putting comma decimals into en-US App Store screenshots
metadata:
  type: reference
---

This Mac is set to Turkey, so new simulators come up as `en_TR` with languages
`(en-TR, tr-TR)`. Any app whose number formatters follow the device locale then renders
comma decimals — `hiddendevice`'s first en-US screenshots read "12,4 σ" and "4,72 µT".

To a US reviewer that reads as a typo, and it ships in the store listing.

**How to apply:** before capturing marketing screenshots,
`xcrun simctl spawn <udid> defaults write -g AppleLocale -string en_US` and
`... AppleLanguages -array en-US`, then reboot the sim. Or pin `en_US_POSIX` in the app's
formatters — which is why `bugdetector` was immune and `hiddendevice` was not.
Worth re-checking already-shipped apps' screenshots for stray comma decimals.

Related: [[copyright-and-five-screenshots]].
