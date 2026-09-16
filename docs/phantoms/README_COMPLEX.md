# StrataMetric wound phantoms — complex set (P7–P10 + lids)

Companion to the basic set (P1–P6). Same conventions: watertight binary STL in **millimetres**,
80 × 80 mm blocks 12–22 mm tall, hollowed, a 50.000 mm key line and four fiducial dots engraved 0.5 mm into the top
face, and the phantom's own exact geometry engraved 0.4 mm into the bottom face, mirrored so it
reads when you turn the block over.

These four exist because the simple set cannot fail in the ways a real wound makes software fail:
a non-convex boundary, an elongated wound, a wound on a curved limb, and undermining.

| ID | File | What it tests | True volume | Max depth | Opening area | Perimeter |
|---|---|---|---|---|---|---|
| P7 | `P7_lobed_r18_d9.stl` | non-convex, stellate boundary — segmentation, area, perimeter | 4 677.55 mm³ | 9.000 mm | 1 039.46 mm² | 126.816 mm |
| P8 | `P8_trough_L40_r9_d8.stl` | elongated dehisced trough — length/width axes, aspect ratio | 4 857.88 mm³ | 8.000 mm | 974.47 mm² | 136.549 mm |
| P9 | `P9_paraboloid_on_cyl_r60.stl` | wound on a **curved limb** — reference-surface fitting | 7 068.58 mm³ | 10.000 mm | 1 413.72 mm² | — |
| P10 | `P10_undermining_base.stl` + a lid | **undermining** — hidden volume and probe extent | see below | see below | see below | — |

Every value above is closed-form, not numerically fitted:

- **P7** lobed paraboloid, R(θ) = 18(1 + 0.18·cos3θ + 0.10·cos(5θ+0.7)), depth = h(1−(r/R)²).
  V = (π·h·R₀²/4)(2 + Σaₖ²), A = (π·R₀²/2)(2 + Σaₖ²). Rim radius runs 13.132–22.868 mm.
  Perimeter 126.816 mm (integrated over 65 536 steps; converged to better than 1e-6 mm).
- **P8** stadium trough, radius 9 mm about a 40 mm segment. V = 4hR·L/3 + πhR²/2,
  A = 2RL + πR², perimeter = 2L + 2πR — all exact.
- **P9** elliptic paraboloid a = 25, b = 18, h = 10 **cut into a cylinder of radius 60.000 mm**
  (axis along y, i.e. a forearm or calf). Depth is applied as a vertical offset from the cylinder,
  so the enclosed volume is exactly πabh/2 = 7 068.58 mm³ — deliberately identical to P1's
  hemisphere, so the pair isolates the effect of the reference surface from the effect of volume.
  **Its key line runs along y** (at x = −30), a line of constant height on the cylinder, so the
  groove is straight and flat; the four fiducials also all sit at equal height, so the 64.000 mm
  edges and 90.510 mm diagonal stay exact.

## P9 — what to look for

A planar reference fit through the wound rim does not coincide with the cylinder surface, so an
app that fits a plane will report a materially different volume from one that fits the curved
skin. Scan P1 and P9 back to back: they have the **same true volume**. If the two reported
volumes differ, the difference is entirely the reference-surface error.

## P10 — undermining, two parts

True undermining is an undercut, so it cannot be a single printed block: resin is trapped, no
caliper reaches inside, and LiDAR physically cannot see under the shelf. P10 is therefore a base
plus an interchangeable lid.

- **Base**: a flat-bottomed chamber Ø40.000 × 12.000 mm deep, inside a Ø56.400 × 3.000 mm register
  pocket that centres the lid. Chamber alone = 15 079.64 mm³.
- **Lid L1** `L1_lid_concentric_r12.stl` — Ø56.000 × 3.000 mm disc, Ø24.000 hole on centre.
- **Lid L2** `L2_lid_offset6_r12.stl` — same disc, hole offset 6.000 mm in +x (asymmetric undermining).

Drop a lid into the pocket; its top finishes flush with the block's top face, which is the skin
plane. Assembled truths (identical for both lids except the extent):

| Quantity | Value |
|---|---|
| Wound opening at skin | Ø24.000 mm, area 452.39 mm² |
| Depth, skin to chamber floor | 15.000 mm |
| Shelf underside below skin | 3.000 mm |
| **Total wound volume** | **16 436.81 mm³** |
| Visible (line-of-sight through the opening) | 6 785.84 mm³ |
| **Undermined (hidden) volume** | **9 650.97 mm³ — 58.7 % of the total** |

Undermining extent, measured from the wound edge outward to the chamber wall (12 o'clock = +y):

| Lid | 12 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L1 concentric | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 | 8.000 |
| L2 offset 6 mm | 7.079 | 4.313 | 2.578 | 2.000 | 2.578 | 4.313 | 7.079 | 10.313 | 12.970 | 14.000 | 12.970 | 10.313 |

L2's extents come from t(θ) = √(36cos²θ + 364) − 6cosθ − 12.

**What to test with it.** The app cannot see the undermined volume and must not pretend to. Three
distinct checks: (a) the optically reported volume should match the **visible** 6 785.84 mm³, not
the total; (b) probe-entered undermining at the twelve clock positions should reproduce the table
above; (c) the engine's undermining model should turn those probe depths into something near
9 650.97 mm³. The register records this last formula as reading 5–12× low, so expect it to fail
until it is fixed — P10 is the fixture that proves the fix.

Swapping L1 for L2 changes only the extent distribution, so it isolates whether the undermining
model handles asymmetry or merely averages.

## Printing

Same as the basic set: **Industrial SLA**, finest layer height, cavity face up, no supports inside
the cavity, do not scale. The lids are thin discs — print them flat, and keep them with the base.

A note on the two-part fit: the pocket is modelled at Ø56.400 and the lids at Ø56.000, giving
0.200 mm radial clearance. If your printer runs tight, sand the lid edge rather than the pocket.
The nominal volumes above assume zero clearance; the 0.2 mm ring contributes about 106 mm³
(0.6 % of the total), so if you need the tighter number, measure the assembled gap and subtract.

## Before the first scan

Identical to the basic set, with two additions:

- On P10, caliper the chamber diameter and depth, and the lid hole and thickness, **before**
  assembling. The undermining truths are derived from those four numbers.
- On P9, check the block's top curvature with a radius gauge or by measuring the edge-to-centre
  drop (nominal 15.279 mm at x = ±40).

`truth.json` carries every number above per part, including the per-clock extents.
