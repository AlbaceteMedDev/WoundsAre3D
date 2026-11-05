# Lifelike colour wound phantoms W1–W8 — specification

Everything needed to understand, reproduce or change the eight full-colour wound phantoms.
`make_lifelike.py` is the reference implementation and this document describes it; where the
two disagree, the code is right and this document is out of date. Per-wound numbers (design
parameters, measured truth, labels, colours) are not repeated here: they are in
`truth_lifelike.json` and, in the reproduction kit, in `DATA-CARDS.md` and
`data/parameters.json`, all generated from the code.

## 1. What the phantoms are for

Each phantom is an 80 × 80 mm block whose top is skin with one wound in it. The wounds look like
real ones — irregular margins, uneven beds, mottled tissue, periwound changes — in full colour
on six skin tones, and every size is known exactly because it is measured on the mesh that is
printed. They test what exact geometric phantoms cannot: finding the wound edge and classifying
tissue on something that looks like a patient. The grey P-series (`make_phantoms_step.py`) is a
separate set and is not described here.

| Part | Wound | Skin type |
|---|---|---|
| W1 | Venous leg ulcer | II |
| W2 | Neuropathic diabetic foot ulcer in callus | IV |
| W3 | Stage 3 pressure injury with a rolled edge | V |
| W4 | Stage 4 pressure injury with exposed bone and undermining | III |
| W5 | Unstageable pressure injury, eschar | I |
| W6 | Arterial ulcer | VI |
| W7 | Surgical dehiscence with suture marks | IV |
| W8 | Healing wound | II |

## 2. Coordinates and the block

- Millimetres throughout. x runs to 3 o'clock, y to 12 o'clock, z up. The block occupies
  x, y ∈ [−40, 40], z ∈ [0, H]; its top, z = H, is the **skin plane**.
- 12 o'clock is the edge nearest the part number engraved on the top (at y = +33).
- Polar angle θ is measured anticlockwise from +x (3 o'clock), about the wound centre
  **C = (0, 1.5)**. A clock hour is `round((90° − θ)/30°) mod 12`, with 0 written as 12.
- The wound and all periwound changes live in the **patch** x ∈ [−29, 29], y ∈ [−26, 29],
  clear of the fiducial dots, the key line and the part number.
- Block height `H = max(14, ceil(maximum depth + 6))`, so at least 6 mm of material lies under
  the deepest point. W4 is 22 mm; the rest are 14 mm.
- Sides and underside are a light neutral grey, `BODY` = #E3E1DD. The top outside the patch is
  plain skin.

## 3. Building blocks

**Noise field** `f(seed, x, y, scale, n=28, stretch=1, angle=0)` (`field()`): a sum of n plane
waves `a_i cos(k_i·(x, y) + φ_i)` divided by `sqrt(Σ a_i²/2)`, so it has roughly unit amplitude.
From `numpy.random.default_rng(seed)`: wave directions from a 2-D normal, wavenumbers
`|k_i| = (2π/scale) U(0.6, 1.4)`, phases `U(0, 2π)`, amplitudes `N(0, 1)`. `stretch > 1` lengthens the
features along `angle` degrees (fibrous textures). In the wound design, `f_k(scale)` means
`field(wound seed + k, x, y, scale)`; each feature has its own k, listed where it is used.

**smoothstep**(e0, e1, x) = t²(3 − 2t) with t = clip((x − e0)/(e1 − e0), 0, 1).
**mix**(a, b, t) = a(1 − t) + bt with t clipped to [0, 1], applied to sRGB triples in [0, 1].
**window**(θ, a0, a1) = sin(πt) with t = ((θ° − a0) mod 360)/(a1 − a0) when 0 ≤ t ≤ 1, else 0:
an arc from a0 to a1 degrees anticlockwise, peaking mid-arc.
**edge_taper**(x, y) = smoothstep(0.5, 4.0, distance to the patch edge): periwound changes fade
out before the patch edge so they never meet plain skin in a line.

**Granules** (`bumps()`, seed + 12): domed bumps on a jittered hexagonal lattice, spacing
0.95 mm (rows 0.95 × 0.866 apart, alternate rows offset by half), each centre jittered by
U(−0.35, 0.35) × spacing, radius 0.70 × U(0.7, 1.3), relative height U(0.55, 1.2), profile
`h (1 − (d/r)²)^1.5`; the value at a point is the largest of its four nearest bumps.

**Soft boundaries** (`smoother()`): for colour and relief only, each tissue's 0/1 indicator is
averaged over all wound points within 0.4 mm, so tissues blend over a few tenths of a millimetre.
The truth uses the hard tissue map.

## 4. The wound outline

`r(θ) = r_e(θ − rot) × max(1 + Σ A_m cos(mθ + φ_m), 0.5)` (`r_of()`), where
`r_e(t) = a b / sqrt((b cos t)² + (a sin t)²)` is an ellipse with semi-axis **a** across
(3–9 o'clock) and **b** along (12–6), rotated by **rot** degrees. The harmonics come from
`harmonics(seed, amp, mmax, rough)`: for m = 2 … mmax, `A_m = amp U(0.3, 1)/m^0.8` and
`φ_m = U(0, 2π)`; if rough > 0, also m = mmax + 1 … 40 with `A_m = rough U(0.3, 1)/m^0.5`.
`data/parameters.json` lists every (m, A_m, φ_m).

The **margin polygon** (`outline()`) samples r(θ) at 40,000 angles and resamples it every
0.12 mm of arc length. The mesh follows this polygon exactly, so the wound's area, perimeter,
length and width are the polygon's.

Normalised radius `ρ = |p − C| / r(θ)`: ρ < 1 is inside the wound. Inside, the distance in from
the margin is `(1 − ρ) r(θ)`; outside, the distance out is `o = (ρ − 1) r(θ)`, both measured
along the ray from C.

## 5. Tissue map

Scores (`Design.scores()`), at a wound point with inward distance `in = (1 − ρ) r(θ)`:

| Tissue | Score |
|---|---|
| bone (W4 only) | `1 − e + 0.12 f_53(2)`, where e is the elliptical radius about C + `bone.at`, semi-axes `bone.axes`, rotated `bone.rot` |
| epithelial | `exp(−in/2)(1 + 0.35 f_1(6))`, plus `0.6 max(f_2(3.5) − 1, 0)` where the wound has **islands** (partial thickness: W1, W8) |
| necrotic | `0.8 f_3(9) + 0.4 f_5(4) + 0.6(1 − ρ)` |
| slough | `f_4(8, stretch 1.4, angle seed mod 180) + 0.35 f_6(3) + 0.5 cos(θ − seed°) + 0.25 f_3(9)` |

Each tissue in priority order **bone, epithelial, necrotic, slough** takes the points where its
score is above its threshold and no earlier tissue has taken them; the rest is **granulation**.
The thresholds (`fit_thresholds()`) are fitted on a 0.1 mm grid so that each tissue covers its
target share (`tissue` in each wound's parameters) of the wound's **plan** area.

## 6. Depth and relief

Inside the wound (`Design.depth()`), depth below the skin plane:

    base   = D max(1 − ρ^k, 0) (1 + 0.12 f_10(30)) (1 + 0.05 f_11(7))
    crack  = max(1 − |f_13(7)|/0.045, 0) clip(f_16(9) + 0.6, 0, 1)        eschar fissures
    relief = soft_granulation (gh g + 0.08 f_17(3))                       gh = 0.08 pale, else 0.14
           + soft_slough (0.12 + 0.03 f_14(1, stretch 2))
           + soft_necrotic (0.40 + 0.06 f_15(2) − 0.25 crack)
           + soft_epithelial 0.03
           + soft_bone (0.9 + 0.05 f_54(1.5))                            a bony prominence
    ramp   = smoothstep(0, 1.2, in)                                       relief fades at the margin
    depth  = max(base − relief ramp min(1, base/0.6 + 0.2), 0.08 smoothstep(0, 0.6, in))

g is the granule field (0–1.2). **D** sets the depth and **k** the wall: a large k gives a flat
base and a steep, punched-out wall; k near 2 gives a shallow saucer.

Outside the wound (`Design.raise_()`), height above the skin plane, all × edge_taper:

- **callus** (W2): `hc C (1 + 0.10 f_21(3)) + 0.04 C f_23(1.5)`, with
  `C = smoothstep(0, 0.8, o)(1 − smoothstep(w − 1.8, w, o))`, `w = wc (1 + 0.18 f_20(8))`,
  (wc, hc) = `peri.callus`;
- **rolled edge** (W3): `he window(θ, a0, a1)^0.7 exp(−((o − 0.9)/0.9)²) smoothstep(0, 0.25, o)`,
  (a0, a1, he) = `peri.epibole`;
- **maceration texture**: `0.05 M (1 + f_22(0.7)) smoothstep(0, 0.3, o)`, M as in §8;
- **suture marks** (W7): pits 0.25 mm deep, discs of radius 0.45 mm at x = ±(a + 2.2) every
  7 mm in y.

## 7. Colours of the wound bed

All colours are sRGB. Hex values are in `TISSUE_REF` (§12). Each vertex's colour is
`Σ soft_tissue × tissue colour` (`Design.bed_colour()`):

- **granulation**: `mix(G0, G2, 0.30 + 0.9 g + 0.15 f_44(2) + 0.10 f_49(0.6))`; on the arterial
  ulcer (W6, `pale`) the pale pair, `mix(P0, P2, 0.25 + 1.1 g + 0.1 f_44(3))`;
- **slough**: `s = mix(tan, yellow, 0.5 + 0.35 f_45(3))`, then towards cream by
  `0.45 clip(f_50(2) + 0.3)`, towards grey by `0.25 clip(f_46(5) − 0.4)`, towards the pinkish
  tan of thin fibrin (#B3746B) by `0.3 clip((0.7 − soft_slough) 2.5)` where it meets
  granulation, and scaled by `1 + 0.05 f_51(0.8, stretch 2)`;
- **necrotic**: `mix(N0, N1, 0.5 + 0.35 f_47(2))`, browner (N2) where it thins, by
  `0.85 clip((0.9 − soft_necrotic) 3)`, darker in the fissures by `1 − 0.30 crack`;
- **epithelial**: `mix(E0, E1, 0.5 + 0.3 f_48(2))`, using the dark-skin pair where the skin's
  luminance `0.2126R + 0.7152G + 0.0722B` is below 0.47 (types V, VI);
- **bone**: `mix(B0, B1, 0.5 + 0.35 f_52(1.5))`.

## 8. Periwound layers

Outside the wound, the skin colour is overlaid layer by layer in this order
(`Design.periwound_layers()`): each layer has a weight w ∈ [0, 1] and mixes towards its colour.
The same weights define where each change shows in the truth (§11). tap = edge_taper.

| Layer | Weight w | Colour |
|---|---|---|
| haemosiderin | `0.75 clip(hz) tap`; `hz = F clip(0.45 + 0.5 f_32(5)) + 0.5 S F`, `F = 1 − smoothstep(2, hw + 3, o(1 + 0.3 f_30(10)))`, speckle `S = clip((f_31(1.2) − 1.2) 3)` | PERI_COL.hae |
| erythema | `0.85 exp(−o/we)(1 − smoothstep(1.5we, 3we, o)) tap`, `we = width (1 + 0.25 f_33(12))` | PERI_COL.ery |
| pale shiny skin | `0.75 exp(−o/wp)(0.8 + 0.2 f_37(3)) tap`, `wp = width max(1 + 0.35 f_36(9), 0.3)` | PERI_COL.pal (ashen) |
| callus | `0.85 C (0.88 + 0.12 f_34(3.5)) tap` | PERI_COL.cal |
| blood in callus | `0.75 clip((f_35(4) − 1.7) 2) C tap` | #74433B |
| rolled edge | `0.6 window^0.7 exp(−((o − 0.9)/0.9)²) tap` | (skin + #EAC9BE)/2 |
| maceration | `0.85 M tap`; M = max of `window(θ, a0, a1) exp(−o/3)` (`peri.maceration`) and `exp(−o/w)` (`peri.maceration_ring`) | PERI_COL.mac |
| incision line | `0.85 max(1 − |x − C_x|/0.8, 0) tap` | #B8746C on skin with luminance > 0.55, else #8A5248 |
| suture marks | `0.85 pits tap` | #6A3530 |

## 9. The undermining pocket (W4)

Undermining runs from `undermine.start` to `undermine.end` degrees (30° to 150°: from 2 o'clock
round through 12 to 10). Its extent beyond the margin is `E(θ) = extent sin(πt)^1.2` across that
arc (10.0 mm at 12 o'clock). In section along each ray the pocket is a **slot** whose ceiling is
2.0 mm (`ROOF`) below the skin plane, of height `h(θ) = min(height, 2E(θ))` (5.0 mm wherever the
extent allows), from 0.94 r(θ) — inside the wound's open air — out to `r(θ) + E(θ) − h/2`, ending
in a **half-round end** of radius h/2 whose furthest point is at `r(θ) + E(θ)`, mid-height. A ball
tip up to h across therefore reaches the stated extent. Sections are taken every 0.5°; the two
ends, where E < 0.2 mm, are closed flat (`pocket_tool()`).

## 10. Mesh and solid

1. **Top surface.** A constrained Delaunay triangulation (Shewchuk's Triangle, switches
   `pq28Aa`) of the square ±41 mm — 1 mm past the block — with the patch rectangle and the
   margin polygon as fixed edges. Largest triangle 0.011 mm² in the wound, 0.030 mm² in the
   patch, 2.0 mm² beyond it; smallest angle 28°. Each vertex gets
   `z = H − depth + raise` and a colour (§7, §8).
2. **Solid** (manifold3d booleans that carry the colours as vertex properties): a box from
   z = 0 to `H + max raise + 0.5`, minus the region above the designed surface, so the block's
   top becomes the surface; on W4, minus the pocket; minus the engraving tools (§13).
3. **Truth is measured** on this solid before the labels are cut (§11).

## 11. Ground truth (`truth_lifelike.json`)

| Field | Definition |
|---|---|
| `length_mm`, `width_mm` | extent of the margin polygon along y (12–6) and x (3–9): the clock method |
| `longest_mm`, `longest_angle_deg`, `width_across_longest_mm` | the margin's longest diameter, its angle from the 12–6 line (positive towards 3 o'clock) and the margin's width across it |
| `area_mm2`, `perimeter_mm` | of the margin polygon, in plan |
| `max_depth_mm` | skin plane minus the lowest vertex strictly inside the margin |
| `volume_mm3` | volume of (margin polygon extruded from z = 0 to H) minus the part: the space between the skin plane and the bed inside the margin |
| `skin_plane_z_mm` | H |
| `tissue_share`, `tissue_pct` | each tissue's share of the wound's plan area on a 0.05 mm grid; whole percentages by largest remainder (ties: granulation, slough, necrotic, epithelial, bone) |
| `tissue_share_surface`, `bed_surface_area_mm2` | the same shares by the designed bed's 3-D surface area (W4 before its pocket), and that area |
| `tissue_colour` | each tissue's mean colour on the part |
| `periwound`, `periwound_conditions` | the periwound changes in label order; for each, the area over which its weight (§8) is at least 0.3 on a 0.1 mm grid, the clock hours that area spans, and how far it reaches from the margin along the ray from C |
| `undermining` (W4) | extent at each clock hour; maximum and where; from/to clock; undermined area (margin + extent polygon minus the wound); hidden volume (the pocket beyond the margin); roof; pocket height at each clock hour |
| `total_volume_mm3` (W4) | volume + hidden volume |
| `labels` | every engraved line: face, text, cap height, centre, reading direction, face normal |
| `material_mm3`, `vertices`, `triangles`, `block_mm`, `files` | the printed part |

## 12. Colour tables

All sRGB; CIELAB (D65) values are in `data/parameters.json`.

- **Skin** (`SKIN`): medians of 697 reflectance spectra measured on faces (the University of
  Oulu Physics-Based Face Database, Marszalec et al., J Electron Imaging 2000; RIT's
  Lippmann2000), binned by individual typology angle and matched to Fitzpatrick type by the
  median angle of each perceived type in 789 adults (Lipnick et al., Br J Dermatol 2026;
  194:135, doi:10.1093/bjd/ljaf397).
- **Periwound** (`PERI_COL`, per skin type): erythema, haemosiderin, maceration, callus, pallor.
  Redness deepens and turns violaceous on darker skin; pallor is the skin 13.5 L* lighter with
  a* and b* about halved (ashen).
- **Tissue** (`TISSUE_REF`): granulation within about 7 ΔE00 of the median granulation in
  LUTSeg's tissue-labelled ulcer photographs (CC BY 4.0); epithelium with LUTSeg's pink hue but
  lighter; slough and eschar from the clinical descriptions (LUTSeg's photographs are of
  leprosy-related ulcers on uncalibrated smartphones); exposed bone ivory to white.
- **Ink**: #1C1C1C on the grey sides and underside; on the top, #1C1C1C where the skin's
  luminance is above 0.47, else #F4F4F2 (at least 4.5:1 contrast).

## 13. Labels

- DejaVu Sans Mono Bold, capitals only, 1.0 mm deep along the face normal, cap height 4.5–6.0 mm
  (the largest that fits), line pitch 1.4 × cap, extra letter spacing 0.06 × cap, at least
  0.6 mm of material between letters, 1.5 mm clear of every edge. Glyph outlines are tessellated
  to 0.01 mm. The grooves are coloured with the ink.
- **Specification** (`spec_lines()`): `<ID> <TITLE>`; `L<length> W<width> D<depth>`;
  `AREA <area> MM2`; `PERIM <perimeter> MM`; `VOL <volume> MM3`; on W4
  `UNDERMINED <from>-<to>`, `MAX <extent> MM AT <clock>`, `HIDDEN <volume> MM3`; the tissue
  lines — `PCT` then each tissue present, largest first, packed into lines of at most 19
  characters (`GRAN`, `SLOUGH`, `NECROTIC`, `EPI`, `BONE`); the periwound lines — `PERI` then
  each change, packed the same way, never splitting a name; `SKIN TYPE <type>`.
- **Side walls** (`side_lines()`): ID and title, L W D, area, volume, on W4
  `UNDERMINED MAX <extent>`, the tissue lines, the periwound lines and the skin type, dealt to
  front, right, back and left (at most three per wall) at the largest common cap height. A
  14 mm wall takes 8 lines in all, a 22 mm wall 12; over that, the skin type and then the
  periwound lines are left to the underside.
- **Underside** (`bottom_lines()`): the specification in at most 12 lines, read from below; over
  12, the skin type and then the periwound's later lines are left to the side walls; with room
  to spare it adds the long wound name and `STRATAMETRIC`.
- Every specification line must be on some face; the build stops if one is not.
- **Top**: the part ID (6 mm cap) at y = +33; the key line 50.000 mm long and 0.8 mm wide at
  y = −30 with 0.8 × 6 mm end ticks and `50.000` (4.5 mm cap) under it; four fiducial dots
  Ø2.5 mm at (±32, ±32); all 1 mm deep.

## 14. Files

- `lifelike/<id>_<name>.3mf`: 3MF core with the Materials extension; one `m:colorgroup` holding
  every distinct colour, each triangle with p1/p2/p3 (a colour per corner); unit millimetre;
  coordinates to 5 decimals. For Xometry and HP Multi Jet Fusion colour.
- `lifelike/<id>_<name>.wrl.zip`: VRML 2.0 `IndexedFaceSet`, `colorPerVertex TRUE`, one colour
  per point in point order and no `colorIndex` (some readers ignore it). Where a vertex's
  corners differ, any colour but the ink wins, then the colour covering the most area round the
  vertex, so an engraving's walls fade into the groove instead of ink spreading onto the face.
  Millimetres, though VRML carries no units. For Stratasys PolyJet (GrabCAD Print) and
  Shapeways.
- Every file is under 950,000 triangles (Shapeways' colour limit is one million).

## 15. Verification (`verify_lifelike.py`)

From the files alone, for each part:

- the 3MF is one valid closed solid with no zero-area triangle, under 950,000 triangles; where
  lib3mf is installed, it reads the file in strict mode with no warning;
- the VRML has the same points and triangles, one colour per point, each a colour its corners
  carry in the 3MF;
- each engraved line, sliced 0.5 mm into its face, opens as many glyphs as its text has, with at
  least 0.55 mm between them; every specification line is on some face; every engraved number is
  the truth;
- re-measured on the file: the opening sliced 0.003 mm under the skin plane (area and perimeter
  within 1 %, length and width within 1 % + 0.1 mm), the volume (0.01 % + 0.05 mm³), the maximum
  depth (0.001 mm), W4's hidden volume (0.01 % + 0.05 mm³) and its pocket's height and roof at
  11, 12 and 1 o'clock (0.05 mm);
- the bed's upward-facing triangles inside the margin, classed by nearest tissue colour, give
  the labelled shares within 8 points.

## 16. Reproducing

**The design**, with numpy, scipy and matplotlib only — anywhere, including the sandbox of an AI
assistant that runs Python: `python preview_design.py` recomputes everything that does not need
the mesh with the build's own functions — the outline's sizes and longest diameter, tissue shares
and percentages, where each periwound change shows, W4's undermining extents — and checks them
against the truth, to rounding. It estimates maximum depth, volume, block height and tissue
colours on a 0.15 mm grid (within 0.05 mm, 2 % and 8/255 of the truth) and draws each wound from
above: in colour, as a tissue map and as depth. About 30 seconds for all eight.

**The print files**: Python 3.11 with the versions in `requirements-lifelike.txt`
(`requirements.txt` in the kit) — cadquery for the lettering; manifold3d, triangle, numpy and
scipy for the meshes:

    pip install -r requirements-lifelike.txt
    python make_lifelike.py           # all eight, about 5 minutes and 1.1 GB; or name parts: W4 W6
    python verify_lifelike.py         # must print ALL OK
    python render_lifelike.py         # optional pictures; headless Linux needs libosmesa6

**Byte for byte**: the build is deterministic. With the same versions on Linux x86-64 it writes
the same model and VRML text; `check_reproduction.py` compares a rebuild's content hashes and
truth with a reference (`data/` in the kit) and reports IDENTICAL, or EQUIVALENT where other
versions or platforms triangulate differently but every truth value and label agrees within its
tolerance. The labels are cut from DejaVu Sans Mono Bold; the kit bundles the file the parts were
built with (`code/fonts/`), which `make_phantoms_step.py` takes before any installed copy.

`make_repro_kit.py` assembles the kit: this specification, a data card per wound, every design
input as JSON, the truth, the content hashes, the code with its font and requirements, pictures
and the printing notes, with a guide for using it with an AI assistant such as ChatGPT.

## 17. Changing a wound

Edit its entry in `WOUNDS` (`make_lifelike.py`): `a`, `b`, `rot` and `harm` for the outline;
`D` and `k` for depth and wall; `tissue` for target shares (they must sum to 1); `islands`,
`pale`, `bone` and `undermine` for those features; `peri` for the periwound changes and
`peri_names` for what is engraved about them; `skin` for the skin type; `seed` for a different
random texture. Then rebuild, verify and re-render that part. The truth, labels and pictures
follow from the geometry; nothing is typed in by hand.

## 18. Printing

Full colour, matte (PolyJet Matte finish), solid, millimetres — choose millimetres when the
software asks, since VRML has no units. Send PolyJet shops the VRML; Xometry the 3MF. Ask for a
skin-tone colour profile (GrabCAD "Vivid 1.1 D50 Relative"). Clear all support from W4's pocket.
Check each part against its picture and labels on arrival, and measure with calipers.
`ORDER-SHEET.md` has the full order.

## 19. Sources and limits

Clinical descriptions: NPIAP 2016 staging (Edsberg et al., J Wound Ostomy Continence Nurs 2016),
the BMJ ABC of Wound Healing (2006), Bowers and Franco (Am Fam Physician 2020) and the WUWHS 2018
consensus on surgical wound dehiscence. Granule size and height and the eschar's fissures are
design choices; no clinical source gives them in millimetres. Colours are targets to roughly
10–20 ΔE, not measurements of tissue, and printers reproduce them only approximately. The
booleans leave a few needle-thin (but never zero-area) triangles where W4's pocket ends meet the
wound wall; the 3MF specification allows them.
