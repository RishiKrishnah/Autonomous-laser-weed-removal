# Autonomous Vision-Guided Weed Targeting and Safe Treatment Prototype

A computer-vision-based autonomous precision-weeding prototype that detects weed species, identifies a target point, tracks the target temporally, converts image coordinates into pan/tilt commands, applies software safety checks, and records system events.

The system is designed around the following pipeline:

```text
RGB Camera
    │
    ▼
YOLO Weed Detection
    │
    ▼
Target Selection
    │
    ▼
Temporal Target Tracking
    │
    ▼
Crop Exclusion Check
    │
    ▼
Pixel → Pan/Tilt Localization
    │
    ▼
Safety Gate
    │
    ├── BLOCKED ──────────────┐
    │                         │
    ▼                         │
Safe Hardware Interface       │
    │                         │
    ▼                         │
Temporal Visual Verification  │
    │                         │
    ▼                         │
Event Logging ◄───────────────┘
```

> **Safety note:** The submitted reference implementation does **not autonomously activate a hazardous laser**. Treatment output is disabled by default. The hardware layer supports safe simulation/indicator control, while the software demonstrates detection, localization, tracking, safety decisions, pan/tilt control, verification logic, and logging.

---

# 1. Project Overview

Precision weed removal requires a system capable of distinguishing weeds from crops and accurately directing a treatment mechanism toward the selected weed.

This project implements the computer-vision and robotic targeting pipeline required for such a system.

The main objectives are:

1. Detect weeds from an RGB camera.
2. Classify the detected weed species.
3. Select an appropriate target.
4. Track the target over multiple frames.
5. Reject unstable or rapidly moving targets.
6. Prevent targeting inside configured crop-exclusion regions.
7. Convert image coordinates into pan/tilt servo coordinates.
8. Apply a multi-condition software safety gate.
9. Interface with an ESP32-based pan/tilt controller.
10. Maintain safe default hardware states.
11. Perform temporal visual verification.
12. Log targeting and safety events.
13. Provide reproducible dataset preparation, training, and evaluation scripts.
14. Provide automated unit tests for the core robotics and safety logic.

---

# 2. Key Features

## Computer Vision

- YOLO-based weed detection
- Multi-class weed classification
- Configurable confidence threshold
- Configurable IoU threshold
- 640 × 640 inference configuration
- Bounding-box based target selection
- Camera-frame target prioritization

## Temporal Tracking

- Multi-frame target stabilization
- Configurable number of stable frames
- Maximum allowable target movement
- Target timeout handling
- Automatic tracker reset when no target is detected

## Target Localization

The current implementation uses the center of the detected bounding box as the target point:

```text
YOLO Bounding Box
        │
        ▼
Bounding Box Center
        │
        ▼
Camera Calibration
        │
        ▼
Pan / Tilt Coordinates
```

The architecture can later be extended with a dedicated stem or treatment-point estimator.

## Crop Safety

The system supports configurable polygonal crop-exclusion zones.

A target is rejected when its target point falls inside a configured crop zone.

```text
+--------------------------------------+
|                                      |
|        WEED TARGET                   |
|           ●                          |
|                                      |
|                    ┌──────────────┐  |
|                    │ CROP ZONE    │  |
|                    │              │  |
|                    │   BLOCKED    │  |
|                    │              │  |
|                    └──────────────┘  |
|                                      |
+--------------------------------------+
```

## Safety Gate

The safety system considers:

- Detection confidence
- Target stability
- Crop proximity
- Target timeout
- Emergency-stop state
- Interlock state
- Treatment-enable state
- Stationary-target requirement

The system fails safely whenever a required condition is not satisfied.

## Hardware Interface

The hardware layer supports:

- Simulation mode
- Serial communication
- Pan control
- Tilt control
- Safe indicator output
- Emergency-stop handling
- Servo limits

## ESP32

The ESP32 firmware provides a safe controller for:

- Pan servo
- Tilt servo
- Emergency stop
- Enclosure/interlock input
- Safe indicator output
- Serial status reporting

## Logging

System events are recorded with information such as:

- Weed class
- Weed class name
- Detection confidence
- Target coordinates
- Pan angle
- Tilt angle
- Crop exclusion status
- Safety state
- Verification state
- Timestamp

---

# 3. Dataset

This project is based on the **MH-Weed16** dataset.

The original MH-Weed16 dataset contains 16 weed classes.

However, the dataset prepared and used by this repository is a **15-class subset**.

> **Important:** The current trained dataset does not contain class 15, Punarnava. Therefore, this implementation must be described as a **15-class MH-Weed16 subset**, not as a 16-class trained model.

## 3.1 Current Dataset Classes

| ID | Weed Class |
|---:|---|
| 0 | Kena |
| 1 | Lavhala |
| 2 | Lambs Quarter Plant |
| 3 | Little Mallow |
| 4 | Moti dudhi |
| 5 | Obscure morning glory |
| 6 | Asian pigeonwings |
| 7 | Bilayat |
| 8 | Choti dudhi |
| 9 | Digitaria SP |
| 10 | Gajar gavat |
| 11 | Graceful sandmat |
| 12 | Sicklepod |
| 13 | Harali |
| 14 | Dwarf cassia |

Class 15:

```text
Punarnava
```

is not included in the current prepared dataset.

---

# 4. Prepared Dataset

The current prepared YOLO dataset contains:

| Split | Images | Labels |
|---|---:|---:|
| Training | 4,659 | 4,659 |
| Validation | 998 | 998 |
| Test | 999 | 999 |
| **Total** | **6,656** | **6,656** |

The dataset is divided into:

```text
data/yolo/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
│
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
│
└── dataset.yaml
```

The dataset split is generated reproducibly using a fixed random seed.

Default:

```text
seed = 42
```

The split used by the preparation script is approximately:

```text
70% training
15% validation
15% testing
```

The dataset itself should not be committed to GitHub.

---

# 5. Repository Structure

```text
autonomous-laser-weed-removal/
│
├── configs/
│   ├── classes.txt
│   ├── config.yaml
│   └── mh_weed16.yaml
│
├── data/
│   └── README.md
│
├── docs/
│   ├── ARCHITECTURE.md
│   └── EXPERIMENTS.md
│
├── firmware/
│   └── esp32/
│       └── weed_target_controller.ino
│
├── models/
│   └── README.md
│
├── scripts/
│   ├── prepare_dataset.py
│   ├── train_detector.py
│   ├── evaluate_detector.py
│   └── export_model.py
│
├── src/
│   └── weedlaser/
│       ├── __init__.py
│       ├── config.py
│       ├── crop_exclusion.py
│       ├── detector.py
│       ├── hardware.py
│       ├── localization.py
│       ├── logger.py
│       ├── main.py
│       ├── safety.py
│       ├── tracker.py
│       └── verification.py
│
├── tests/
│   └── test_core.py
│
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── .gitignore
├── LICENSE
└── README.md
```

---

# 6. System Architecture

The system is divided into independent modules.

```text
                    ┌──────────────────┐
                    │    RGB Camera    │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  YOLO Detector   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Target Selection │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Temporal Tracker │
                    └────────┬─────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
       ┌──────────────────┐    ┌──────────────────┐
       │ Crop Exclusion   │    │ Localization     │
       └────────┬─────────┘    └────────┬─────────┘
                │                       │
                └───────────┬───────────┘
                            ▼
                   ┌─────────────────┐
                   │   Safety Gate   │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Hardware Layer  │
                   └────────┬────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │ ESP32 / Servo  │
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ Verification   │
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ Event Logger   │
                    └────────────────┘
```

---

# 7. Software Requirements

Recommended environment:

- Python 3.10 or newer
- OpenCV
- Ultralytics YOLO
- NumPy
- PyYAML
- PySerial
- Pillow
- Pandas
- Matplotlib
- Scikit-learn
- tqdm

Development tools:

- pytest
- Ruff

The Python version requirement is defined in `pyproject.toml`.

---

# 8. Installation

## 8.1 Windows

Open PowerShell:

```powershell
git clone <YOUR-REPOSITORY-URL>

cd autonomous-laser-weed-removal

python -m venv .venv

.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip

pip install -r requirements.txt
```

For development dependencies:

```powershell
pip install -r requirements-dev.txt
```

---

## 8.2 Linux

```bash
git clone <YOUR-REPOSITORY-URL>

cd autonomous-laser-weed-removal

python3 -m venv .venv

source .venv/bin/activate

python -m pip install --upgrade pip

pip install -r requirements.txt
```

For development dependencies:

```bash
pip install -r requirements-dev.txt
```

---

# 9. PyTorch Installation

Ultralytics requires PyTorch.

If the automatic dependency installation does not install a suitable PyTorch build for the available GPU, install the appropriate PyTorch version for the system first using the official PyTorch installation instructions.

After installing PyTorch, install the project requirements:

```bash
pip install -r requirements.txt
```

Verify the installation:

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())"
```

A CUDA-enabled installation should report:

```text
True
```

for `torch.cuda.is_available()` when a compatible NVIDIA GPU and CUDA-enabled PyTorch installation are available.

---

# 10. Dataset Preparation

The repository contains a reproducible dataset preparation script.

The current implementation expects the MH-Weed16 dataset root and specifically looks for the required image and YOLO annotation directories inside the dataset.

Run:

```powershell
python scripts/prepare_dataset.py `
    --dataset-root "C:\path\to\MH-Weed16" `
    --output data/yolo `
    --seed 42
```

On Linux:

```bash
python scripts/prepare_dataset.py \
    --dataset-root /path/to/MH-Weed16 \
    --output data/yolo \
    --seed 42
```

The script:

1. Locates the image directory.
2. Locates the YOLO annotation directory.
3. Validates annotation format.
4. Validates class IDs.
5. Validates normalized coordinates.
6. Matches images with annotation files.
7. Randomizes the dataset using a fixed seed.
8. Creates train/validation/test splits.
9. Copies images and labels into YOLO format.
10. Generates `dataset.yaml`.

The resulting dataset should contain:

```text
data/yolo/
├── images/
│   ├── train/
│   ├── val/
│   └── test/
│
├── labels/
│   ├── train/
│   ├── val/
│   └── test/
│
└── dataset.yaml
```

---

# 11. Dataset Configuration

The generated `dataset.yaml` contains:

```yaml
nc: 15
```

and the 15 class names.

The dataset must remain consistent with:

```text
configs/classes.txt
```

Do not add Punarnava to `classes.txt` unless the dataset is regenerated with actual annotations for that class.

---

# 12. Model Training

The project uses Ultralytics YOLO for object detection.

A baseline training run can be performed with:

```powershell
python scripts/train_detector.py `
    --data data/yolo/dataset.yaml `
    --model yolov8n.pt `
    --epochs 100 `
    --imgsz 640 `
    --batch 16 `
    --device 0 `
    --project runs `
    --name weed_detector_final
```

The resulting weights should be available under:

```text
runs/
└── weed_detector_final/
    └── weights/
        ├── best.pt
        └── last.pt
```

The exact output location depends on the Ultralytics run configuration.

---

# 13. CPU Training

For systems without a CUDA-capable GPU:

```powershell
python scripts/train_detector.py `
    --data data/yolo/dataset.yaml `
    --model yolov8n.pt `
    --epochs 20 `
    --imgsz 640 `
    --batch 4 `
    --device cpu `
    --project runs `
    --name weed_detector_cpu
```

CPU training will generally be slower than GPU training.

---

# 14. Model Evaluation

Evaluation must be performed on the held-out test split.

Example:

```powershell
python scripts/evaluate_detector.py `
    --weights runs/weed_detector_final/weights/best.pt `
    --data data/yolo/dataset.yaml `
    --device 0 `
    --imgsz 640
```

The evaluation script reports:

```text
Precision
Recall
mAP@0.50
mAP@0.50:0.95
```

The evaluation results should be recorded in the project experiment documentation.

> Do not hard-code or claim model accuracy in this README unless the final trained model has actually been evaluated and the reported values correspond to that exact model and test set.

---

# 15. Single-Image Prediction

A single test image can be evaluated using Ultralytics directly.

Example:

```powershell
python -c "from ultralytics import YOLO; m=YOLO('runs/weed_detector_final/weights/best.pt'); r=m.predict(source='data/yolo/images/test/YOUR_IMAGE.jpeg', conf=0.55, save=True); print(r[0].boxes)"
```

The prediction output contains:

- Bounding boxes
- Class IDs
- Class names
- Confidence scores

The generated annotated image can then be inspected visually.

---

# 16. Live Camera Inference

After training the model, run:

```powershell
python -m src.weedlaser.main `
    --weights runs/weed_detector_final/weights/best.pt `
    --source 0 `
    --config configs/config.yaml
```

The `--source` argument can be:

```text
0
```

for the default webcam, or a video path such as:

```text
sample_video.mp4
```

Example:

```powershell
python -m src.weedlaser.main `
    --weights runs/weed_detector_final/weights/best.pt `
    --source "test_video.mp4" `
    --config configs/config.yaml
```

Press:

```text
q
```

to exit the display window.

---

# 17. Runtime Configuration

The main configuration is:

```text
configs/config.yaml
```

Important parameters include:

```yaml
camera:
  source: 0
  width: 640
  height: 480
  fps: 30
```

Model configuration:

```yaml
model:
  confidence: 0.55
  iou: 0.45
  imgsz: 640
  target_mode: bbox_center
```

Tracking:

```yaml
tracking:
  enabled: true
  required_stable_frames: 5
  max_center_jump_px: 60
  target_timeout_s: 1.0
```

Safety:

```yaml
safety:
  require_stable_target: true
  minimum_confidence: 0.55
  require_stationary: true
  emergency_stop: true
  interlock_closed: false
  treatment_enabled: false
```

Hardware:

```yaml
hardware:
  mode: simulation
```

These defaults intentionally keep the system in a safe state.

---

# 18. Target Selection

The detector may identify multiple weeds in a frame.

The localization module converts each detection into a target representation.

The current target point is:

```text
x_center = (x1 + x2) / 2
y_center = (y1 + y2) / 2
```

The system then selects a target based on the configured target-selection logic.

The current implementation uses the bounding-box center as a conservative target-point approximation.

---

# 19. Temporal Target Tracking

A single detection is not considered sufficient for stable autonomous targeting.

The tracker requires the target to remain stable over multiple frames.

Current configuration:

```yaml
required_stable_frames: 5
max_center_jump_px: 60
target_timeout_s: 1.0
```

Conceptually:

```text
Frame 1 ── Detection
Frame 2 ── Detection
Frame 3 ── Detection
Frame 4 ── Detection
Frame 5 ── Detection
             │
             ▼
        Stable Target
```

If the target moves beyond the permitted threshold, the target is considered unstable.

If the target disappears for longer than the configured timeout, the tracker resets.

---

# 20. Crop Exclusion

Crop exclusion is implemented in:

```text
src/weedlaser/crop_exclusion.py
```

The system supports polygonal exclusion zones.

Example configuration:

```yaml
crop_exclusion:
  enabled: true
  zones:
    - name: crop_zone_1
      points:
        - [0, 0]
        - [200, 0]
        - [200, 150]
        - [0, 150]
```

The points represent image coordinates.

If the target point lies inside a crop-exclusion polygon:

```text
Target = BLOCKED
```

This prevents the target from being treated as an eligible target.

---

# 21. Pixel-to-Servo Localization

The localization module converts image coordinates into pan/tilt coordinates.

Conceptually:

```text
Image X/Y
   │
   ▼
Camera Calibration
   │
   ▼
Pan / Tilt Angles
   │
   ▼
Servo Limits
```

The configured limits are:

```yaml
pan_min_deg: 20
pan_max_deg: 160

tilt_min_deg: 20
tilt_max_deg: 120
```

The output is clipped to the configured servo limits.

This prevents the software from commanding angles outside the permitted mechanical range.

---

# 22. Camera Calibration

The configuration contains calibration parameters for:

```text
Camera resolution
Pan center
Tilt center
Pixel-to-angle coefficients
```

The default calibration is an initial empirical configuration.

For a physical prototype, the calibration values should be experimentally measured using known image points and corresponding pan/tilt positions.

A proper calibration experiment should record:

```text
Image coordinate
Expected pan angle
Expected tilt angle
Measured pan angle
Measured tilt angle
Localization error
```

The final calibration values should be documented in `docs/EXPERIMENTS.md`.

---

# 23. Safety State Machine

The safety module is implemented in:

```text
src/weedlaser/safety.py
```

The conceptual system flow is:

```text
IDLE
  │
  ▼
DETECTION
  │
  ▼
TARGET TRACKING
  │
  ▼
STABLE TARGET
  │
  ▼
CROP SAFETY CHECK
  │
  ▼
LOCALIZATION
  │
  ▼
SAFETY GATE
  │
  ├───────────────┐
  │               │
  ▼               ▼
READY           BLOCKED
  │
  ▼
SAFE HARDWARE INTERFACE
  │
  ▼
VERIFICATION
  │
  ▼
LOGGING
```

The safety gate checks:

### Detection confidence

The detection must meet the configured minimum confidence.

```yaml
minimum_confidence: 0.55
```

### Target stability

The target must remain stable for the configured number of frames.

### Crop exclusion

A target inside a crop zone is rejected.

### Emergency stop

If the emergency-stop state is active, the safety gate blocks operation.

### Interlock

The system requires the configured interlock condition.

### Treatment enable

The system requires explicit treatment authorization.

### Stationary target

The current configuration requires the target to be stationary before any treatment authorization state is considered.

---

# 24. Safe Default State

The reference configuration intentionally contains:

```yaml
emergency_stop: true
interlock_closed: false
treatment_enabled: false
```

This means the default runtime state is:

```text
BLOCKED
```

This is intentional.

The project prioritizes fail-safe behavior over autonomous treatment activation.

A `READY` state can still be tested through the software unit tests by supplying safe simulated inputs to the safety gate.

---

# 25. Hardware Abstraction

The hardware interface is implemented in:

```text
src/weedlaser/hardware.py
```

The abstraction allows the same application pipeline to operate with:

```text
Simulation Controller
```

or

```text
Serial Controller
```

This separates computer-vision logic from physical hardware.

The application can therefore be developed and tested without connecting an actuator.

---

# 26. ESP32 Controller

Firmware:

```text
firmware/esp32/weed_target_controller.ino
```

The ESP32 controls the pan/tilt mechanism and safe indicator interface.

The current firmware supports the following serial commands.

## Pan

```text
PAN <degrees>
```

Example:

```text
PAN 90
```

## Tilt

```text
TILT <degrees>
```

Example:

```text
TILT 70
```

## Safe Indicator

```text
INDICATOR ON
```

and:

```text
INDICATOR OFF
```

## Emergency Stop

```text
E_STOP
```

## Reset

```text
RESET
```

## Status

```text
STATUS
```

The firmware maintains servo limits and checks the emergency-stop/interlock state.

The firmware does not provide an autonomous hazardous laser-firing command.

---

# 27. Serial Configuration

The configuration contains:

```yaml
hardware:
  mode: simulation
  serial_port: COM3
  baudrate: 115200
```

For a safe ESP32 hardware demonstration, change the serial port to the correct device.

Example:

```yaml
hardware:
  mode: serial
  serial_port: COM5
  baudrate: 115200
```

The exact COM port depends on the connected ESP32.

On Linux the device may appear as:

```text
/dev/ttyUSB0
```

or:

```text
/dev/ttyACM0
```

---

# 28. Verification

The verification module is implemented in:

```text
src/weedlaser/verification.py
```

The current implementation performs **temporal visual verification** using changes in detection confidence across frames.

It should therefore be interpreted as:

```text
Visual confidence-based verification
```

and **not** as proof that a physical weed has been destroyed.

The current architecture does not claim physical treatment effectiveness.

A future validated implementation could replace or extend this module with an experimentally validated post-treatment visual assessment model.

---

# 29. Event Logging

The logging system is implemented in:

```text
src/weedlaser/logger.py
```

Events contain information such as:

```text
Timestamp
Class ID
Class name
Confidence
Target X
Target Y
Pan
Tilt
Crop exclusion state
Safety state
Verification state
```

The logging directory is configured through:

```yaml
logging:
  directory: logs
```

The resulting logs can be used for:

- Debugging
- System evaluation
- Safety analysis
- Targeting accuracy analysis
- Experiment reporting
- Reproducibility

---

# 30. Automated Testing

Run the complete test suite with:

```powershell
pytest -q
```

The tests cover core functionality including:

- Detection representation
- Target selection
- Tracker stability
- Tracker movement rejection
- Tracker timeout
- Servo mapping
- Servo clipping
- Crop exclusion
- Safety blocking
- Safety-ready conditions
- Verification behavior

A successful run should report all tests passing.

---

# 31. Code Quality

Ruff is configured in `pyproject.toml`.

Run:

```powershell
ruff check src scripts tests
```

The project targets:

```text
Python >= 3.10
```

with a configured line length of:

```text
100 characters
```

---

# 32. Recommended Validation Procedure

Before the final project demonstration, perform validation in the following order.

## Step 1 — Unit Tests

```powershell
pytest -q
```

Expected:

```text
All tests pass
```

## Step 2 — Code Quality

```powershell
ruff check src scripts tests
```

Expected:

```text
No linting errors
```

## Step 3 — Dataset Validation

Verify:

```text
4659 training images
998 validation images
999 test images
15 classes
```

## Step 4 — Model Evaluation

Run:

```powershell
python scripts/evaluate_detector.py `
    --weights runs/weed_detector_final/weights/best.pt `
    --data data/yolo/dataset.yaml `
    --device 0 `
    --imgsz 640
```

Record:

```text
Precision
Recall
mAP@0.50
mAP@0.50:0.95
```

## Step 5 — Single Image Prediction

Test several images from:

```text
data/yolo/images/test/
```

## Step 6 — Video Test

Run the detector on a recorded video.

## Step 7 — Camera Test

Run:

```powershell
python -m src.weedlaser.main `
    --weights runs/weed_detector_final/weights/best.pt `
    --source 0 `
    --config configs/config.yaml
```

## Step 8 — Hardware Simulation

Verify that pan/tilt commands are generated correctly without connecting a hazardous actuator.

## Step 9 — ESP32 Safe Demonstration

Connect only approved low-risk hardware such as:

- Servo motors
- Safe LED/indicator
- E-stop
- Interlock input

## Step 10 — Logging

Verify that runtime events are written to the configured logging directory.

---

# 33. Demonstration Scenarios

## Demonstration 1 — Weed Detection

```text
Camera
  ↓
YOLO
  ↓
Bounding Box
  ↓
Class Name + Confidence
```

Demonstrate:

- Weed detection
- Class identification
- Confidence score

---

## Demonstration 2 — Target Tracking

```text
Detection
    ↓
Frame-to-frame tracking
    ↓
Stable target
```

Demonstrate:

- Stable target acquisition
- Movement rejection
- Target timeout

---

## Demonstration 3 — Target Localization

```text
Bounding Box
     ↓
Center Point
     ↓
Pixel Coordinates
     ↓
Pan/Tilt Angles
```

Demonstrate:

- Target point calculation
- Servo angle calculation
- Servo range clipping

---

## Demonstration 4 — Crop Safety

Configure a crop polygon and demonstrate:

```text
Target outside crop zone
        ↓
Potentially eligible
```

versus:

```text
Target inside crop zone
        ↓
BLOCKED
```

---

## Demonstration 5 — Safety Gate

Demonstrate that the system blocks authorization when:

- Confidence is too low
- Target is unstable
- Target is inside a crop zone
- E-stop is active
- Interlock is open
- Treatment is disabled

---

## Demonstration 6 — End-to-End Safe Pipeline

```text
Camera
  ↓
YOLO Detection
  ↓
Target Selection
  ↓
Tracking
  ↓
Crop Check
  ↓
Localization
  ↓
Safety Gate
  ↓
Pan/Tilt Simulation
  ↓
Temporal Verification
  ↓
Logging
```

This is the recommended final software demonstration.

---

# 34. Research Experiments

The system can be evaluated using controlled experiments.

## Experiment 1 — Detection Performance

Measure:

```text
Precision
Recall
mAP@0.50
mAP@0.50:0.95
```

---

## Experiment 2 — Model Comparison

Compare:

```text
YOLOv8n
YOLOv8s
```

under the same dataset split and evaluation protocol.

---

## Experiment 3 — Targeting Strategy

Compare:

```text
Bounding-box center
```

against a future:

```text
Stem/target-point estimator
```

---

## Experiment 4 — Target Stability

Evaluate:

```text
Static target
Moving target
Partially occluded target
```

---

## Experiment 5 — Lighting

Evaluate detection under:

```text
Bright illumination
Normal illumination
Low illumination
Uneven illumination
```

---

## Experiment 6 — Camera Distance

Evaluate different camera-to-ground distances.

Record:

```text
Detection confidence
Detection accuracy
Localization error
Targeting success
```

---

## Experiment 7 — Weed Density

Evaluate:

```text
Single weed
Low-density weeds
Medium-density weeds
High-density weeds
```

---

# 35. Recommended System Metrics

The following metrics can be reported in the final project evaluation.

## Detection

```text
Precision
Recall
mAP@0.50
mAP@0.50:0.95
```

## Runtime

```text
Inference latency
Frames per second
Target acquisition time
```

## Targeting

```text
Pixel localization error
Pan error
Tilt error
Physical targeting error
```

## Safety

```text
False authorization rate
Crop false-positive rate
Target rejection rate
E-stop response
Interlock rejection rate
```

## System

```text
Successful target rate
End-to-end latency
System uptime
Logging reliability
```

---

# 36. Calibration Experiment

Before reporting physical targeting accuracy, calibrate the camera-to-servo relationship.

A recommended calibration procedure is:

```text
1. Place a known visual target.
2. Detect the target.
3. Record its image coordinates.
4. Determine the correct pan angle.
5. Determine the correct tilt angle.
6. Repeat for multiple image positions.
7. Fit calibration coefficients.
8. Validate on previously unseen target positions.
```

Record the results in:

```text
docs/EXPERIMENTS.md
```

Do not report simulated localization values as physical targeting accuracy.

---

# 37. Model Export

The repository includes:

```text
scripts/export_model.py
```

Example ONNX export:

```powershell
python scripts/export_model.py `
    --weights runs/weed_detector_final/weights/best.pt `
    --format onnx `
    --imgsz 640
```

Other supported export formats depend on the installed Ultralytics environment.

---

# 38. Reproducibility

For reproducible experiments, record:

```text
Dataset version
Dataset split
Random seed
Model architecture
Initial weights
Epochs
Image size
Batch size
Device
Confidence threshold
IoU threshold
Calibration values
Software versions
Evaluation results
```

The dataset preparation script uses:

```text
seed = 42
```

unless another seed is explicitly provided.

---

# 39. Limitations

The current implementation has several important limitations.

### 1. Fifteen-class subset

The current prepared dataset contains 15 classes rather than all 16 classes from MH-Weed16.

### 2. Bounding-box target point

The target point is currently estimated using the bounding-box center.

This does not guarantee that the center corresponds to the biologically optimal treatment point of the weed.

### 3. Calibration

The default calibration values are initial configuration values and should be replaced by experimentally measured calibration parameters for a physical prototype.

### 4. Crop exclusion

Crop protection depends on correctly calibrated crop-exclusion polygons.

### 5. Verification

The current verification module performs temporal visual confidence comparison. It does not constitute validated physical treatment-success detection.

### 6. Environmental robustness

Performance may change with:

- Lighting
- Camera height
- Camera angle
- Weed scale
- Occlusion
- Background complexity
- Motion blur
- Weed density

### 7. Hazardous treatment

The reference implementation does not autonomously activate a hazardous laser.

Any future treatment hardware would require a separately engineered and independently validated safety system.

---

# 40. Safety and Responsible Use

This project concerns a robotic system that could potentially be connected to an optical treatment actuator.

The repository therefore uses a conservative design.

The default configuration contains:

```yaml
emergency_stop: true
interlock_closed: false
treatment_enabled: false
```

The reference implementation uses safe simulation/indicator interfaces rather than autonomous hazardous laser activation.

For any future physical treatment integration, appropriate engineering controls must be established before operation, including:

- Beam containment/enclosure
- Hardware interlock
- Emergency stop
- Controlled test environment
- Appropriate protective equipment
- Supervision
- Independent hardware safety mechanisms
- Controlled access to the test area

The software safety gate should not be treated as the only safety mechanism.

> **Never test an exposed high-power optical source on an open bench or in an occupied environment.**

---

# 41. Project Development Workflow

Recommended development workflow:

```text
Dataset
   ↓
Dataset Validation
   ↓
YOLO Training
   ↓
Test Evaluation
   ↓
Single Image Testing
   ↓
Video Testing
   ↓
Live Camera Testing
   ↓
Simulation
   ↓
Safe Servo Demonstration
   ↓
Safety Validation
   ↓
Experiment Logging
   ↓
Final Evaluation
```

This separates computer-vision validation from physical hardware validation.

---

# 42. Troubleshooting

## Camera does not open

Check:

```text
--source 0
```

Try another camera index:

```powershell
--source 1
```

Also verify that another application is not using the camera.

---

## Model file not found

Check:

```text
runs/weed_detector_final/weights/best.pt
```

Use the actual path generated by the training run.

On Windows, prefer forward slashes or correctly escaped paths when passing paths through Python.

Example:

```text
runs/weed_detector_final/weights/best.pt
```

---

## CUDA is unavailable

Check:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

If it returns:

```text
False
```

verify the installed PyTorch build and NVIDIA driver.

---

## Dataset preparation fails

Check that the supplied MH-Weed16 root contains the expected directory structure.

The preparation script validates:

- Image directory
- Annotation directory
- Image/label matching
- YOLO annotation format
- Class IDs
- Normalized coordinates

---

## No detections

Check:

```text
Model weights
Confidence threshold
Dataset class mapping
Image quality
Camera resolution
Lighting
```

Try lowering the confidence threshold temporarily for debugging, but do not automatically use a lower threshold in the final safety configuration.

---

## Safety state remains BLOCKED

This is expected with the default configuration.

The default configuration contains:

```yaml
emergency_stop: true
interlock_closed: false
treatment_enabled: false
```

The purpose is to keep the reference system fail-safe.

The safety module can be tested independently using the unit tests.

---

# 43. Academic Evaluation

For the final project report, the implementation can be evaluated at four levels.

## Level 1 — Detection

```text
Can the system identify weeds?
```

## Level 2 — Targeting

```text
Can the system identify and localize a stable target?
```

## Level 3 — Safety

```text
Can the system correctly reject unsafe targets?
```

## Level 4 — Integrated System

```text
Can the complete pipeline operate from camera input
through targeting, safety evaluation, hardware simulation,
verification, and logging?
```

This separation makes it possible to evaluate the computer-vision, robotics, and safety components independently.

---

# 44. Expected Final Demonstration

The recommended final demonstration should show:

```text
1. Camera input
       ↓
2. YOLO weed detection
       ↓
3. Weed class identification
       ↓
4. Target selection
       ↓
5. Temporal stabilization
       ↓
6. Crop exclusion
       ↓
7. Pixel-to-pan/tilt conversion
       ↓
8. Safety state evaluation
       ↓
9. Servo/simulation command
       ↓
10. Temporal visual verification
       ↓
11. Event logging
```

The demonstration should emphasize that the system makes a **safety-gated targeting decision**, rather than claiming validated autonomous physical weed destruction.

---

# 45. Future Improvements

Potential extensions include:

1. Add the missing Punarnava class after obtaining and validating appropriate annotations.
2. Train a larger YOLO model such as YOLOv8s.
3. Add a dedicated weed stem/target-point model.
4. Improve camera calibration.
5. Add depth sensing.
6. Add 3D camera-to-ground localization.
7. Improve crop segmentation.
8. Add more robust multi-object tracking.
9. Add illumination normalization.
10. Add real-time performance benchmarking.
11. Add hardware-in-the-loop testing using only safe actuators.
12. Improve visual post-action verification.
13. Add experiment dashboards.
14. Add automated dataset-quality checks.
15. Add continuous integration for tests and linting.

---

# 46. Citation

The project uses the MH-Weed16 dataset as the primary weed-detection dataset.

When presenting or publishing results, cite the original MH-Weed16 dataset and its associated publication according to the citation information supplied by the dataset authors.

Do not represent the current repository as a full 16-class implementation unless the missing class has actually been added, annotated, trained, and evaluated.

---

# 47. License

This project is distributed under the license included in:

```text
LICENSE
```

The dataset remains subject to its own license and terms of use.

---

# 48. Quick Start

For a clean setup, the complete workflow is:

```powershell
# 1. Create environment
python -m venv .venv

# 2. Activate environment
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Prepare dataset
python scripts/prepare_dataset.py `
    --dataset-root "C:\path\to\MH-Weed16" `
    --output data/yolo `
    --seed 42

# 5. Train model
python scripts/train_detector.py `
    --data data/yolo/dataset.yaml `
    --model yolov8n.pt `
    --epochs 100 `
    --imgsz 640 `
    --batch 16 `
    --device 0 `
    --project runs `
    --name weed_detector_final

# 6. Evaluate model
python scripts/evaluate_detector.py `
    --weights runs/weed_detector_final/weights/best.pt `
    --data data/yolo/dataset.yaml `
    --device 0 `
    --imgsz 640

# 7. Run tests
pytest -q

# 8. Run linting
ruff check src scripts tests

# 9. Run live camera inference
python -m src.weedlaser.main `
    --weights runs/weed_detector_final/weights/best.pt `
    --source 0 `
    --config configs/config.yaml
```

---

# 49. Final Project Status

The current implementation provides a complete reference pipeline for:

```text
Weed Detection
      +
Target Selection
      +
Temporal Tracking
      +
Crop Exclusion
      +
Pixel-to-Servo Localization
      +
Safety Gating
      +
Safe Hardware Interface
      +
Temporal Visual Verification
      +
Event Logging
      +
Dataset Preparation
      +
Model Training
      +
Model Evaluation
      +
Automated Testing
```

The implementation is intentionally designed so that hazardous treatment activation is **not part of the default autonomous runtime**.

The strongest claim supported by the current implementation is therefore:

> **An autonomous vision-guided weed detection, targeting, tracking, safety-gating, pan/tilt-control, verification, and logging prototype using a 15-class subset of the MH-Weed16 dataset.**

This accurately represents the implemented system while keeping the software architecture extensible for future controlled research.