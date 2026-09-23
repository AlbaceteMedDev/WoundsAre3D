# Print order — StrataMetric wound phantoms (STEP, revision B)

12 parts. Upload the twelve `.step` files. **Dimensions are in millimetres — do not scale.**

Revision B replaces the earlier STL set, which failed inspection: the hollow was offset
vertically rather than along the surface normal, leaving walls of 0.36 mm on P2 and 0.13 mm
on P10. Do not print any file from the earlier set.

## What changed

- **Exact geometry.** Every cavity is the analytic surface itself — sphere, cone, elliptic
  paraboloid, cylinder — not a triangulation of it. There is no faceting; tessellate at
  whatever tolerance your process wants.
- **Wall thickness is correct in every direction.** The internal void is kept 3.5 mm from
  every outer surface measured perpendicular to that surface, including the vertical and
  near-vertical cavity walls that failed before. Measured minimum on the delivered geometry:
  **3.500 mm**, and **3.000 mm** directly beneath the 0.5 mm top-face engravings.
- **Closed shells with powder escape.** Hollow blocks are fully closed, with two escape
  holes through the ±X side walls at y = ±33 mm. Nothing is trapped.
- **P5 and P6 are solid.** At 9 mm tall, hollowing leaves a void too thin to be worth it.

## Settings

| Setting | Value |
|---|---|
| Process | **MJF** (HP Multi Jet Fusion). SLS PA12 is an acceptable alternative |
| Material | Nylon PA12, **natural grey**. No dye, especially not black |
| Finish | **Standard / as-printed.** No polishing, shot peening, vapour smoothing, bead blasting or tumbling |
| Orientation | Cavity face up |
| Supports | Not applicable to powder bed; if you move to a supported process, **none inside any cavity** |
| Quantity | 1 of each; a second P6 is useful as a spare flat reference |

**Why MJF.** Powder bed needs no supports, so nothing ever touches a cavity surface; loose
powder clears through the escape holes; and the matte, diffuse, opaque surface is the best
target for the depth sensor under test. Glossy or translucent material corrupts depth
readings.

## Note to the shop

> Dimensions are in millimetres — do not scale. These are metrology reference parts: please
> do not sand, polish, tumble, shot-peen, vapour-smooth or otherwise finish any surface.
> Natural grey PA12, no dye. Each hollow block is a closed shell with two powder-escape holes
> in the side walls — please make sure all loose powder is cleared from the interior. Both
> faces carry functional engravings 0.4–0.5 mm deep that must be preserved.

## Parts

| File | Size (mm) | Material | Interior | Notes |
|---|---|---|---|---|
| `P1_hemisphere_r15.step` | 80 × 80 × 19 | 58.7 cm³ | hollow, 2 × Ø8 vents |  |
| `P2_hemisphere_r25.step` | 80 × 80 × 29 | 73.5 cm³ | hollow, 2 × Ø8 vents | deepest cavity, 25 mm |
| `P3_cone_r20_d10.step` | 80 × 80 × 14 | 52.2 cm³ | hollow, 2 × Ø6 vents |  |
| `P4_paraboloid_30x20_d12.step` | 80 × 80 × 16 | 54.5 cm³ | hollow, 2 × Ø8 vents |  |
| `P5_paraboloid_12x8_d4.step` | 80 × 80 × 9 | 56.9 cm³ | solid | smallest cavity — check fine detail |
| `P6_flat_plate.step` | 80 × 80 × 9 | 57.5 cm³ | solid | no cavity; engravings only |
| `P7_lobed_r18_d9.step` | 80 × 80 × 13 | 52.5 cm³ | hollow, 2 × Ø5 vents |  |
| `P8_trough_L40_r9_d8.step` | 80 × 80 × 12 | 55.6 cm³ | hollow, 2 × Ø4 vents |  |
| `P9_paraboloid_on_cyl_r60.step` | 80 × 80 × 22 | 73.7 cm³ | hollow, 2 × Ø8 vents | top face is a cylinder of R 60 mm |
| `P10_undermining_base.step` | 80 × 80 × 19 | 59.2 cm³ | hollow, 2 × Ø8 vents | Ø56.4 × 3 mm register pocket for L1/L2 |
| `L1_lid_concentric_r12.step` | Ø56 × 3 | 6.0 cm³ | solid | pairs with P10 |
| `L2_lid_offset6_r12.step` | Ø56 × 3 | 6.0 cm³ | solid | pairs with P10 |
| **Set** | | **606 cm³** | | |

L1 and L2 drop into P10's register pocket. If they bind, sand the **lid** edge, never the
pocket — the pocket depth sets the skin plane that the whole undermining measurement
references.

## Ordering the minimum first

Four parts give a working bench: **P6** (flat plate; its depth noise is the sensor floor),
**P1** (volume against a closed form), and **P10 + L1** (the whole undermining path).

## Reference values

`truth_step.json` carries the exact geometry of every part, and each block carries its own
values engraved on the underside at 4 mm cap height. **Measure the printed parts with
calipers on arrival and use the measured values as truth** — every process shrinks a little,
and the measured number is the one that matters.
