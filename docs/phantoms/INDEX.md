# Test phantoms — index

Printable ground-truth phantoms for bench-testing wound measurement. Each block carries one
cavity whose volume, opening area and maximum depth are known in closed form, so a scan can
be scored against an exact number rather than against another measurement.

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
