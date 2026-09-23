> **Revision A — superseded. Do not print.** These notes describe the earlier STL set, which
> failed a print service's wall-thickness inspection. The cavity geometry and truth values
> below still hold; the hollowing described here does not. See `INDEX.md` for revision B.

# StrataMetric wound-measurement phantom set

Six 80 × 80 mm blocks, 9–29 mm tall (each only as thick as its cavity needs), with one cavity of
closed-form volume cut into the top face. Hollowed — see "Hollow shell" below.
All files are watertight binary STL in **millimetres**. Cavity volumes reproduce the analytic
value to better than 0.01 %.

| ID | File | Cavity | Opening | Max depth | True volume |
|---|---|---|---|---|---|
| P1 | P1_hemisphere_r15.stl | hemisphere, R = 15 mm | Ø30.000 mm | 15.000 mm | 7 068.58 mm³ = 7.069 cm³ |
| P2 | P2_hemisphere_r25.stl | hemisphere, R = 25 mm | Ø50.000 mm | 25.000 mm | 32 724.92 mm³ = 32.725 cm³ |
| P3 | P3_cone_r20_d10.stl | cone, R = 20 mm, h = 10 mm | Ø40.000 mm | 10.000 mm | 4 188.79 mm³ = 4.189 cm³ |
| P4 | P4_paraboloid_30x20_d12.stl | elliptic paraboloid, a = 30, b = 20, h = 12 mm | 60.000 × 40.000 mm | 12.000 mm | 11 309.73 mm³ = 11.310 cm³ |
| P5 | P5_paraboloid_12x8_d4.stl | elliptic paraboloid, a = 12, b = 8, h = 4 mm | 24.000 × 16.000 mm | 4.000 mm | 603.19 mm³ = 0.603 cm³ |
| P6 | P6_flat_plate.stl | none — sensor-floor reference | — | 0 | 0 |

Hemisphere V = ⅔πR³ · cone V = ⅓πR²h · elliptic paraboloid V = πabh/2.
These are the shapes the engine's regulatory suite already validates against, so bench results
map one-to-one onto the existing tests. `truth.csv` and `truth.json` carry the same numbers.

## The measurement key line

Every block carries the same reference line on the **top face**, engraved 0.5 mm deep:

```
        |<------------ 50.000 mm ------------>|
        |                                     |
        ├─────────────────────────────────────┤     <- groove, 0.800 mm wide
        |                                     |        end ticks 0.800 × 6.000 mm
                      50.000                           engraved value, 3.2 mm tall
```

**Definition — the key line length is 50.000 mm, measured centre-of-tick to centre-of-tick.**
The groove runs exactly between those two centres, so three readings all give the same number:

| Reading | Value |
|---|---|
| tick centre → tick centre | **50.000 mm** (the definition) |
| groove end → groove end | 50.000 mm |
| tick outer edge → outer edge | 50.800 mm |
| tick inner edge → inner edge | 49.200 mm |

The line is centred at x = 0, y = −30.000 mm and never touches any cavity.

**Second, larger reference:** the four fiducial dots (Ø2.500 mm) have centres at (±32, ±32) mm, so
centre-to-centre along an edge is **64.000 mm** and across the diagonal **90.510 mm**. Use the
fiducial square for scale checks over a wider baseline than the key line allows.

Use these to verify the app's scale recovery on every single scan: if the reported length of the
key line drifts from 50.000 mm, the scan's other numbers are not trustworthy either.

## The spec plate (bottom face)

The underside of each block is engraved 0.4 mm deep with its own exact nominal geometry —
shape, defining parameters, depth, opening area, volume in mm³ and cm³, the key-line and
fiducial lengths, and the block size. The text is mirrored in the model so it **reads correctly
when you turn the block over**. Each phantom therefore carries its own truth; you cannot mix
up which block produced which scan.

The plate ends with `CAD NOMINAL - VERIFY`, because the printed part is what you measure
against, not the CAD (see below).

## Ordering prints

- **Process: Industrial SLA** (the "better precision and detail" tier). Standard SLA is an
  acceptable fallback. Avoid FDM, MJF and SLS for the reference set — layer stepping and powder
  texture both degrade the cavity wall.
- Material: standard grey or beige resin. Layer height: finest offered (0.05 mm).
- Orientation: cavity facing up, block flat on the plate. **No supports inside the cavity.**
- Order note: *"Do not scale — dimensions are in millimetres. Cavity face up, no supports inside
  the cavity. Fine detail on both the top and bottom faces (0.4–0.5 mm engravings) must be preserved."*
- Quantity: one of each; a second P6 is worth having as a spare flat reference.

## After the prints arrive — before the first scan

1. **Measure and re-baseline.** Calipers on the opening (diameter or both axes), depth gauge at
   the centre, and calipers across the key line and the fiducial square. Resin shrinks a few
   tenths of a millimetre. Write the measured values next to the CAD values in `truth.csv`;
   **the measured values are the truth from then on.**
2. **Recompute volume** from the measured parameters using the formula on the spec plate, and
   cross-check with a saline fill from a 1 mL (P5) or 5 mL syringe.
3. Fill the engravings with a fine black permanent marker and wipe the face, so the dots, key
   line and ID read clearly in the RGB frame.
4. Matte the surface: translucent setting powder, or a thin skin-tone silicone coat for the
   realistic-appearance variants.

## Bench protocol

10 scans per phantom × 3 distances (20, 30, 40 cm) × 2 lighting conditions × 2 operators,
hand-held. Per scan record: phantom id, distance, light, operator, reported volume / max depth /
opening area / confidence interval, quality grade, **and the reported length of the key line**.

Report per phantom and condition: bias (mean error), limits of agreement (mean ± 1.96 SD),
confidence-interval coverage (fraction of scans whose 95 % CI contains the truth), and
repeatability (SD of the 10 repeats). Scan P6 first — depth noise on the flat plate is the
sensor floor and the only defensible replacement for the current "±0.3 mm" claim.

Realism variants, applied to the same blocks one at a time: glycerin or gel for a wet gloss,
dark acrylic for eschar, mounted on 100 mm and 150 mm PVC pipe for limb curvature, a silicone
rolled edge for a realistic wound margin.

## Regenerating

`make_phantoms.py` (numpy + Pillow, matplotlib for the previews) rebuilds everything; edit the
`PHANTOMS` list to change sizes. It refuses to write a mesh that is not watertight, whose volume
disagrees with the analytic value, or whose engravings collide with a cavity.

## Hollow shell

Every block is an open-bottomed shell: a 3.5 mm solid rim, a 34 × 34 mm solid pad in the centre
carrying the spec plate, a 3.5 mm ceiling over the ring between them, and two 3 mm stiffening ribs
running pad-to-rim on each axis so the thin ceiling stays flat. The void is open at the bottom and
connected throughout, so no resin is trapped and the part drains as it lifts from the vat —
nothing needs a drain hole drilled. Each block is also only as thick as its own cavity requires
(9–29 mm) rather than a uniform 30 mm, leaving 4 mm of material under the deepest point.

Material for the twelve parts drops from 1 844 cm³ to **454 cm³, 4.1× less**, with no change to
any cavity, engraving or reference value. Minimum material thickness anywhere is **3.5 mm**.

| | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Height (mm) | 19 | 29 | 14 | 16 | 9 | 9 | 13 | 12 | 22 | 19 |
| Material (cm³) | 53 | 59 | 44 | 43 | 35 | 36 | 41 | 39 | 50 | 43 |
| vs solid | 29% | 37% | 23% | 24% | 18% | 19% | 22% | 21% | 27% | 24% |

The remaining material is mostly the rim, the pad and the ceiling — there is little left to remove
without either losing the spec plate or thinning the shell to where it risks warping, which would
distort the top face the measurements reference.

`python make_phantoms.py --solid` regenerates solid blocks if you ever want them.
