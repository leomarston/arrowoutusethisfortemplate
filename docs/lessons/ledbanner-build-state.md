---
name: ledbanner-build-state
description: "LED Banner - Dot Matrix Sign: one texel = one lamp; the SwiftUI shader traps and the 4.3 separation from partylights/strobelight/teleprompter"
metadata:
  type: project
---

"LED Banner - Dot Matrix Sign" (slug `ledbanner`, app 6807578500, UTILITIES, #FFB000) — built
2026-09-02. The phone becomes a sign someone standing in FRONT of it reads across a room.

**The identity, and it is one decision:** the message is rasterised by CoreText at the panel's
REAL row count — a bitmap literally 24 pixels tall, not 24 points and not 24×3 — so one pixel of
the bake is one lamp, and the UNLIT lamp field stays visible across the whole panel. Every
competitor draws big anti-aliased text and lays a dot texture over it; that is why theirs read as
a font and this reads as hardware.

**SwiftUI shader traps, all found the hard way:**
1. A `Shader` used as a **ShapeStyle fill silently draws nothing**. Proven by filling green
   underneath: the green survived, so geometry was fine and the shader never ran. Use
   `.colorEffect()`.
2. `panel.read(uint2)` addresses ABSOLUTE texels and SwiftUI does not guarantee the texture keeps
   the UIImage's pixel dimensions. Sample in NORMALISED space with `filter::nearest` instead —
   scale-independent, and still an exact fetch so the matrix does not blur back into text.
3. Split the scroll into whole + fractional parts applied in DIFFERENT spaces: the fraction
   shifts the SAMPLING POSITION before it is divided into cells (lamps glide sub-cell), the whole
   part shifts the COLUMN INDEX (the message advances). Both on the column index truncates the
   fraction, so "smooth" and "stepped" render identically and the stepped toggle does nothing.
4. Orientation: settle it on the CPU. `PanelBakeTests` renders an "L" as ASCII art and asserts
   its foot is on the bottom row — two build-and-screenshot cycles were wasted guessing at pixels
   before writing that test.
5. The Metal toolchain is a separate 705 MB download: `xcodebuild -downloadComponent MetalToolchain`.

**Geometry:** pitch = min(height/(rows+2), width/26). From height alone a portrait phone gives
eleven visible lamps and auto-fit shrinks every message into illegibility. The band is exactly
panelRows tall so it centres instead of hanging off the top. STILL mode auto-fits (a still sign
must show all of itself); moving modes never shrink. The read-distance estimate is measured from
the actual baked cap height, derated 0.72 for the gaps between lamps, and rounded DOWN — and it
describes the BOARD, not the small bench preview.

**4.3 separation, enforced in code:** no pixel is lit except as part of the typed message. No
strobe, pulse, colour-wash or blank-bright mode (that is `partylights`), no Hz/duty-cycle/BPM/
tap-tempo (that is `strobelight`), no camera, no recording, no vertical script scroller (that is
`teleprompter`). Also: no forced landscape — `requestGeometryUpdate` is refused unpredictably
with no way to explain it to the user, so the board follows the device.

Free tier is a complete sign: all three motions, both polarities, mirror (a shop window is read
through glass), the full-screen board, 24 rows, 3 saved signs, and the Essentials phrases —
which lead with "I'M DEAF — PLEASE TEXT ME", because someone who cannot speak should not meet a
paywall. Related: [[strings-escape-decode]], [[disk-fills-fast-clean-archives]].
