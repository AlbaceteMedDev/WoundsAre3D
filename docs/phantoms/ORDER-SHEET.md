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
`parts_sheet.pdf` is the same in print: a picture of each part with its sizes, how to tell
the parts apart, and the full detail.
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

## Lifelike colour set W1–W8 (a separate order)

Eight full-colour wounds on six skin tones (`INDEX.md`, "Lifelike colour set"). Order them
separately from the P-series: a different process, different files.

| Setting | Value |
|---|---|
| Process | **Full colour, matte.** Best: Stratasys PolyJet (J750, J850, J55) with the **Matte** finish. Also usable: HP Multi Jet Fusion colour (Shapeways "Nylon PA12 Full Color"), which prints duller, darker colours; Mimaki full colour (Shapeways "High Definition Full Color", matte only) |
| Files | `lifelike/*.wrl.zip` (VRML, colour per vertex) for PolyJet through GrabCAD Print and for Shapeways. `lifelike/*.3mf` for Xometry, which quotes PolyJet from 3MF, and JLC3DP full colour |
| Units | Millimetres — do not scale |
| Colour | sRGB targets. On PolyJet ask for the skin-tone colour profile (GrabCAD "Vivid 1.1 D50 Relative"). Colours will not match a screen exactly |
| Finish | Matte only: no gloss, clear coat or wax. The parts are scanned by an optical depth sensor |
| Interior | Solid; no vents or drain holes needed |
| Quantity | 1 of each |

**Note to the shop**

> Full-colour wound models used to test a wound-measurement device. Millimetres — do not scale.
> Matte finish all over; no gloss or clear coat. Colours are carried per vertex in the VRML
> (per triangle corner in the 3MF); please print with your skin-tone profile. The labels on the
> sides and underside are engraved 1.0 mm deep and coloured: keep support material out of them,
> and keep it off the wound surfaces as far as the process allows. W4 has an undermined pocket
> under the wound's upper edge, 2 mm below the surface; please clear any support from it.

| File (.3mf and .wrl.zip) | Wound | Skin type | Block (mm) | Material | Triangles |
|---|---|---|---|---|---|
| `W1_venous_leg_ulcer` | Venous Leg Ulcer | II | 80 × 80 × 14 | 86.3 cm³ | 810,484 |
| `W2_diabetic_foot_ulcer` | Diabetic Foot Ulcer | IV | 80 × 80 × 14 | 87.4 cm³ | 746,472 |
| `W3_pressure_injury_stage3` | Pressure Injury S3 | V | 80 × 80 × 14 | 84.4 cm³ | 901,020 |
| `W4_pressure_injury_stage4` | Pressure Injury S4 | III | 80 × 80 × 26 | 157.1 cm³ | 942,962 |
| `W5_unstageable_eschar` | Unstageable Eschar | I | 80 × 80 × 14 | 87.0 cm³ | 671,304 |
| `W6_arterial_ulcer` | Arterial Ulcer | VI | 80 × 80 × 14 | 87.3 cm³ | 562,630 |
| `W7_surgical_dehiscence` | Surgical Dehiscence | IV | 80 × 80 × 14 | 85.8 cm³ | 553,442 |
| `W8_healing_wound` | Healing Wound | II | 80 × 80 × 14 | 87.7 cm³ | 542,074 |
| **Set** | | | | **763 cm³** | |

Every file is under one million triangles (Shapeways' colour upload limit) and under 12 MB.

**Check on arrival.** Compare each part with its picture on `parts_sheet.pdf` pages 5–6 and read
its engraved labels. Expect printed colours to sit a little away from the screen; the tissue
types should still be plain. Measure with calipers and use the measured values as truth, as for
the P-series.
