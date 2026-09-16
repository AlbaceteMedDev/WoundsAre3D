# Test phantoms — index

Printable ground-truth phantoms for bench-testing wound measurement. Each block carries one
cavity whose volume, opening area and maximum depth are known in closed form, so a scan can be
scored against an exact number rather than against another measurement.

The twelve `.stl` files are **not** committed — they are 127 MB of deterministic output. This
directory holds the generator and the truth data that produce them.

## Files

| File | What it is |
|---|---|
| `make_phantoms.py` | Generator. Writes all twelve STLs, `truth.csv` and `truth.json`. |
| `truth.json` | Per-phantom ground truth: closed-form volume, mesh volume, opening area, perimeter, key-line length, fiducial spacing, material volume. |
| `truth.csv` | The same numbers, flat. |
| `README.md` | Basic set (P1–P6): the shapes the engine's regulatory suite already validates against. |
| `README_COMPLEX.md` | Complex set (P7–P10 + lids L1/L2): non-convex boundary, elongated wound, curved limb, undermining. |
| `ORDER-SHEET.md` | What to send a print service — process, material, tolerance, orientation, per-part notes. |

## Regenerating

    python3 -m venv .venv
    .venv/bin/pip install numpy pillow      # matplotlib only for the optional preview PNGs
    .venv/bin/python make_phantoms.py       # add --solid for solid blocks instead of hollow shells

Runs in a couple of minutes and prints, per phantom, the triangle count, block height, closed-form
volume, the error of the mesh against it, the material volume and a watertightness check. Every
cavity should reproduce its analytic volume to better than 0.1 %, and every mesh should report
watertight. Passing phantom IDs as arguments (`make_phantoms.py P7 P10 L1 L2`) regenerates only
those.

The generator is deterministic — no randomness, no timestamps in the output — so a clean run
reproduces the files below byte for byte.

## Expected output

Twelve watertight binary STLs in millimetres, 454 cm³ of material for the set.

    9c5e70e3d91e1cad4f8ac8a32566690fc761bc8a8ace32c25ea64d79313a398e  P1_hemisphere_r15.stl
    58a28c0225e2ea05a8e3677f2fa6fc49f2d966d7eba33f3459309d2aab83b0ff  P2_hemisphere_r25.stl
    42ded24368c08112b270f1f958d2e3a80cd64e0dfdde1fe8381ad60cd4578062  P3_cone_r20_d10.stl
    0861a732642fdf9531d1b5ad1a66c50ebf9f0ce7ae1e09ff9e82a9ed8b30309f  P4_paraboloid_30x20_d12.stl
    b1a694e91ab036d719300843a1b436fb1229196db343696363ac6f7497901e2b  P5_paraboloid_12x8_d4.stl
    72be1f0f9491d52e2726129522a529d30cbe2a6d9efcdd448edde37026952d6d  P6_flat_plate.stl
    6cb0e82f3b38970091a6b3ef19eab559af6fbb90dc5ef48e226b08d85c2af7b8  P7_lobed_r18_d9.stl
    8e1d3c1b2a6003eb64041bccaeffa7d3a8b418728a974cde1370d752e032e144  P8_trough_L40_r9_d8.stl
    90d16ab428c5064b1db2b4e5a9e165914389898a792b2adc4feaa47a62e519c8  P9_paraboloid_on_cyl_r60.stl
    6702e1607b7d9fc2ea56c7759712230be1fc3a5530b0e3bb53d2e620eed0fef1  P10_undermining_base.stl
    81f8d7ff29898a33e57581c3a1c546bc961f5fc946add59150cf86a165a13dc6  L1_lid_concentric_r12.stl
    ba4935cfb38df4564510e3bcf2678b8eadf336464c89e93599894e06a8ef6501  L2_lid_offset6_r12.stl

All ten blocks carry the same triangle count, so the twelve files have identical byte sizes across
geometry revisions. Check the hash, not the size, before sending anything to a printer.

## P10 and the undermining acceptance case

P10 plus a lid is the fixture behind the undermining measurement in
`woundscan-engine/src/woundscan/geometry/undermining.py`. The pocket extends under intact skin,
so the scanner cannot see it — the geometry is what the clinician-probed measurement has to
reproduce. Ground truth for the assembled part:

| Quantity | Value |
|---|---|
| Visible opening area | 452.39 mm² |
| Undermined area | 804.25 mm² |
| Total area | 1 256.64 mm² |
| Visible volume | 6 785.84 mm³ |
| Undermined volume | 9 650.97 mm³ |
| Hidden fraction | 58.7 % |

L1 seats the lid concentrically; L2 offsets it 6 mm, which makes the undermining asymmetric
around the clock. Both lids are 6 031.86 mm³ of solid.
