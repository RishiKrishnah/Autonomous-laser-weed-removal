# System Architecture

```text
                         RGB CAMERA
                             |
                             v
                    +-------------------+
                    |   YOLO Detector   |
                    +---------+---------+
                              |
                         detections
                              |
                              v
                    +-------------------+
                    | Target Selector   |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Temporal Tracker  |
                    +---------+---------+
                              |
                         stable target
                              |
                              v
                    +-------------------+
                    | Crop Exclusion    |
                    | Safety Zones      |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Target Localizer  |
                    | BBox Center       |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Pixel -> Pan/Tilt |
                    | Calibration      |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Software Safety   |
                    | Gate              |
                    +---------+---------+
                              |
                    +---------+---------+
                    |                   |
                  BLOCKED             READY
                    |                   |
                    v                   v
                  SAFE OFF       SAFE INDICATOR
                                        |
                                        v
                                  RE-IMAGE
                                        |
                                        v
                                  VERIFICATION
                                        |
                                        v
                                      LOG