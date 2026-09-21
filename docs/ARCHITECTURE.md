# System Architecture

```text
                    RGB CAMERA
                        |
                        v
              +-------------------+
              | YOLO Weed Detector |
              +---------+---------+
                        |
                 boxes + classes
                        |
                        v
              +-------------------+
              | Target Localizer  |
              | bbox/stem point   |
              +---------+---------+
                        |
                        v
              +-------------------+
              | Temporal Tracker  |
              +---------+---------+
                        |
                        v
              +-------------------+
              | Safety State Gate |
              +---------+---------+
                        |
                        v
              +-------------------+
              | Pixel -> Pan/Tilt |
              | Calibration       |
              +---------+---------+
                        |
                        v
                 ESP32 / MCU
                   /                         /                      PAN SERVO    TILT SERVO
                        |
                        v
                 SAFE TREATMENT
                    INTERFACE
                        |
                        v
                   RE-IMAGE
                        |
                        v
                     LOG
```

## Design principles

- Detection and actuation are separated.
- Treatment is disabled by default.
- A target must be stable before treatment is permitted.
- Crop proximity is checked before treatment.
- Hardware interlocks are expected to be independent of the ML model.
- A safe indicator is used for early testing.
