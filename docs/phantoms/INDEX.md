# Test phantoms — index

Printable ground-truth phantoms for bench-testing wound measurement. Each block carries one
cavity whose volume, opening area and maximum depth are known in closed form, so a scan can
be scored against an exact number rather than against another measurement.

## Current: revision B, exact STEP

`make_phantoms_step.py` builds all twelve parts as exact B-rep and writes STEP AP214. **Send
these to a print service.**

| File | What it is |
|---|---|
| `make_phantoms_step.py` | Generator. Writes the twelve `.step` files and `truth_step.json`. |
| `step/*.step` | The twelve parts, ready to upload. |
| `truth_step.json` | Per-part ground truth and delivered material volume. |
| `verify_walls.py` | Measures the minimum wall of every hollow part on the B-rep. |
| `verify_step.py` | Re-imports every STEP file cold and checks it is one valid closed solid. |
| `ORDER-SHEET.md` | What to send a print service. |

### Regenerating

    python3 -m venv .venv
    .venv/bin/pip install cadquery          # pulls OpenCASCADE; a few hundred MB
    .venv/bin/python make_phantoms_step.py  # add --no-text to skip the spec plates
    .venv/bin/python verify_walls.py
    .venv/bin/python verify_step.py

`make_phantoms_step.py` asserts every cavity against its closed form and refuses to write a
part that is off by more than 0.01 %. `verify_walls.py` measures the minimum distance from
each part's internal void to its outer boundary — the number a print service's
wall-thickness check reports.

### Verified results

| Part | Cavity volume, closed form | Cavity volume, B-rep | Error | Min wall | Min wall at engravings | Material |
|---|---|---|---|---|---|---|
| P1 | 7,068.583 mm³ | 7,068.583 mm³ | 0.000000% | 3.500 mm | 3.000 mm | 58.7 cm³ |
| P2 | 32,724.923 mm³ | 32,724.923 mm³ | 0.000000% | 3.500 mm | 3.000 mm | 73.5 cm³ |
| P3 | 4,188.790 mm³ | 4,188.790 mm³ | 0.000000% | 3.500 mm | 3.000 mm | 52.2 cm³ |
| P4 | 11,309.734 mm³ | 11,309.734 mm³ | 0.000000% | 3.500 mm | 3.000 mm | 54.5 cm³ |
| P5 | 603.186 mm³ | 603.186 mm³ | 0.000000% | solid | solid | 56.9 cm³ |
| P6 | 0.000 mm³ | 0.000 mm³ | 0.000000% | solid | solid | 57.5 cm³ |
| P7 | 4,677.547 mm³ | 4,677.547 mm³ | 0.000005% | 3.500 mm | 3.000 mm | 52.5 cm³ |
| P8 | 4,857.876 mm³ | 4,857.845 mm³ | 0.000636% | 3.500 mm | 3.000 mm | 55.6 cm³ |
| P9 | 7,068.583 mm³ | 7,068.583 mm³ | 0.000011% | 3.500 mm | 3.000 mm | 73.7 cm³ |
| P10 | 15,079.645 mm³ | 15,079.645 mm³ | 0.000000% | 3.500 mm | 3.000 mm | 59.2 cm³ |
| L1 | 6,031.858 mm³ (solid) | 6,031.858 mm³ | 0.000000% | solid | solid | 6.0 cm³ |
| L2 | 6,031.858 mm³ (solid) | 6,031.858 mm³ | 0.000000% | solid | solid | 6.0 cm³ |

Twelve files, 606 cm³ of material. Every STEP file re-imports as one valid, closed solid whose volume matches the build to within 0.001 %. The 3.000 mm figure is the 3.5 mm wall less the 0.5 mm top-face engraving directly above the void.

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
representation and the hollowing differ. The revision A files are kept because
`truth.json` is referenced by the undermining validation in the engine.
