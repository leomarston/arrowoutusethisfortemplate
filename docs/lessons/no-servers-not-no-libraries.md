---
name: no-servers-not-no-libraries
description: "User's real constraint is NO SERVERS/backend to run — NOT a ban on client libs OR on public-endpoint network for an app's core function"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 10b31e1e-cc4c-4b19-a629-68bf07a6bc5f
---

The app-factory hard constraint the user actually cares about is **no servers / no backend to run and maintain** (no Firebase/Supabase/own-API/analytics-backend/AI-API). It is NOT a ban on client-side libraries. The repo's original CLAUDE.md line "Üçüncü parti SPM paketi ekleme (RevenueCat hariç)" over-stated this; the user corrected it: *"who said no external libraries, i said no external servers that will cause us to run a server."*

**Why:** An offline, on-device library (e.g. **LAME** for MP3 encoding, since iOS/AVFoundation cannot encode MP3) makes no network calls, needs no infrastructure, and does not violate the privacy/offline architecture. Bundling it is fine.

**How to apply:** Allow bundled offline client-side libraries when there's a genuine need (codecs, etc.). Still prefer SwiftUI + system frameworks and avoid dependency bloat. Keep enforcing: no servers, no analytics/tracking/AI network calls, RevenueCat is the only external SDK for subscription state. CLAUDE.md was updated 2026-07-15 to reflect this. Relevant to the [[app-factory-setup-state]] Reco build (an MP3 audio cutter that requires LAME).

**2026-07-22 — public-endpoint network policy (user confirmed):** when an app's CORE function inherently needs the network (speed test / WiFi tester, ping, etc.), it MAY call a reputable **public** endpoint — e.g. `speed.cloudflare.com`'s free `__down`/`__up` for throughput, `1.1.1.1` for ping. Rationale: there's no backend the user runs/maintains, so the "no servers" rule holds. Still hard-forbidden: analytics, tracking, AI calls, any own/Firebase/Supabase backend; all user data stays local. This unblocked queue app #2 `wifispeed` (Speed Test WiFi Tester) and #3 `netspeed`. Codified in CLAUDE.md's "Sert kisitlar".
