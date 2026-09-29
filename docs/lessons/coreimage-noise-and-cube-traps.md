---
name: coreimage-noise-and-cube-traps
description: "CIRandomGenerator randomises ALPHA (premultiplied, so a colour matrix divides by it) and a .cube LUT needs CIColorCubeWithColorSpace; both silently corrupt the picture"
metadata: 
  node_type: memory
  type: reference
  originSessionId: fc7b699b-a869-4b18-8ef7-1c0149346fa1
  modified: 2026-09-09T17:08:11.890Z
---

Two Core Image traps found rebuilding `vincam`/`procam` on 2026-09-09. Both produce a
picture that is *wrong* rather than an error, and both scale with image size, so a
thumbnail can look right while the full-resolution save is ruined.

**1. `CIRandomGenerator` randomises alpha too, and CIImage colour is premultiplied.**
Apply a colour matrix straight to it and every channel is divided by that random alpha:
symmetric noise becomes strictly positive and heavy-tailed. Measured: the same grey-noise
matrix gives mean 215 with 51.8% of pixels above 250 on the raw generator, and mean 176
with 4.2% above 250 once composited over opaque black. In `vincam` this made the grain
stage BRIGHTEN a flat frame by up to 164 levels — worse at higher resolution because more
octaves apply — so a 12 MP photo developed to white while its 120 px thumbnail looked
fine. **Composite the generator over opaque black before any matrix.**
Related: `CIAdditionCompositing` sums ALPHA as well as colour and everything downstream
divides it back out — six opaque layers arrived at a sixth of mid grey. Use a *blend*
(`CILinearDodgeBlendMode`) to sum colour, and apply grain with `CIOverlayBlendMode` about
mid grey so the mean is preserved.

**2. A `.cube` LUT is written in sRGB; Core Image's working space is linear.** Plain
`CIColorCube` interpolates the table against linear values, so an **identity** cube
measurably shifts the image (5/255 on a 2x2x2) and every imported LUT is subtly wrong.
Use `CIColorCubeWithColorSpace` with `CGColorSpace(name: .sRGB)`; identity deviation
becomes 0.

**And a look rule that no test caught.** Film grain built as a *flat* octave ladder is
scale-invariant, which is what lets a 120 px chooser thumbnail predict the 3024 px save —
but run it out to 64/128 px cells and the coarse layers are soft blobs a tenth of the
frame across, and the photograph reads as mould-stained paper. `grainSD` is a
first-difference measure and nearly blind to a blob that wide, so the suite stayed green.
Keep the ladder flat, stop it at ~32 reference px, and **crop the finder out of the raw
capture at full resolution and look at it** before believing the numbers.

See [[camera-device-only-bug-classes]], [[verify-real-not-mock]], [[fixture-photography]].
