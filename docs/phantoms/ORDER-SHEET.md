# Print order — StrataMetric wound phantoms (STEP, revision C)

12 parts. Upload the twelve `.step` files. **Dimensions are in millimetres — do not scale.**

Revision C replaces revision B. Do not print any file from an earlier revision.

## What changed from revision B

- **Every part now carries its measurements, legibly.** Each block's side walls are engraved
  with its part number, depth, opening area and volume; the underside carries the full
  specification; each lid carries its hole size and offset on its underside. In revision B the
  engraving step kept only one character of each line, so the files themselves never
  contained the measurements — and what was there was cut 0.4 mm deep, below MJF's limits.
- **All engravings are 1.0 mm deep** — HP's own minimum for text on MJF parts — in capitals at
  4.5–6 mm cap height (median stroke 0.76–1.06 mm), with at least 0.6 mm of material between
  letters.
- **P10 and its lids are keyed.** An index groove on P10's top and a notch in each lid's rim
  fix which way the lid sits, which L2's offset hole needs.
- **Powder vents moved to the floor.** Every hollow block has two Ø6 mm holes up through its
  base at opposite corners (x, y = +33, +33 and −33, −33). Revision B's side-wall vents broke
  out through the curved top of P9 as open slots, and were as small as Ø4 on the shallow
  blocks.

Unchanged from revision B: exact B-rep geometry with no faceting, and a void held 3.5 mm from
every outer surface along the normal — 2.5 mm directly behind a 1.0 mm engraving. The files are
STEP AP214.

## Settings

| Setting | Value |
|---|---|
| Process | **MJF** (HP Multi Jet Fusion). SLS PA12 is an acceptable alternative |
| Material | Nylon PA12, **natural grey**. No dye, especially not black |
| Finish | **Standard depowdering (bead blast) only.** No polishing, tumbling, vapour smoothing or dyeing |
| Orientation | Cavity face up |
| Supports | Not applicable to powder bed; if you move to a supported process, **none inside any cavity** |
| Quantity | 1 of each; a second P6 is useful as a spare flat reference |

**Why MJF.** Powder bed needs no supports, so nothing ever touches a cavity surface; loose
powder clears through the escape holes; and the matte, diffuse, opaque surface is the best
target for the depth sensor under test. Glossy or translucent material corrupts depth
readings.

## Note to the shop

> Dimensions are in millimetres — do not scale. These are metrology reference parts: please
> do not sand, polish, tumble, vapour-smooth, dye or otherwise finish any surface beyond
> standard depowdering. Natural grey PA12. Each hollow block is a closed shell with two Ø6 mm
> powder-escape holes in its base; P8's interior is two separate voids, one hole each — please
> make sure all loose powder is cleared from every void. The side walls, top and underside
> carry engraved text 1.0 mm deep (the side walls carry the measurements the parts are used
> for): please blow the powder out of the lettering and do not let it fill.

## Parts

| File | Size (mm) | Material | Interior | Notes |
|---|---|---|---|---|
| `P1_hemisphere_r15.step` | 80 × 80 × 19 | 57.6 cm³ | hollow, 2 × Ø6 floor vents |  |
| `P2_hemisphere_r25.step` | 80 × 80 × 29 | 72.6 cm³ | hollow, 2 × Ø6 floor vents | deepest cavity, 25 mm |
| `P3_cone_r20_d10.step` | 80 × 80 × 14 | 50.9 cm³ | hollow, 2 × Ø6 floor vents |  |
| `P4_paraboloid_30x20_d12.step` | 80 × 80 × 16 | 53.8 cm³ | hollow, 2 × Ø6 floor vents |  |
| `P5_paraboloid_12x8_d4.step` | 80 × 80 × 9 | 55.5 cm³ | solid | smallest cavity — check fine detail |
| `P6_flat_plate.step` | 80 × 80 × 9 | 56.0 cm³ | solid | no cavity |
| `P7_lobed_r18_d9.step` | 80 × 80 × 13 | 51.0 cm³ | hollow, 2 × Ø6 floor vents |  |
| `P8_trough_L40_r9_d8.step` | 80 × 80 × 12 | 54.3 cm³ | hollow: 2 voids, 1 × Ø6 floor vent each | void split by the trough's grown footprint |
| `P9_paraboloid_on_cyl_r60.step` | 80 × 80 × 22 | 73.4 cm³ | hollow, 2 × Ø6 floor vents | top face is a cylinder of R 60 mm |
| `P10_undermining_base.step` | 80 × 80 × 19 | 57.6 cm³ | hollow, 2 × Ø6 floor vents | Ø56.4 × 3 mm register pocket for L1/L2 |
| `L1_lid_concentric_r12.step` | Ø56 × 3 | 5.8 cm³ | solid | pairs with P10; label on underside, rim notch |
| `L2_lid_offset6_r12.step` | Ø56 × 3 | 5.8 cm³ | solid | pairs with P10; label on underside, rim notch |
| **Set** | | **594 cm³** | | |

L1 and L2 drop into P10's register pocket, **notch to the index groove** on P10's top. If they
bind, sand the **lid** edge, never the pocket — the pocket depth sets the skin plane that the
whole undermining measurement references.

## Check on arrival

Every block should show its part number, depth, area and volume on its side walls, and a
specification block on its underside; each lid its hole and offset on its underside.
`labels_preview/` shows exactly what each face should read. If a label is filled with powder,
blow it out; if it is missing, the print is wrong.

## Ordering the minimum first

Four parts give a working bench: **P6** (flat plate; its depth noise is the sensor floor),
**P1** (volume against a closed form), and **P10 + L1** (the whole undermining path).

## Reference values

`truth_step.json` carries the exact geometry and every engraved label of every part.
**Measure the printed parts with calipers on arrival and use the measured values as truth** —
every process shrinks a little, and the measured number is the one that matters.

## Parts already printed from revision B

Their cavities are identical to revision C's, so they remain usable — except as a scale
reference on P9, whose fiducial dots were cut away by its vents, leaving four open slots in its
top near the corners; use P9 for depth, area and volume only. Print `label_sheet.pdf` at 100 %
on adhesive paper and stick each block's label on its underside.
Keep the lid labels with the lids, not on them — anything stuck to a lid changes how it seats.
Revision B's lids are not keyed, and its P10 has no legible part number to orient by: seat L2
with its hole nearest 3 o'clock, taking 6 o'clock as the side of P10 with the 50 mm key line.
