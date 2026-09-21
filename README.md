# Autonomous Laser-Based Weed Removal System

A vision-guided precision-weeding prototype based on the MH-Weed16 dataset.

> **Project scope:** RGB camera → weed detection → target localization → pan/tilt aiming → safety gate → treatment output → verification/logging.

The repository is designed so that the **laser output is disabled by default**. Development can be completed using a safe indicator/LED output before any controlled laser integration.

## 1. Project objective

Build a robotic precision-weeding module that:

1. detects weed instances from an RGB camera,
2. identifies the weed species,
3. estimates a target point,
4. converts image coordinates into pan/tilt commands,
5. checks temporal stability and crop-safety conditions,
6. activates a treatment output only when all safety conditions are satisfied,
7. re-images the target and records the result.

The project architecture follows the supplied project plan and literature review: detect → localize → aim → verify → treat → re-check.

## 2. Dataset

This project is configured for **MH-Weed16 Version 1**.

The published Version 1 dataset contains 18,395 individual weed images across 16 weed species and 7,577 crop-with-weed samples, including 6,656 weed samples with bounding-box annotations. The source paper states that the crop-with-weed images were captured from a top-down view and that annotations are available in Pascal VOC, TXT and JSON formats.

**The dataset is NOT included in this repository** because it is large. Download it from the official Mendeley/Kaggle source and place it outside Git history or under `data/raw/` locally.

Sources:
- Mendeley Data: https://data.mendeley.com/datasets/d3n3mgjjbv/1
- Paper: https://www.sciencedirect.com/science/article/pii/S2352340925004214
- Kaggle dataset: https://www.kaggle.com/datasets/sayalis069/mh-weed16

### MH-Weed16 classes

| ID | Common name | Scientific name |
|---:|---|---|
| 0 | Kena | Commelina benghalensis |
| 1 | Lavhala | Cyperus rotundus |
| 2 | Lambs Quarter Plant | Chenopodium album |
| 3 | Little Mallow | Malva parviflora |
| 4 | Moti dudhi | Euphorbia geniculata |
| 5 | Obscure morning glory | Ipomoea obscura |
| 6 | Asian pigeon wings | Clitoria ternatea |
| 7 | Bilayat | Argemone mexicana |
| 8 | Choti dudhi | Euphorbia hirta |
| 9 | Digitaria SP | Digitaria sanguinalis |
| 10 | Gajar gavat | Parthenium hysterophorus |
| 11 | Graceful sandmat | Euphorbia hypericifolia |
| 12 | Sicklepod | Senna obtusifolia |
| 13 | Harali | Cynodon dactylon |
| 14 | Dwarf cassia | Chamaecrista pumila |
| 15 | Punarnava | Boerhaavia diffusa |

## 3. Repository structure

```text
autonomous-laser-weed-removal/
├── configs/
│   ├── config.yaml
│   └── mh_weed16.yaml
├── data/
│   └── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── EXPERIMENTS.md
├── firmware/
│   └── esp32/
│       └── weed_target_controller.ino
├── models/
│   └── README.md
├── scripts/
│   ├── prepare_dataset.py
│   ├── train_detector.py
│   ├── evaluate_detector.py
│   └── export_model.py
├── src/
│   └── weedlaser/
│       ├── __init__.py
│       ├── config.py
│       ├── detector.py
│       ├── hardware.py
│       ├── localization.py
│       ├── safety.py
│       ├── targeting.py
│       ├── tracker.py
│       ├── logger.py
│       └── main.py
├── tests/
│   └── test_core.py
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .gitignore
└── LICENSE
```

## 4. Installation

### Windows PowerShell

```powershell
git clone <YOUR-GITHUB-REPO-URL>
cd autonomous-laser-weed-removal

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PyTorch installation fails, install the appropriate PyTorch build for your CPU/GPU from https://pytorch.org/ and then rerun the requirements installation.

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 5. Dataset preparation

Do not commit the dataset to GitHub.

Recommended local layout:

```text
raw/
└── MH-Weed16/
    ├── Crop with Weed/
    ├── Individual Weed Species/
    └── ...
```

The preparation script can discover images and common annotation formats.

Run:

```bash
python scripts/prepare_dataset.py \
  --source /path/to/MH-Weed16 \
  --output data/yolo \
  --classes configs/classes.txt
```

Then inspect:

```text
data/yolo/
├── images/train
├── images/val
├── images/test
├── labels/train
├── labels/val
├── labels/test
└── dataset.yaml
```

If the source release already provides a clean YOLO dataset, use that directly and skip conversion.

## 6. Train

Baseline:

```bash
python scripts/train_detector.py \
  --data data/yolo/dataset.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --imgsz 640 \
  --batch 16 \
  --device 0
```

For CPU:

```bash
python scripts/train_detector.py \
  --data data/yolo/dataset.yaml \
  --model yolov8n.pt \
  --epochs 20 \
  --imgsz 640 \
  --batch 4 \
  --device cpu
```

The first experiment should establish a reproducible baseline. Do not claim final accuracy until the model has been trained and evaluated on a held-out test set.

## 7. Evaluate

```bash
python scripts/evaluate_detector.py \
  --weights runs/weed_detector/weights/best.pt \
  --data data/yolo/dataset.yaml \
  --device 0
```

Record at least:

- precision
- recall
- mAP@0.50
- mAP@0.50:0.95
- inference latency/FPS
- per-class performance
- false detections on crops

## 8. Camera inference

After training:

```bash
python -m src.weedlaser.main \
  --weights runs/weed_detector/weights/best.pt \
  --source 0 \
  --config configs/config.yaml
```

Press `q` to quit.

The default runtime uses a **safe indicator output**, not a real laser.

## 9. Targeting

The targeting module supports two modes:

### BBox center

```text
YOLO box → center point → camera calibration → pan/tilt
```

### Stem/target point

The architecture leaves a clean extension point for a stem-localization model:

```text
YOLO box → target-point estimator → camera calibration → pan/tilt
```

The repository currently uses a conservative box-center fallback so the complete pipeline can be demonstrated without requiring a second trained model.

## 10. Safety state machine

The treatment output is allowed only if all required conditions are true:

```text
IDLE
  ↓
DETECTION
  ↓
STABLE_TARGET
  ↓
AIMING
  ↓
SAFETY_CHECK
  ↓
TREATMENT
  ↓
VERIFY
  ↓
LOG
```

The following conditions are enforced in software:

- confidence threshold
- temporal stability
- crop-proximity exclusion
- target age/timeout
- emergency-stop state
- enclosure/interlock state
- explicit treatment-enable flag
- optional stationary-fire requirement

The default configuration sets:

```yaml
hardware:
  treatment_enabled: false
```

Keep it disabled during software development.

## 11. ESP32 controller

The Arduino/ESP32 firmware accepts:

```text
PAN <degrees>
TILT <degrees>
STATUS
TREAT ON
TREAT OFF
E_STOP
RESET
```

The firmware is configured so that treatment output remains disabled after boot.

Use a safe indicator during development. The firmware's treatment pin should be connected to your approved safety-controlled actuator/indicator circuit, not directly to a hazardous source.

## 12. Recommended demonstration

### Demo A — Detection

Camera → YOLO → bounding boxes.

### Demo B — Targeting

Camera → YOLO → target point → pan/tilt → safe LED/indicator.

### Demo C — Safety

Show that treatment is blocked when:

- confidence is low,
- target moves,
- a crop is too close,
- E-stop is active,
- enclosure/interlock is open,
- treatment mode is disabled.

### Demo D — End-to-end

Detection → stable target → pan/tilt → safety gate → safe treatment simulation → re-image → log.

## 13. Research experiments

Use these comparisons:

1. YOLOv8n vs YOLOv8s.
2. BBox-center targeting vs estimated stem-point targeting.
3. Static target vs moving target.
4. Different illumination conditions.
5. Different camera-to-ground distances.
6. Different weed densities.
7. Detection-only success vs system-level targeting success.

Important system metrics:

```text
Detection precision/recall
mAP@0.50
mAP@0.50:0.95
Inference latency
Targeting error in cm
Successful target rate
Crop false-positive rate
Treatment success rate
Energy/time per target
```

## 14. Safety

This project involves a potentially hazardous optical actuator.

**Do not test an exposed high-power laser on an open bench or in an occupied area.**

Use an appropriate engineering control hierarchy: enclosure/beam containment, interlock, emergency stop, controlled test area, appropriate eye protection and supervision. The software in this repository intentionally defaults to a non-laser indicator mode.

## 15. Citation

If you use MH-Weed16, cite the dataset and associated paper.

Shinde, S., & Attar, V. (2025). *An Indian annotated weed dataset for computer vision tasks in precision farming*. Data in Brief, 61, 111691. https://doi.org/10.1016/j.dib.2025.111691

Dataset:
Shinde, S., & Attar, V. (2024). *MH-Weed16: An Indian Multiclass Annotated Weed Dataset for Computer Vision Tasks*. Mendeley Data, Version 1. https://doi.org/10.17632/d3n3mgjjbv.1

## 16. Important reproducibility note

This repository contains the project code and configuration, not the MH-Weed16 images. The dataset is large and has its own licensing terms. Download the exact dataset version used for your experiments and record the version, source URL and checksum in your final report.
