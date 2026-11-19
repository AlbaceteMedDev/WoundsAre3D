# Test phantoms — index

Printable ground-truth phantoms for bench-testing wound measurement. Each block carries one
cavity whose volume, opening area and maximum depth are known exactly, so a scan can be scored
against an exact number rather than against another measurement. There are two sets: the
P-series (revision C, below), exact closed-form shapes in natural grey for measuring geometry,
and the lifelike W-series (further down), real-looking wounds in full colour on six skin tones.

## Current: revision C, exact STEP with legible labels

`make_phantoms_step.py` builds all twelve parts as exact B-rep and writes STEP AP214
(`verify_step.py` checks the schema; revision B wrote AP203 for all but its first file). **Send
these to a print service** with `ORDER-SHEET.md`.

| File | What it is |
|---|---|
| `make_phantoms_step.py` | Generator. Writes the twelve `.step` files and `truth_step.json`. |
| `step/*.step` | The twelve parts, ready to upload. |
| `truth_step.json` | Per-part ground truth, delivered material, vents, and every engraved label. |
| `verify_labels.py` | Slices every labelled face and checks each label glyph by glyph. Writes `labels_preview/`. |
| `verify_walls.py` | Minimum wall of every hollow part, plain and with every engraving cut. |
| `verify_step.py` | Re-imports every STEP file cold and checks it is one valid closed solid. |
| `labels_preview/*.png` | Each labelled face of each part, sectioned 0.5 mm in — what the print should read. |
| `make_parts_sheet.py`, `parts_sheet.pdf` | A picture of every part beside its sizes; then each part's file, how to recognise it, and its opening, depth, area, perimeter and volume; P10's lid-seated values and undermining by clock position. Every size in mm and cm. |
| `render_parts.py`, `renders/*.png` | The pictures: each STEP file rendered at one scale and from one angle. |
| `make_label_sheet.py`, `label_sheet.pdf` | Stick-on labels for parts printed from revision B. |
| `ORDER-SHEET.md` | What to send a print service. |

### What each part says

Each block's **side walls** carry its part number, maximum depth, opening area and cavity
volume — readable with the part sitting cavity-up. Its **underside** carries the fuller
specification: shape, the dimensions that define it, and the same values. Its **top** carries
the part number, the four fiducial dots and the 50.000 mm key line. P9's opening area is given
two ways, since its skin is curved: `PLAN` 1413.72 mm² as seen from above, and `SKIN`
1446.60 mm² measured on the cylinder itself; its depth is 10.000 mm below the crown. P10's labels give
its truths **with a lid seated** — opening, depth, total, seen and hidden volume, undermined
area — since that is how it is used. Each lid carries its hole diameter and offset on its
**underside**, in the ring that rests on P10's pocket floor; its top is skin around the wound
and stays clean.

P10 and its lids are **keyed**: an index groove on P10's top marks 3 o'clock, and each lid
has a notch in its rim on the side its hole is offset to; 12 o'clock is then the edge nearest
the "P10" engraved on the top face.
Seat the lid with its notch at the groove, and L2's undermining extents match the clock table
in `truth_step.json` (2.000 mm at 3 o'clock to 14.000 mm at 9 o'clock). Without that the lid
turns freely and the table means nothing.

Every engraving is 1.0 mm deep along the surface normal, including under P9's curved top, at
4.5–6 mm cap height in DejaVu Sans Mono Bold, all in capitals. The lettering is adjusted for
MJF in three ways:

- **Capitals only, units included** (`MM`, `MM2`, `MM3`; `A` and `B` for semi-axes). The face's
  lowercase m, a and b join their arches to their stems through necks that engrave at
  0.28–0.38 mm, below HP's 0.5 mm minimum slit.
- **Zeros are plain rings.** The face's zero carries a dot, and the ridge between dot and ring
  would be 0.2 mm wide.
- **Letters at least 0.6 mm apart.** Every pair gets a further 0.06 × cap of spacing, and any
  pair still closer than 0.6 mm — R-A, at 0.37 mm, the worst — is pushed apart until it is
  not. On the lids the check is repeated after the line is bent round its arc, since bending
  closes the gaps at the letters' inner ends.

Measured on the delivered geometry the median groove is 0.76–0.79 mm on the 4.5 mm lines and
1.06 mm at 6 mm. That meets HP's MJF text rule (depth ≥ 1 mm, slits ≥ 0.5 mm) and
Materialise's (line ≥ 0.5 mm, depth 1 mm), and JLC3DP's 0.8 mm from about 5 mm cap up — most
parts' side labels are 5–6 mm; P4, P5, P9, the lids and the top "50.000" are at 4.5 mm. It does
not meet HLH Rapid's 1 mm groove and 1 mm land everywhere, which would take a cap height of
7–9 mm, more than the side walls hold. The narrowest grooves left are local necks in B, M,
3, 6, 8 and 9, about 0.43–0.5 mm at 4.5 mm cap, measured on the font's outlines. The measurements are on the side walls and top,
which face sideways or up in the build, the orientations MJF engraves most sharply; the
underside block faces down and is the copy to expect softest.

### Regenerating

    python3 -m venv .venv
    .venv/bin/pip install cadquery          # pulls OpenCASCADE; a few hundred MB
    .venv/bin/python make_phantoms_step.py  # all parts; name some (P9 L2) to build just those
    .venv/bin/python verify_labels.py
    .venv/bin/python verify_walls.py
    .venv/bin/python verify_step.py
    .venv/bin/python make_label_sheet.py
    .venv/bin/python render_parts.py        # headless Linux also needs: apt install libosmesa6
    .venv/bin/python make_parts_sheet.py    # also needs: .venv/bin/pip install reportlab

The generator needs the DejaVu Sans Mono Bold font file — from `fonts-dejavu-core`, from
matplotlib, or wherever `PHANTOM_FONT` points — and stops if it cannot find it: asked for a
missing font, OpenCASCADE quietly substitutes another, whose metrics the layout does not fit.
It asserts every cavity against its closed form and refuses to write a part that is off by
more than 0.01 %, or a label that will not fit at 4.5 mm cap height. `verify_labels.py`
slices each labelled face at 0.1 mm, 0.9 mm and 1.2 mm: every glyph must be open at the first
two and none at the third, counted independently from the label's text; at least 0.55 mm of
material must stand between neighbouring letters; and any other opening must be a feature
the part is meant to have. `verify_walls.py` measures the minimum distance from each part's
internal void to its outer boundary — the number a print service's wall-thickness check
reports.

The hollow blocks' voids are vented through the floor at two opposite corners. P8's is in
two halves, each reaching one vent: its grown trough would otherwise have stopped 0.36 mm
short of the void's end walls, leaving a slit too narrow to clear of powder, so it is run
through them.

### Verified results

| Part | Cavity volume, closed form | B-rep | Error | Min wall | Behind engravings | Labels | Glyphs | Min land | Material |
|---|---|---|---|---|---|---|---|---|---|
| P1 | 7,068.583 mm³ | 7,068.583 mm³ | 0.000000% | 3.500 mm | 2.500 mm | 11 | 143 | 0.600 mm | 57.6 cm³ |
| P2 | 32,724.923 mm³ | 32,724.923 mm³ | 0.000000% | 3.500 mm | 2.500 mm | 11 | 147 | 0.600 mm | 72.6 cm³ |
| P3 | 4,188.790 mm³ | 4,188.790 mm³ | 0.000000% | 3.500 mm | 2.500 mm | 11 | 131 | 0.600 mm | 50.9 cm³ |
| P4 | 11,309.734 mm³ | 11,309.734 mm³ | 0.000000% | 3.500 mm | 2.500 mm | 11 | 150 | 0.600 mm | 53.8 cm³ |
| P5 | 603.186 mm³ | 603.186 mm³ | 0.000000% | solid | solid | 11 | 140 | 0.600 mm | 55.5 cm³ |
| P6 | 0.000 mm³ | 0.000 mm³ | 0.000000% | solid | solid | 10 | 112 | 0.600 mm | 56.0 cm³ |
| P7 | 4,677.547 mm³ | 4,677.547 mm³ | 0.000005% | 3.500 mm | 2.500 mm | 13 | 159 | 0.600 mm | 51.0 cm³ |
| P8 | 4,857.876 mm³ | 4,857.876 mm³ | 0.000001% | 3.500 mm | 2.500 mm | 11 | 135 | 0.600 mm | 54.3 cm³ |
| P9 | 7,068.583 mm³ | 7,068.583 mm³ | 0.000011% | 3.500 mm | 2.500 mm | 13 | 170 | 0.600 mm | 73.4 cm³ |
| P10 | 15,079.645 mm³ | 15,079.645 mm³ | 0.000000% | 3.500 mm | 2.500 mm | 19 | 260 | 0.600 mm | 57.6 cm³ |
| L1 | lid | | | solid | solid | 2 arcs | 26 | 0.602 mm | 5.8 cm³ |
| L2 | lid | | | solid | solid | 2 arcs | 26 | 0.602 mm | 5.8 cm³ |

Twelve files, 594 cm³ of material. P10's volume is the chamber the build checks; its labels and `truth_step.json` give the lid-seated truths. Every label passes `verify_labels.py` glyph for glyph at full depth with no unexpected opening on any face; every STEP file re-imports cold as one valid closed AP214 solid whose volume matches the build to within 0.0008 % (`verify_step.py` allows 0.01 %). The 2.500 mm figure is the 3.5 mm wall less the 1.0 mm engraving directly over the void. Glyphs counts the openings the side-wall and underside labels cut (the lids: both arcs); min land is the narrowest strip of material between two letters on any face.

## Lifelike colour set: W1–W8

The P-series are exact shapes in natural grey, for measuring geometry. The W-series look like
real wounds: irregular margins and uneven beds; velvety granulation, slough, cracked eschar, new
epithelium at the margins (and in islands where a wound is partial-thickness) and, in the stage 4
injury, exposed bone; erythema, haemosiderin staining, maceration, callus with blood in it, a
rolled edge, ashen pale skin and suture marks around them — in full colour on six skin tones.
They test what the P-series cannot: finding the wound edge and classifying tissue on something
that looks like a patient. Every size is still known exactly, because it is measured on the mesh
that is printed.

| File | What it is |
|---|---|
| `make_lifelike.py` | Generator. Designs each wound as functions of position — outline, depth, tissue map, periwound — samples them on a mesh that follows the wound margin exactly, colours every vertex, adds W4's undermining and cuts the labels with mesh booleans that carry the colour. Writes `lifelike/` and `truth_lifelike.json`. |
| `lifelike/*.3mf` | Colour 3MF, millimetres: colour per triangle corner (3MF Materials extension). For Xometry and HP Multi Jet Fusion colour. |
| `lifelike/*.wrl.zip` | VRML 2.0, millimetres, one colour per vertex — no `colorIndex`, which some readers ignore. For Stratasys PolyJet through GrabCAD Print, and for Shapeways. |
| `truth_lifelike.json` | Per part: wound type, skin type, each periwound change and where it shows, length, width, longest diameter, maximum depth, area, perimeter, volume, tissue shares (of the area seen from above and of the bed's surface) and whole percentages, each tissue's mean printed colour, W4's undermining by clock position, and every engraved label with its position. |
| `verify_lifelike.py` | Re-opens each 3MF and VRML and checks them from the files alone (below). |
| `render_lifelike.py`, `renders/lifelike/*.png` | Colour pictures from the 3MF files: the part at the P-series' scale and angle, and the wound from above. |
| `LIFELIKE-SPEC.md` | The full specification: coordinates, every formula, colours and their sources, labels, files, truth and verification. |
| `preview_design.py` | The design without meshing, with numpy, scipy and matplotlib only: recomputes and checks everything that does not need the mesh and draws each wound as designed. Runs where the meshing libraries cannot be installed, such as an AI assistant's sandbox. |
| `make_repro_kit.py`, `check_reproduction.py`, `requirements-lifelike.txt` | The reproduction kit (below); a check that a rebuild matches the printed parts byte for byte; and the exact versions they were built with. |

`parts_sheet.pdf` pages 5–7 show every W part with its picture, sizes in mm and cm, and tissue
shares beside a swatch of each tissue's mean colour on that part. `ORDER-SHEET.md` says how to
print them.

### The eight wounds

| Part | Wound | Skin type | Periwound | L × W × D (mm) | Area (mm²) | Perimeter (mm) | Volume (mm³) | Tissue % G / S / N / E |
|---|---|---|---|---|---|---|---|---|
| W1 | Venous Leg Ulcer | II | Haemosiderin, erythema, maceration | 46.6 × 30.8 × 2.42 | 950.3 | 121.7 | 1054.3 | 55 / 25 / 0 / 20 |
| W2 | Diabetic Foot Ulcer | IV | Callus, maceration, blood in callus | 15.8 × 14.3 × 4.67 | 175.7 | 47.3 | 569.5 | 70 / 20 / 10 / 0 |
| W3 | Pressure Injury S3 | V | Rolled edge, erythema | 32.5 × 27.9 × 7.56 | 688.7 | 95.8 | 3164.1 | 65 / 30 / 0 / 5 |
| W4 | Pressure Injury S4; undermined 10–2 o'clock, max 10.0 mm in a 5.0 mm pocket, hidden 1038.9 mm³ | III | Erythema, maceration | 30.8 × 23.7 × 15.38 | 568.2 | 86.4 | 6547.9 | 38 / 40 / 19 / 0 + bone 3 |
| W5 | Unstageable Eschar | I | Erythema | 32.0 × 26.3 × 1.96 | 628.2 | 91.0 | 573.9 | 0 / 15 / 85 / 0 |
| W6 | Arterial Ulcer | VI | Pale shiny | 14.2 × 12.0 × 4.19 | 132.2 | 41.0 | 394.9 | 20 / 50 / 30 / 0 |
| W7 | Surgical Dehiscence | IV | Erythema, suture marks | 44.0 × 12.4 × 6.79 | 415.0 | 95.3 | 1879.3 | 75 / 15 / 0 / 10 |
| W8 | Healing Wound | II | Intact | 25.8 × 20.2 × 1.39 | 408.1 | 74.7 | 192.2 | 40 / 0 / 0 / 60 |

G / S / N / E: granulation, slough, necrotic, epithelial, as whole percentages of the wound area
seen from straight above; W4 also shows exposed bone.

Where each periwound change shows — the area over which its colour weighs at least 0.3, the clock
hours that area spans, and how far it reaches from the margin along a line from the wound centre:

| Part | Periwound change | Area (mm²) | Clock hours | Reaches (mm) |
|---|---|---|---|---|
| W1 | haemosiderin | 401.4 | all round | 11.6 |
| W1 | erythema | 480.2 | all round | 6.5 |
| W1 | maceration | 40.4 | 5, 6, 7 | 2.9 |
| W2 | callus | 236.7 | all round | 5.9 |
| W2 | blood in callus | 7.8 | 1, 2, 3, 4, 5, 6, 7, 10, 12 | 5.4 |
| W2 | maceration | 63.7 | all round | 1.2 |
| W3 | erythema | 708.8 | all round | 8.9 |
| W3 | rolled edge | 34.8 | 5, 6, 7, 8 | 1.6 |
| W4 | erythema | 514.4 | all round | 9.3 |
| W4 | maceration | 47.8 | 5, 6, 7, 8 | 3.1 |
| W5 | erythema | 422.4 | all round | 7.0 |
| W6 | pale shiny skin | 228.1 | all round | 9.5 |
| W7 | erythema | 219.8 | all round | 4.9 |
| W7 | incision line | 6.7 | 6, 12 | 3.8 |
| W7 | suture marks | 6.3 | 1, 2, 3, 4, 5, 7, 8, 9, 10, 11 | 11.4 |
| W8 | intact skin | | | |

### What each part says

Each part is labelled like the P-series, 1.0 mm deep in capitals, and the grooves are coloured —
dark on the light grey sides and underside, dark or light on the skin by contrast (at least 4.5:1).
Between them, the underside and the side walls carry the part and wound type, `L W D`, area,
perimeter, volume, tissue percentages, every periwound change, the skin type and W4's undermining:
the underside takes up to twelve lines and the side walls repeat the main figures, and where the
underside has no room for a line (the skin type, or a periwound change) a side wall carries it.
`verify_lifelike.py` checks that every line is on one face or the other. The top carries the part
number, the four fiducial dots and the 50.000 mm key line, as on the P-series.

Abbreviations on the parts: `L W D` length, width and maximum depth, mm; `PERIM` perimeter;
`MM2`, `MM3` mm², mm³; `PCT` percent of the wound area; `GRAN` granulation; `EPI` epithelial;
`PERI` periwound; `ST3`, `ST4` stage 3, stage 4; `HIDDEN` the undermining's hidden volume.

### How the numbers are defined

- **Length** is the wound's extent from 12 to 6 o'clock (12 is the edge with the part number)
  and **width** its extent from 3 to 9 — the clock method. Every wound lies roughly along 12–6,
  so the length is the longer; its longest diameter, the angle of that diameter and the width
  across it are in `truth_lifelike.json`, for devices that measure that way.
- **Area** and **perimeter** are of the wound margin, in plan. The mesh follows the margin
  exactly, so these are the margin polygon's.
- **Maximum depth** and **volume** are from the plane of the surrounding skin (the block's top),
  not from a callus or rolled edge standing above it. Volume is the space between that plane and
  the wound bed inside the margin, measured on the mesh.
- **Undermining** (W4) is measured from the margin outward, along a line from the wound
  centre, as a probe would. The pocket is a slot 5.0 mm high under a 2.0 mm roof
  with a half-round end, so a probe with a ball tip up to 5 mm across slides in to the full
  extent at 11, 12 and 1 o'clock; its **hidden volume** is the pocket beyond the margin.
- **Tissue shares** are fractions of the wound's area seen from straight above, from the tissue
  map on a 0.05 mm grid. On steep walls a share of the bed's surface differs — W4's slough covers
  more of its walls than of its plan — so the JSON gives those too, below.

| Part | Longest diameter (mm), angle from 12–6 | Width across it (mm) | Bed surface (mm²) | Tissue by surface % G / S / N / E |
|---|---|---|---|---|
| W1 | 46.8 at +6° | 29.5 | 991.8 | 55 / 25 / 0 / 20 |
| W2 | 16.1 at +13° | 14.3 | 294.4 | 75 / 16 / 9 / 0 |
| W3 | 33.0 at -17° | 27.9 | 972.8 | 64 / 27 / 0 / 9 |
| W4 | 30.8 at +1° | 23.8 | 1538.0 | 36 / 48 / 14 / 0 + bone 2 |
| W5 | 32.3 at +23° | 25.2 | 667.9 | 0 / 15 / 85 / 0 |
| W6 | 14.2 at +3° | 12.0 | 235.7 | 19 / 53 / 28 / 0 |
| W7 | 44.0 at +0° | 12.5 | 744.7 | 66 / 14 / 0 / 20 |
| W8 | 26.4 at -14° | 20.4 | 417.3 | 41 / 0 / 0 / 59 |

### Where the look comes from

- **Shapes and textures** follow clinical descriptions: the NPIAP 2016 staging definitions
  (Edsberg et al., J Wound Ostomy Continence Nurs 2016) for the pressure injuries — a stage 4
  shows bone, tendon or muscle, so W4 shows bone; the BMJ ABC of Wound Healing (2006) — venous
  ulcers with gently sloping edges, granulation under fibrin and haemosiderin; arterial ulcers
  punched out with a pale, non-granulating base and shiny surrounding skin; neuropathic foot
  ulcers crater-like inside a thick ring of callus; Bowers and Franco, Am Fam Physician 2020; and
  the WUWHS 2018 consensus on surgical wound dehiscence. Granule size and height (about 1 mm,
  0.1–0.2 mm high) and the eschar's fissures are design choices: no clinical source gives them
  in millimetres.
- **Skin tones** are medians of 697 reflectance spectra measured on faces (the University of
  Oulu Physics-Based Face Database, Marszalec et al., J Electron Imaging 2000, and RIT's
  Lippmann2000), binned by individual typology angle and matched to Fitzpatrick type by the
  median angle of each perceived type in 789 adults (Lipnick et al., Br J Dermatol 2026). Measured
  skin is darker and redder than swatch scales such as Monk's, whose prints read too bright.
- **Tissue colours**: granulation is within about 7 ΔE00 of the median colour of the granulation
  in LUTSeg's tissue-labelled ulcer photographs (CC BY 4.0), and new epithelium has LUTSeg's pink
  hue (a* about 20–24) but is lighter, more so on light skin. LUTSeg's photographs are of leprosy-related ulcers taken on uncalibrated smartphones,
  so slough and eschar follow the clinical descriptions instead — tan-to-cream slough, with
  LUTSeg's pinkish tan only where thin fibrin lies over granulation, and dark brown-black eschar,
  never pure black. Redness on the darker skin types is a deepening or violaceous tone, and pallor
  is ashen. These are targets to roughly 10–20 ΔE, not measurements of tissue.

### Regenerating

In the virtual environment above — the W-series uses `make_phantoms_step.py` for its lettering,
which needs cadquery:

    .venv/bin/pip install -r requirements-lifelike.txt   # the versions the files were built with
    .venv/bin/python make_lifelike.py       # about 5 minutes; name parts (W4) to build only those
    .venv/bin/python verify_lifelike.py     # lib3mf is optional: without it that one check is skipped
    .venv/bin/python render_lifelike.py     # headless Linux also needs: apt install libosmesa6
    .venv/bin/python make_parts_sheet.py
    .venv/bin/python make_repro_kit.py      # build/lifelike_wound_phantoms_kit.zip

`verify_lifelike.py` re-opens each part's files and checks, from them alone: the 3MF is one valid
closed solid under 950,000 triangles with no zero-area triangle, and lib3mf (the 3MF Consortium's
reader) opens it in strict mode without a warning; the VRML holds the same points and triangles
with one colour per point, each a colour its corners carry in the 3MF; every engraved line, sliced
0.5 mm into its face, opens exactly as many glyphs as its text has (counted from the font), with
at least 0.55 mm of material between them, and every line of the specification is on some face;
every engraved number is the truth; the opening (sliced just under the skin plane), the volume, the
maximum depth, W4's hidden volume and its pocket's height under the roof, re-measured on the file,
match the truth; and the wound bed's triangles, classed by nearest tissue colour, give the
labelled tissue shares within 8 points.

### Reproduction kit

`make_repro_kit.py` packs everything needed to reproduce the set into one zip of about 9 MB,
`build/lifelike_wound_phantoms_kit.zip` (not committed): `LIFELIKE-SPEC.md`, a data card per wound,
every design input as JSON with colours in CIELAB, the truth, content hashes of the print files,
the code with the exact font and pinned versions, the pictures, the parts-sheet pages and the
order notes — and a guide, with prompts, for an AI assistant that runs Python, such as ChatGPT.
In such a sandbox, which cannot install the meshing libraries, `preview_design.py` recomputes and
checks the outline sizes, tissue shares, periwound and undermining extents and draws each wound as
designed. On a computer the kit rebuilds the print files, and `check_reproduction.py` confirms
they are byte for byte those of the printed parts: W4 and W6, rebuilt from an unpacked kit, were.

### Verified results

| Part | Triangles | Colours | Labels | Narrowest land (mm) | Opening area, slice / truth (mm²) | Volume, file / truth (mm³) | Max depth (mm) | Tissue by colour G / S / N / E (%) | Labelled (%) |
|---|---|---|---|---|---|---|---|---|---|
| W1 | 419,954 | 19,755 | 22 | 0.600 | 949.14 / 950.28 | 1054.25 / 1054.25 | 2.42 | 56 / 26 / 0 / 18 | 55 / 25 / 0 / 20 |
| W2 | 322,820 | 5,235 | 21 | 0.600 | 175.65 / 175.68 | 569.50 / 569.50 | 4.67 | 71 / 21 / 8 / 0 | 70 / 20 / 10 / 0 |
| W3 | 405,968 | 14,673 | 22 | 0.600 | 688.59 / 688.71 | 3164.08 / 3164.08 | 7.56 | 66 / 31 / 0 / 4 | 65 / 30 / 0 / 5 |
| W4 | 449,782 | 15,743 | 25 | 0.600 | 568.21 / 568.23 | 6547.89 / 6547.89 | 15.38 | 39 / 42 / 17 / 0 + bone 2 | 38 / 40 / 19 / 0 + bone 3 |
| W5 | 376,958 | 6,077 | 21 | 0.600 | 627.61 / 628.17 | 573.94 / 573.94 | 1.96 | 0 / 15 / 85 / 0 | 0 / 15 / 85 / 0 |
| W6 | 323,134 | 5,457 | 20 | 0.600 | 132.17 / 132.19 | 394.88 / 394.88 | 4.19 | 27 / 45 / 28 / 0 | 20 / 50 / 30 / 0 |
| W7 | 348,698 | 7,304 | 22 | 0.600 | 414.91 / 414.98 | 1879.34 / 1879.34 | 6.79 | 77 / 15 / 0 / 7 | 75 / 15 / 0 / 10 |
| W8 | 330,712 | 1,951 | 18 | 0.600 | 406.60 / 408.10 | 192.23 / 192.23 | 1.39 | 42 / 0 / 0 / 58 | 40 / 0 / 0 / 60 |

## Superseded: revision B

Revision B's geometry was right — exact surfaces, 3.5 mm walls along the normal — but it
failed on its labels and on one part's vents. **Do not print it.**

- **The measurements were never in the files.** The engraving step passed each line of text
  through a helper that keeps the largest solid of a compound. A line of text is a compound
  with one solid per glyph, so each line engraved a single character: P1's underside carried
  10 of its 132 characters, its top "P" for "P1" and one "0" for "50.000". The verification
  scripts measured walls and re-import validity and never counted glyphs. `verify_labels.py`
  now does.
- **What was engraved was too shallow.** 0.4 mm on the underside and 0.5 mm on the top,
  against HP's 1 mm for text and JLC3DP's 0.8 mm; and the underside, where the measurements
  were, is a down-facing surface, the worst for engraved detail in MJF.
- **P9's vents broke out through its top.** They ran along x at the void's mid-height, but
  P9's ±X walls are only 6.7 mm tall under its curved top, so the Ø8 holes emerged through the
  top face as four open slots near the corners, taking the four fiducial dots with them.
- **The lids carried no label at all.**

Parts already printed from revision B have the same cavities and remain usable as references
— except P9 as a scale reference: its fiducial dots are gone and its top has four open slots
near the corners, so use it for depth, area and volume only. `label_sheet.pdf` gives them
their labels.

Two places where the CAD stops a hair short of the closed form, both far inside print
tolerance: P9's opening is lofted through slices that stop 0.025 mm short of each tip of its
50 mm length, and the trough of P8 closes 0.03 µm above its 8 mm floor. Both are counted in
the cavity-volume check, which every part passes to better than 0.00002 %.

## Superseded: revision A, heightfield STL

`make_phantoms.py`, `truth.csv`, `truth.json`, `README.md` and `README_COMPLEX.md` describe
the earlier STL set. **Do not print it.** It failed a print service's inspection, correctly:

- The hollow was offset **vertically** by 3.5 mm, which is a true 3.5 mm wall only where the
  surface is horizontal. On a wall tilted `a` from horizontal the real thickness is
  `3.5·cos a`. P2's rim thinned to **0.361 mm** and P10's vertical well wall to
  **0.132 mm**, against a 0.80 mm process minimum. The "uniform 3.5 mm minimum wall" these
  documents claim was measured in z only, and is wrong.
- A square-grid heightfield turns circular boundaries into a 0.32 mm staircase and renders
  P10's vertical wall as a ramp tilted 1.53° off vertical — a 0.32 mm departure from the
  intended sharp edge.

The cavity geometry and closed-form truth values are unchanged between revisions; only the
representation, the hollowing and the labelling differ. The revision A files are kept because
`truth.json` and `README_COMPLEX.md` are where the undermining truths that the engine's
validation (`woundscan-engine/tests/unit/test_undermining.py`, which carries its own copy of
the values) was checked against are written out; revision C's `truth_step.json` now carries
them too. Their P7 perimeter, 126.816 mm, is 0.003 mm low: the revision A integration dropped
the closing interval of the loop. It is 126.819 mm.
