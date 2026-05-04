# ML Models

Three models, all trained from scratch on labeled wound datasets.

## Wound boundary segmentation

- **Architecture**: U-Net (4 encoder/decoder levels, 32→256 channels)
- **Input**: RGB photo, 1024×1024 crop centered on wound
- **Output**: binary mask of wound vs periwound + per-pixel confidence
- **Training data**: Medetec public corpus + AZH wound database +
  internal labeled captures
- **Loss**: weighted BCE + Dice
- **Metric**: mean IoU on validation
- **Failure modes**: low contrast wounds with similar tissue color
  inside/outside wound; eschar mistaken for periwound shadow
- **Fallback**: HSV color heuristic (red-saturation × edge inverse).
  Intended only for development; production uses real weights.

## Tissue classification

- **Architecture**: U-Net++ or DeepLabV3 with depth as 4th input channel
- **Classes**: granulation, slough, eschar, epithelial, bone/tendon, periwound
- **Output**: per-pixel softmax probabilities; argmax class map
- **Training data**: AZH + internal annotations from clinical staff
- **Loss**: cross-entropy weighted by class imbalance
- **Metric**: macro F1 on validation set
- **Failure modes**: mixed-tissue regions, photo white balance shifts
- **Fallback**: HSV color rules for each class

## Probe tip detection

- **Architecture**: YOLOv8-nano fine-tuned
- **Training data**: synthetic compositions of probes over wound photos +
  labeled clinical captures
- **Output**: bounding box + tip pixel position + confidence
- **Failure modes**: occluded probe tips, blue gloves vs blue probes
- **Fallback**: returns no detections (clinician falls back to manual tap)

## Versioning

Each model deployment includes:
- `name` and `version` strings
- `weights_sha256` content hash
- `ModelCard` describing training dataset, validation metrics, intended
  use, known failure modes

The `ModelRegistry` (`woundscan/ml/model_registry.py`) enforces that
the same `(name, version)` always points to the same weight hash.

## Model performance dashboard

The web admin dashboard exposes:
- Per-model rolling validation accuracy
- Drift detection (z-score of weekly mean vs baseline)
- Failure-mode tagging from clinician corrections
- Per-clinician model utilization stats

## Robust fiducial detector

Not a learned model but uses ML-style robustness:
- CLAHE for glare resilience
- Multi-scale ArUco detection
- Per-marker dedup keeping lowest reprojection error
