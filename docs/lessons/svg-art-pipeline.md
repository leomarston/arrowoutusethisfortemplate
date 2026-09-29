---
name: svg-art-pipeline
description: "How to make REAL crafted art (not code-drawn shapes/SF Symbols) for factory apps — competitor-grounded SVG via multi-agent, rasterized with a WebKit tool"
metadata: 
  node_type: memory
  type: reference
  originSessionId: ae97ad8a-623d-439e-96e1-4e1876d608af
---

When an app needs real illustrated art (game sprites, mascots, prey) and the user rejects code-drawn shapes / SF Symbols as "slop / lazy":

1. **Ground it in competitors FIRST.** Don't invent the style. Pull real competitor screenshots: `curl -s "https://itunes.apple.com/lookup?id=<appid>&country=us"` → JSON `screenshotUrls` (swap the `/392x696bb.png` crop suffix for `/900x1600bb.png` to get hi-res). Download + Read them to see the actual art style. (For Kitz cat-game: top apps use BRIGHT THEMATIC backgrounds — blue water for fish, warm floor/cheese for mice — with realistic-COLORED prey, NOT neon-on-black.)

2. **Generate SVG art with a multi-agent Workflow** (fan out N candidates per asset, `effort:'high'`, schema `{svg:string}`, a shared brief + per-asset brief grounded in the competitor style). Journal (`.../subagents/workflows/<runid>/journal.jsonl`) has each agent's `{svg}` in `result`.

3. **Rasterize to preview/verify** with the native WebKit tool (no deps — cairo/rsvg/inkscape are NOT installed): `swift scripts/svg2png.swift <in.svg> <out.png> <size>`. Build a PIL contact sheet and Read it to pick the best per asset.

4. **Integrate:** rasterize the chosen SVGs to ~320px PNG into `Assets.xcassets/<name>.imageset/` with a Contents.json (single universal image, `"scale":"3x"`). Use `SKTexture(imageNamed:)` in SpriteKit and `Image("<name>")` in SwiftUI. Procedural backgrounds (water/floor/night) via PIL are acceptable as textures.

`scripts/svg2png.swift` (WebKit WKWebView snapshot → transparent PNG) is the reusable rasterizer. Contact-sheet the candidates on a dark AND light bg to judge.

## APP ICONS — same rule (user: "don't make it from code, make actual art… like your competitors' icons")

**Download the competitors' actual icons first:** `curl -s "https://itunes.apple.com/lookup?id=<id>&country=us"` → `artworkUrl512`; swap `512x512bb` → `1024x1024bb` for full res. (Use `curl`, not urllib — Python hits SSL CERTIFICATE_VERIFY_FAILED here.) Contact-sheet them and LOOK before designing.

**What the cat-game category actually does (all 5 top icons, 2026-08):** BRIGHT saturated background (warm yellow/orange, turquoise water, pink) — never dark; ONE bold subject filling the frame — a cute cartoon CAT FACE with huge eyes, or the PREY (orange goldfish / grey mouse), or a chunky PAW; FLAT friendly vector, thick shapes, no thin lines/glow/neon; no text; readable at 60px. My first Kitz icon (dark navy + thin glowing paw) broke every one of these.

**Generate via Workflow** with a brief that states the observed formula explicitly, viewBox `0 0 1024 1024`, background filling the full canvas, subject inside a ~880px safe area, no filters/text. 4 concepts × 2 variants is plenty. Then rasterize, contact-sheet the candidates AT ICON SIZE (~120px) directly under the competitor row to judge fit, pick, and install.

**Per-category formulas observed (download the icons and check before designing):**
- *Cat games* (Peppy Cat, Games for Cats): bright saturated bg + big cute cat face w/ huge eyes, or the prey, or a paw. Flat friendly vector.
- *Vintage cameras* (Dazz Cam, 1998 Cam, Huji): a BIG FRONT-ON CAMERA LENS as the hero — concentric metal/gold rings, deep coated glass with a specular crescent — on a colored retro camera BODY (cream top band + warm dark lower body, one orange flash accent). Dimensional and tactile, NOT flat, NOT a film strip, NOT dark/muddy. My first VinCam icon (dark film frame, PIL-drawn) was exactly the failure mode.

**The icon ASC displays comes from the BUILD**, not a separate upload — so changing it requires a new build number + release + resubmit, not just an asset swap. Verify what ASC actually serves: `GET /v1/builds/{id}/icons` → `iconAsset.templateUrl` (substitute {w}/{h}/{f}) and download it.

**Install:** rasterize to PNG and **resize to exactly 1024×1024** (the WebKit rasterizer returns 2× Retina — App Store rejects anything else) into `AppIcon.appiconset/AppIcon.png`; keep the source at `design/app_icon.svg` so it stays editable.
