from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


class EventLogger:
    def __init__(self, directory: str = "logs"):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "events.csv"

        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "timestamp", "class_name", "confidence",
                    "x", "y", "pan_deg", "tilt_deg", "safety_state"
                ])

    def log(self, class_name, confidence, x, y, pan, tilt, safety_state):
        with self.path.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.now().isoformat(timespec="seconds"),
                class_name,
                f"{confidence:.4f}",
                f"{x:.2f}",
                f"{y:.2f}",
                f"{pan:.2f}",
                f"{tilt:.2f}",
                safety_state,
            ])
