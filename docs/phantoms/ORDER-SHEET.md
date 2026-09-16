# Print order — StrataMetric wound phantoms

12 parts. Upload the twelve `.stl` files in this archive. **Dimensions are in millimetres —
do not scale.**

The blocks are **hollow**: an open-bottomed shell with a solid rim, a solid central pad and a
3.5 mm ceiling, ribbed for stiffness. The void is open and connected, so nothing is trapped and
no drain holes are needed. Minimum material thickness is 3.5 mm. Total material for the set is
about **454 cm³**.

## Settings

| Setting | Value |
|---|---|
| Process | SLA / MSLA resin, **or FDM** — see below |
| Material | Any **opaque** grey or beige. Never clear or translucent |
| Layer height | 0.05 mm resin, or 0.15 mm FDM |
| Orientation | Cavity face up, open side down on the plate |
| Supports | **None inside the cavity** |
| Infill (FDM only) | 15–20 %, 3 perimeters |
| Finish | As-printed. No sanding, tumbling, bead blasting or vapour smoothing |
| Quantity | 1 of each; a 2nd P6 is useful as a spare flat reference |

**Process choice.** These are measured with calipers on arrival and the measured values become the
reference, so print-to-CAD accuracy is not the binding constraint — iPhone LiDAR resolves ±1–3 mm,
so even FDM at ±0.3 mm is far better than the instrument under test. Print FDM first; move to
resin only if the surface finish proves limiting. If ordering resin, standard grey is fine;
premium engineering resins buy precision you cannot use here.

**Opacity is the one hard requirement.** Clear and translucent resins let light penetrate and
scatter beneath the surface, which corrupts depth readings.

## Note to the shop

> Dimensions are in millimetres — do not scale. Parts are hollow with an open bottom; print cavity
> face up with no supports inside the cavity. Both faces carry functional engravings 0.4–0.5 mm
> deep that must be preserved: a reference line and fiducial dots on the top face, a text spec
> plate on the bottom pad. These are metrology reference parts, so please do not sand, tumble or
> smooth any surface. Material must be opaque — no clear or translucent resin.

## Parts

| File | Size (mm) | Material | Notes |
|---|---|---|---|
| `P1_hemisphere_r15.stl` | 80 × 80 × 19 | 53 cm³ |  |
| `P2_hemisphere_r25.stl` | 80 × 80 × 29 | 59 cm³ | deepest cavity, 25 mm |
| `P3_cone_r20_d10.stl` | 80 × 80 × 14 | 44 cm³ |  |
| `P4_paraboloid_30x20_d12.stl` | 80 × 80 × 16 | 43 cm³ |  |
| `P5_paraboloid_12x8_d4.stl` | 80 × 80 × 9 | 35 cm³ | smallest cavity — check fine detail |
| `P6_flat_plate.stl` | 80 × 80 × 9 | 36 cm³ | no cavity; engravings only |
| `P7_lobed_r18_d9.stl` | 80 × 80 × 13 | 41 cm³ |  |
| `P8_trough_L40_r9_d8.stl` | 80 × 80 × 12 | 39 cm³ |  |
| `P9_paraboloid_on_cyl_r60.stl` | 80 × 80 × 22 | 50 cm³ | top face is a cylinder of R 60 mm |
| `P10_undermining_base.stl` | 80 × 80 × 19 | 42 cm³ | has a Ø56.4 × 3 mm register pocket |
| `L1_lid_concentric_r12.stl` | Ø56 × 3 | 6 cm³ | print flat; pairs with P10 |
| `L2_lid_offset6_r12.stl` | Ø56 × 3 | 6 cm³ | print flat; pairs with P10 |

L1 and L2 drop into P10's pocket. If they bind, sand the **lid** edge, never the pocket — the
pocket depth sets the skin plane the whole undermining measurement references.

## Ordering the minimum first

You do not need all twelve to start. Four parts give a working bench: **P6** (the flat plate, whose
depth noise is the sensor floor), **P1** (volume against a closed form), and **P10 + L1** (the
whole undermining path). About 137 cm³ — under a third of the full set.

## Reference values

`truth.csv` and `truth.json` carry the exact nominal geometry of every part, and each part has its
own values engraved on the pad underneath. **Measure the printed parts with calipers on arrival and
use the measured values as truth** — every process shrinks a little, and the measured number is the
one that matters.
