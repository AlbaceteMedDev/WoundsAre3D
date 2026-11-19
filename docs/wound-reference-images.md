# Public images of real wounds — sources and licences

Where to find photographs and scans of actual patient wounds to use as references, and what each
source lets a company do with them. Checked on 26 October 2026: 77 sources were found and each
was re-opened independently to confirm its licence, contents and links. On 4 November 2026
CO2Wounds v1 and LUTSeg (section 1) were downloaded and checked image by image (section 5),
which corrected what is said here about their scale and provenance. A second search that day,
for segmentation sets in particular, added the rows marked *(4 Nov)* in sections 2–4; none of
them is cleared for commercial use, and none was downloaded.

**This file links to images; it does not store any.** Keep patient images out of the
repository. Download them to a controlled location and record each image's source and licence
alongside it — `woundscan-engine/scripts/fetch_wound_segmentation_data.py` does both (section 5).

## The short version

- **No public dataset gives depth or volume ground truth for real wounds under terms a company
  can use.** Real-wound 3D data exists only behind a request or a partnership (WoundsDB, the
  Zivot DFU set, the FEMH burn set — section 3). Until one of those comes through, the phantoms
  in `docs/phantoms/` are the only exact depth and volume truth we have; their lifelike colour
  set (W1–W8) also gives exact tissue-type and periwound truth on real-looking wounds.
- **For segmentation testing**, CO2Wounds v1 and LUTSeg can be used now: 305 photos, 273 of
  them distinct, with wound masks, both published under CC BY 4.0. CO2Wounds v1 is cleared for
  commercial use; keep LUTSeg to internal testing until its authors confirm its licence in
  writing (section 1). LUTSeg adds tissue masks and a subset outlined by five clinicians. A
  script downloads and checks them, and another scores a model (section 5). Neither gives a
  millimetre scale: CO2Wounds v1 has a calibration card in frame, but its size is not published.
- **For visual references**, use Wikimedia Commons, the CDC image library and the CC BY
  case reports listed below. Several of those give clinician length × width × depth in their
  captions, and a few show undermining.

## How to read the licences

| Group | Licences | What we may do |
|---|---|---|
| 1. Usable | Public domain, CC0, CC BY, CC BY-SA | Use commercially with attribution. CC BY-SA also requires adaptations to carry the same licence. |
| 1b. Confirm first | An open licence whose grant is in doubt | Internal testing with attribution. Before any commercial use (the product, its training data or its marketing), get the owners' written confirmation of the licence. |
| 2. Internal research only | CC BY-NC, CC BY-NC-SA, CC BY-NC-ND, other non-commercial terms | Internal benchmarking at a company is a grey area: get legal sign-off first. Never in the product, in training data for it, or in marketing. |
| 3. Ask first | No licence stated, or "on request" | No licence means all rights reserved. Write to the owners. |
| 4. Avoid | Terms that forbid our use outright | Do not download. |

A Creative Commons licence settles copyright, not patient consent. Most of these images carry
no image-specific consent statement, so get legal and regulatory review before any of them
appears in marketing, labelling or a regulatory submission.

## 1. Usable now

### Datasets

| Source | Contents | Ground truth | Licence and access |
|---|---|---|---|
| [CO2Wounds v1](https://data.mendeley.com/datasets/nkw5gx57hw/1) (Universidad Industrial de Santander; Monroy et al., *Comput Biol Med* 2023;165:107335) | 164 smartphone photos of chronic leprosy ulcers, 69 consenting patients, Colombia, downscaled and padded to 640 × 640 with black bars | Binary wound masks for every image. YOLO boxes: class 0 is the wound and class 1 a calibration card (nothing documents this; it was read from the masks, and all 164 agree). The card's size is not published, so there is no millimetre scale until the authors give it. No depth. | **CC BY 4.0**. Direct download, no registration. |

### Datasets to confirm first (group 1b)

| Source | Contents | Ground truth | Licence and access |
|---|---|---|---|
| [LUTSeg](https://huggingface.co/datasets/ksanchez84/LUTSeg) (2026) | 141 photos of leprosy ulcers, 39 patients, followed over 21 months | 6-class tissue masks and wound masks. A 46-image subset was outlined by 5 clinicians separately, so rater disagreement can be measured. No scale, no depth. | **CC BY 4.0 as published; confirm before commercial use.** Direct download. *Caveat:* its card says the images come from CO2Wounds v1 and keep that licence, but only 32 of the 141 are in v1 (matched pixel for pixel). The 21-month span matches CO2Wounds-V2's collection (November 2021 to August 2023), whose current licence is non-commercial; the card's provenance paragraph was added on 17 August 2026, after release, and its "original study" DOI points to an unrelated paper. The uploader is V2's first author, so the grant is plausibly the rights holder's own: fine for internal testing, but get the authors' written confirmation before any commercial use. The fetch script marks every LUTSeg row `confirm-first`, including the 32 photos also in v1, because their masks are LUTSeg's own; for commercial work use the v1 copy. |

Do not mix CO2Wounds v1 with CO2Wounds-V2 (section 2): the second is non-commercial.

### Open-access papers with measured real wounds

These are single figures or small series, but they come with numbers. Attribute the authors
and journal. Open-access articles live on PubMed Central (PMC); each link below is the PMC
article.

| Article | What it shows | Measurements | Licence |
|---|---|---|---|
| [Broder et al., *Cureus* 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5156627/) | One deep stage 4 hip pressure ulcer with undermining and tunnelling, photographed at 8 visits until healed | Clinician L × W × D at each visit (3 × 1.5 × 7.5 cm at day 1). The "volume" in the captions is L × W × D, not a measured volume. | CC BY 3.0 |
| [PMC6921535](https://pmc.ncbi.nlm.nih.gov/articles/PMC6921535/), *BMC Bioinformatics* 2019 | Smartphone structure-from-motion 3D reconstruction of real wounds, with an adhesive-tape scale in every photo | Table 1: reference area for each of 118 wounds (0.11–12.5 cm²) by film tracing on 1 mm² grid paper. The data are under a CC0 waiver. Raw images only on request. | CC BY 4.0, data CC0 |
| [Pavlovčič et al. 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4415308/), *BioMed Eng OnLine* | Laser-scanned 3D surfaces of 4 real wounds, with 8 operators' edge tracings | Repeatability only (no independent reference) | CC BY 4.0, data CC0 |
| [Dudová et al. 2025](https://actavia.sjf.tuke.sk/pdfs/ams/2025/04/05.pdf), *Acta Mechanica Slovaca* | Burn photo beside textured scans from two handheld scanners (Artec Eva, Revopoint Miraco) | Burn area per scan for 26 scan pairs, both devices. Device agreement, not a physical reference. | CC BY 4.0 |
| [Wang et al. 2017](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0183139), *PLOS ONE* | One venous ulcer, visible and infrared | Raw data spreadsheet: per-wound app measurements (45 wounds) and ruler measurements (42 wounds), plus app vs planimeter on 15 plastic model wounds. No images linked to the rows. First author co-founded Swift Medical. | CC BY 4.0 |
| [PMC10425705](https://pmc.ncbi.nlm.nih.gov/articles/PMC10425705/), [PMC12659996](https://pmc.ncbi.nlm.nih.gov/articles/PMC12659996/), [PMC10735093](https://pmc.ncbi.nlm.nih.gov/articles/PMC10735093/), [PMC8121198](https://pmc.ncbi.nlm.nih.gov/articles/PMC8121198/) | Deep sacral, buttock and ischial pressure injuries | L × W × D in the captions or tables (e.g. 18.26 × 8.22 × 7 cm). PMC12659996 states the method: ruler for L and W, cotton-tipped applicator for depth. | CC BY |
| [PMC13136722](https://pmc.ncbi.nlm.nih.gov/articles/PMC13136722/) (Figs 2G, 3A, 3D), [PMC13294340](https://pmc.ncbi.nlm.nih.gov/articles/PMC13294340/) (Figs 1B, 2A) | Pressure injuries with a ruler in frame | Rough scale checks only | CC BY |
| [Tanaka et al., *Cureus* 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12101479/) | Gluteal pressure injury with undermining, 4 time points (Fig 2 only — Fig 1 is AI-generated) | Wound area and undermining area in the captions (6.0 cm² open, 42.0 cm² undermined). Method not described. | CC BY 4.0 |
| [PMC10688995](https://pmc.ncbi.nlm.nih.gov/articles/PMC10688995/) | Abdominal wound dehiscence after hysterectomy | 10 × 4 × 3 cm, depth measured by finger | CC BY |
| [PMC7943335](https://pmc.ncbi.nlm.nih.gov/articles/PMC7943335/), *JMIR mHealth* 2021 | Pressure ulcer with an adhesive calibration marker and traced border | Study-level agreement only | CC BY 4.0 |
| [PMC10531604](https://pmc.ncbi.nlm.nih.gov/articles/PMC10531604/), *J Clin Med* 2023 | Surgical wounds measured by ruler, an iPhone LiDAR app and ImageJ | Values shown in Figs 7–8 only. Flat wounds only. | CC BY 4.0 |
| [PMC11903701](https://pmc.ncbi.nlm.nih.gov/articles/PMC11903701/), *Front AI* 2025 | Burns on curved body sites, LiDAR 3D area vs 2D area | The areas are the authors' model outputs, not independent ground truth | CC BY 4.0 |
| [PMC13604339](https://pmc.ncbi.nlm.nih.gov/articles/PMC13604339/), *Biomedicines* 2026 | Post-surgical diabetic foot wound at 3 time points, ruler in frame | None per image | CC BY 4.0 |
| [PMC13073000](https://pmc.ncbi.nlm.nih.gov/articles/PMC13073000/), *Diagnostics* 2026 | MolecuLight DX (a competing device): 4 real wounds across skin types II–VI | Method reference: two 1 cm calibration stickers, an expert-panel area consensus, and an Artec Leo 3D scanner as the depth reference. No data released. Funded by MolecuLight. | CC BY 4.0 |
| [PMC13673234](https://pmc.ncbi.nlm.nih.gov/articles/PMC13673234/), *Int Wound J* 2026 | Wounds with ArUco markers and a colour chart at skin level | Method reference: in-person calibrated-ruler sizes and dermatologist masks. The article's figures are CC BY; the raw images are not (section 2, WoundAmbit). | CC BY 4.0 |

To find more, search [Open-i](https://openi.nlm.nih.gov/) or Europe PMC, but check every
article's own licence: Open-i's CC BY filter lets non-commercial articles through.

### Individual photographs

| Source | Contents | Licence |
|---|---|---|
| [Wikimedia Commons: Pressure ulcers](https://commons.wikimedia.org/wiki/Category:Pressure_ulcers) | 28 files, of which about a dozen are clinical photos. Best: [Pressure_Ulcer_grade_4.jpg](https://commons.wikimedia.org/wiki/File:Pressure_Ulcer_grade_4.jpg), 4624 × 3472. | Per file: public domain, CC BY-SA 4.0 and others |
| [Wikimedia Commons: Diabetic foot ulcer](https://commons.wikimedia.org/wiki/Category:Diabetic_foot_ulcer) | 36 files. Cleanest provenance: the [Dayya 2022 before/after pair](https://commons.wikimedia.org/wiki/File:Wagner_Grade_1_diabetic_foot_ulcer_before_and_after_debridement_(Dayya_2022).jpg), CC BY 4.0. | Per file |
| [Wikimedia Commons: Venous ulcers of the lower limbs](https://commons.wikimedia.org/wiki/Category:Venous_ulcers_of_the_lower_limbs) | 23 files, up to 3732 × 2352. Two give L × W in their descriptions (2 × 2.6 cm; 45 × 30 mm). | Per file: CC BY-SA, CC BY |
| [Wikimedia Commons: Wounds](https://commons.wikimedia.org/wiki/Category:Wounds) | Scattered single images, including a [dehiscence after hernia repair](https://commons.wikimedia.org/wiki/File:Wound_Dehiscence_post_inguinal_hernia_repair_2014-05-27_00-46.jpg) | Per file |
| [CDC Public Health Image Library](https://wwwn.cdc.gov/phil/) | High-resolution historical photos: tropical leg ulcers ([12174](https://wwwn.cdc.gov/phil/Details.aspx?pid=12174), [28823](https://wwwn.cdc.gov/PHIL/Details.aspx?pid=28823)), a 1959 infected decubitus ulcer ([27802](https://wwwn.cdc.gov/PHIL/Details.aspx?pid=27802)) | Public domain. Credit CDC and the photographer; do not alter the substance or imply CDC endorsement. Check the "Copyright Restrictions" field on each image: some are not public domain. |

Commons licences are declared by uploaders and none of the pages checked had a consent
statement. None show a ruler. Treat them as visual references.

## 2. Internal research only (non-commercial licences)

| Source | Contents | Ground truth | Licence |
|---|---|---|---|
| [Foot Ulcer Segmentation Challenge (FUSeg)](https://github.com/uwm-bigdata/wound-segmentation/tree/master/data/Foot%20Ulcer%20Segmentation%20Challenge), MICCAI 2021 | 1,210 foot-ulcer photos: 810 train, 200 validation, 200 test | Specialist-checked wound masks for train and validation (1,010); 24 are empty (healed), and 7 photos appear in both train and validation | CC BY-NC (version not stated), in the challenge's data usage agreement; the repository has no licence file |
| [CO2Wounds-V2](https://data.mendeley.com/datasets/s2w7rjwz49/2) | 764 photos of leprosy ulcers, 96 patients, November 2021 to August 2023 | Wound masks for 607 (485 train, 122 validation); 24 groups of byte-identical photos, 8 of them across train and validation | CC BY-NC 3.0 on Mendeley version 2; the paper and its GitHub say CC BY-NC-ND. Mendeley version 1 (published 1.7 hours earlier, still online, same files) and the IEEE DataPort copy say CC BY 4.0. Ask the authors or legal before relying on the CC BY copies. |
| [WoundSeg (WSNet)](https://huggingface.co/datasets/subbareddyoota/wseg_dataset), WACV 2023 | 2,686 photos across 8 wound types, 224–331 px | Masks covering wound plus surrounding skin, so they cannot be scored against wound-bed masks | CC BY-NC 4.0. A Mendeley re-release labels the same images CC BY; do not rely on it. |
| [PI-Net / MIPI](https://zenodo.org/records/22032032), 2026 | 406 full-resolution clinical pressure-injury photos from 6 institutions | Pixel masks by stage | CC BY-NC-SA 4.0. Files restricted: request access on Zenodo. |
| [WoundAmbit](https://github.com/VanessaBorst/woundambit) (University Hospital Würzburg) | 20 wound photos with 4 ArUco markers and a colour chart in frame | Sizes estimated by 3 dermatologists | Non-commercial data licence. The only public set with a fiducial at skin level. |
| [SALVE](https://data.csiro.au/collection/csiro%3A64747v1) (CSIRO, WACV 2025) | **Silicone wounds, not patients.** iPhone and webcam video with a 3D-scanner point cloud as truth. | Scanner geometry | CC BY-NC-SA 4.0. The closest public match to our 3D problem; read the paper's benchmark. |
| [Syn3DWound](https://lebrat.github.io/Syn3DWound/) (CSIRO) | **Synthetic**, not patients | Exact 3D wound beds and masks | CC BY-NC-SA 4.0 |
| [SfM-3DULC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8684855/), *Int Wound J* 2021 | Photogrammetry of leg wounds: depth and volume against a fitted reference surface | Method only | CC BY-NC-ND 4.0 |
| [Aarts et al. 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9909710/), *Dermatology* | The same wound measured by eKare inSight (a 3D wound camera) and a marker-based phone app | Competitor output example | CC BY-NC 4.0 |
| [WOUND_CHU](https://github.com/petermich29/CHU_WOUND) (CHU Tambohobe, Madagascar), 2026 *(4 Nov)* | A public extract of 101 photos, one per wound, from 788 taken over up to 35 visits | Tissue masks: necrotic, slough, granulation, epithelial | CC BY-NC 4.0. The full set is on request under a research-only data sharing agreement. |
| [SRRSH-DF](https://github.com/Jiao0416/Download-SRRSH-DF-) (Sir Run Run Shaw Hospital and Hangzhou Dianzi University) *(4 Nov)* | 1,600 diabetic-foot photos; 10 samples public | Segmentation outlines (LabelMe JSON), classes undocumented | Non-commercial terms in its agreement; apply by email with a proposal and an institutional letter |
| [Redscar](https://redscar.uib.es/dataset.html) (University of the Balearic Islands, Hospital Son Espases) *(4 Nov)* | 394 post-surgical abdominal wounds closed with staples, taken on patients' phones; infection labels | Wound and staple masks | No licence ("all rights reserved"); the app's terms and the trial consent rule out commercial use. Registration. |
| [WoundTissue](https://github.com/akabircs/WoundTissue) (Kabir et al., arXiv 2502.10652) *(4 Nov)* | 147 photos by its README, taken from the DFU and Medetec collections; only 13 pairs are public so far | Tissue masks: granulation, slough, maceration, necrosis, tendon, bone | CC BY-NC-SA 4.0 for the labels; the photos keep their owners' rights |

After legal sign-off, `fetch_wound_segmentation_data.py --noncommercial fuseg woundseg co2wounds-v2`
fetches the first three, each pinned to a version and checked against the publisher's hashes,
into a folder of their own (section 5).

## 3. Ask the owners first

The first three are the only real-wound 3D or depth data found anywhere. They are worth a
partnership enquiry.

| Source | Contents | Status |
|---|---|---|
| **WoundsDB**, Silesian University of Technology ([chronicwounddatabase.eu](https://chronicwounddatabase.eu/); Kręcichwost et al., *Comput Med Imaging Graph* 2021, PMID 33477091) | 188 image sets of real chronic wounds: photo, thermal, stereo, depth map and 3D mesh, with expert outlines | Site down on 26 October 2026 (expired certificate). Download needs registration; terms unconfirmed. **Top lead** — contact the authors. |
| **Zivot DFU set**, University of Calgary ([PMC10826077](https://pmc.ncbi.nlm.nih.gov/articles/PMC10826077/)) | 3,686 RGB, 3,680 depth and 3,871 thermal images of diabetic foot ulcers, 3 angles per session | Not released: ethics approval did not cover release. Authors offer it "to selected research institutes upon request". |
| **FEMH burn set**, Far Eastern Memorial Hospital, Taiwan ([PMC11903701](https://pmc.ncbi.nlm.nih.gov/articles/PMC11903701/)) | 1,426 LiDAR RGB-D burn image sets | Request through the hospital ethics committee (irb@mail.femh.org.tw) |
| Zahia et al. 2020 ([PMC7294421](https://pmc.ncbi.nlm.nih.gov/articles/PMC7294421/)) | Structure Sensor scans of pressure injuries, with depth, area and volume measured in Blender | Not released. Figures are CC BY. |
| [Medetec Wound Database](https://www.medetec.co.uk/files/medetec-image-databases.html) | About 600 photos across 16 categories, including about 20 of undermining or tunnelling — the widest variety anywhere | Free for teaching slides and reports. Anything else needs written permission; high resolution on request. |
| University of Wisconsin–Milwaukee / AZH datasets ([segmentation](https://github.com/uwm-bigdata/wound-segmentation), [classification](https://github.com/uwm-bigdata/wound-classification-using-images-and-locations), [tissue](https://github.com/uwm-bigdata/DFUTissueSegNet)) | Foot-ulcer crops with masks; wound-type and body-location labels; 8-class tissue masks | No licence stated |
| [ComplexWoundDB](https://arxiv.org/abs/2209.12822) (UNESP, Brazil) | Home-care chronic wounds with tissue masks by 4 raters | No licence stated |
| [PIDIL](https://findanexpert.unimelb.edu.au/project/301920-pressure-injury-(pressure-ulcer-or-bed-sore)-digital-image-library-(pidil)) (University of Melbourne) | Consented, stage-labelled pressure-injury photos, by its description | No images or terms found; outreach lead |
| **BurnCare** (IIT Roorkee with AIIMS Rishikesh; medRxiv doi:10.64898/2025.12.24.25337638) *(4 Nov)* | 1,003 smartphone photos of burns from 36 consenting patients; skin and burn masks for 441, drawn with SAM2 from a few clicks | No licence stated; a registration form leads to a 2.9 GB download. **Burn masks on photos of consenting patients** (EBIS, section 4, also has burn masks, but on photos scraped from the web) — ask the authors about terms. |
| Diabetic-foot photos from patients of colour (Baseman et al., Georgia Tech and Emory, IEEE BHI 2025) *(4 Nov)* | 3,362 photos from 252 patients, more than 80 % Black, with ulcer segmentation in the paper | The abstract says the images are released, but no download was found. Ask the authors: the leprosy sets above are all from one Colombian programme. |
| Chang et al., *PLOS ONE* 2022 ([figshare 17206904](https://figshare.com/articles/dataset/healing-pressure-ulcer-0013_jpg/17206904), [17206940](https://figshare.com/articles/dataset/images_of_pressure_ulcer_2_/17206940)) *(4 Nov)* | Tissue masks and outlines for 20 Medetec pressure-ulcer photos | CC BY 4.0 covers the annotations only; the photos remain Medetec's (above) |
| Swift Medical and McGill rater study ([Borealis doi:10.5683/SP3/8C4FDV](https://doi.org/10.5683/SP3/8C4FDV)) *(4 Nov)* | Tissue labels by five clinicians for 58 chronic-wound photos | The labels are CC0, but the photos are not public; ask Swift Medical or McGill for them |

## 4. Avoid

| Source | Why |
|---|---|
| [DFU Grand Challenge](https://helward.mmu.ac.uk/STAFF/M.Yap/dataset.php) datasets (2020–2024) | The licence forbids commercial and clinical use, and its IP clauses would put anything built on it at risk. |
| [DermNet](https://dermnetnz.org/image-licence) | Non-commercial, and its terms forbid using the images for AI or measurement testing. |
| NPIAP photo store, International Pressure Ulcer Guideline photos, WOCN image library, Wounds Canada | Copyright; personal educational use or members only. |
| [JSPU DESIGN-R manual](https://www.jspu.org/english/publication/docs/DESIGN-R_manual_eng.pdf) | No reproduction without permission. Read it anyway: it defines how clinicians measure undermining area. |
| OpenStax nursing textbooks | CC BY-NC-SA. Use them to find the original photos they credit, some of which are CC BY or public domain. |
| Kaggle wound collections, EBIS burns, WoundcareVQA, SurgWound | Re-packaged or web-scraped images with no clear rights, whatever licence label they carry. |
| RKT-DFU-800, PIID, PISeg | Not released, no licence, or unclear provenance. |
| Post-operative wound infection photos in [ul8ziz/Wound-infection-detection-model](https://github.com/ul8ziz/Wound-infection-detection-model) *(4 Nov)* | No licence, no named source, ethics approval or consent, and original file names that look like patient record codes. |

## 5. Segmentation test set

`woundscan-engine/scripts/fetch_wound_segmentation_data.py --out DIR` downloads CO2Wounds v1 and
LUTSeg into DIR, which may not lie inside any git work tree, and checks every file against the
publisher's own hash. It writes each photo, byte for byte but named for its format (CO2Wounds v1
publishes JPEGs as .png), beside a 0/255 wound mask of the same size, plus LUTSeg's tissue
masks. `manifest.csv` gives each photo's licence and use group (`usable` for CO2Wounds v1,
`confirm-first` for LUTSeg), split, patient, wound share of the frame, what its mask covers,
provenance note and the first copy of any photo it repeats. `LICENSES.md` says what each set
allows, the credit to cite, and how the masks were changed (binarised; the published files are
kept under `raw/`).

`evaluate_segmentation.py --data DIR --pred PRED`, or `--engine` to run the engine's own model,
scores masks per dataset and by wound size: Dice, IoU, precision, recall, boundary F1 and area
error. Each photo is scored once per run, from the first selected set that lists it. The report,
with any predicted masks, goes to `DIR/reports/` unless `--report` names another place outside
a git work tree. With `--weights`, the run stops unless the engine's U-Net really loads, so a
fallback result is never filed under a model's name (handoff register
`engine-ml-quality-validation-G2`); the report's folder and `summary.json` name the weights
and their SHA-256, so two checkpoints both called `best.pt` are kept apart.

Measured on 4 November 2026:

| What | Photos | Result |
|---|---|---|
| Both sets | 305, of which 273 distinct | Wounds cover a median 3.9 % of the frame (10–90 %: 0.3–18.7 %); no mask is empty |
| The same photo outlined by two teams (CO2Wounds v1 and LUTSeg) | 32 | Dice median 0.80, lowest 0.21. CO2Wounds outlines are tighter: median area 0.74 × LUTSeg's |
| LUTSeg's five clinicians against one another | 46 | Dice median 0.86 (quartiles 0.78–0.92): about the best a model can be expected to reach |
| The engine's `BoundarySegmentationModel`, which falls back to its colour heuristic because no weights are in the repository (handoff register `engine-ml-quality-validation-G1`) | 273 | Dice median 0.067; 98 % of photos under 0.5. It marks reddish skin, the colour card and red objects |

Both sets come from one leprosy programme in Colombia, mostly lower-leg and foot ulcers: they do
not cover pressure injuries, surgical wounds or burns. Of the non-commercial sets (section 2),
WoundSeg adds pressure injuries, surgical and trauma wounds among its eight types, though its
masks include the peri-wound skin, and FUSeg adds foot ulcers, mostly diabetic. None of them has
burns. For burns, BurnCare has burn masks and the FEMH burn set has RGB-D scans (both section 3,
ask first); EBIS also has burn masks, but its photos were scraped from the web (section 4).

## For StrataMetric

- **Depth and volume:** keep validating on the phantoms. For real wounds, pursue WoundsDB and
  the Zivot set, and plan our own consented clinical capture. The published approach uses a
  structured-light scanner as the reference (Artec Leo in the MolecuLight study, Artec Eva in
  the burn study).
- **Segmentation:** test on CO2Wounds v1 and LUTSeg now (section 5). Only CO2Wounds v1 is
  cleared for commercial use: write to LUTSeg's authors before it is used in the product or its
  training data.
- **Area and perimeter in millimetres:** no public set gives a usable scale yet. Ask CO2Wounds'
  authors for their calibration card's dimensions, and keep using the phantoms.
- **Undermining:** visual references in Broder 2016, Tanaka 2025 and Medetec (with
  permission); the JSPU DESIGN-R manual for how clinicians measure it.
