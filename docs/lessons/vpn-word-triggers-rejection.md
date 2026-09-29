---
name: vpn-word-triggers-rejection
description: Apple's automated scan rejects an app 2.1.0 for "VPN functionality" when the WORD VPN merely appears in its strings or description — check the binary before believing the finding, then delete the word
metadata:
  type: feedback
---

`tvremote` build 4 was rejected 2.1.0 with *"An automated analysis indicates the app contains VPN
functionality"* and the three standard questions about what the VPN collects. The app is a LAN TV
remote. It has never had a line of VPN code.

**Prove it before you change anything.** iOS VPN capability is impossible without all three of:
`NetworkExtension.framework` linked, the `com.apple.developer.networking.networkextension`
entitlement (which Apple must grant the account), and a packet-tunnel provider **app extension**.
Check in this order:
```
otool -L Payload/App.app/App | grep -i networkextension
codesign -d --entitlements :- Payload/App.app
ls Payload/App.app/PlugIns          # a VPN cannot exist without one
```
No PlugIns directory = the finding is a false positive, and you can say so with evidence.

**The real trigger is the word.** Any honest app that explains *why it cannot reach something* will
name a VPN as a cause. On tvremote that was five strings × ten languages inside the binary plus one
sentence in each of ten store descriptions. A keyword scanner cannot tell a capability claim from a
troubleshooting note.

**The fix, three parts:**
1. Delete the word from the app AND every localized listing; keep the meaning — *"a privacy app
   that reroutes your phone"* is truer to a non-technical reader anyway. (Expect orphan strings
   from old copy revisions to be among the hits; delete those outright.)
2. Answer Apple's three questions in **App Review Information** — they explicitly ask for it there.
   That field caps at **4,000 characters**, so budget the whole notes file, not just the addition.
3. Reply in the ASC message thread. There is no public API endpoint for review correspondence, and
   the browser is off-limits for App Store Connect, so draft the text and hand it to the owner.

Keep code that *skips* VPN interfaces (`utun*`, `ipsec*`) when choosing the Wi-Fi interface — it
exists to ignore tunnels, and those literals are ≤15 bytes so Swift's small-string optimisation
keeps them out of the strings table anyway.

Related: [[tvremote-build-state]], [[honesty-copy-no-vendor-impossibility]] (honest copy causing
review trouble is a pattern worth watching), [[account-and-no-browser]].
