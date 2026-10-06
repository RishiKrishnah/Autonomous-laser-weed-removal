from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


class EventLogger:
    def __init__(
        self,
        directory: str = "logs",
    ):
        self.directory = Path(directory)

        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path = self.directory / "events.csv"

        if not self.path.exists():
            with self.path.open(
                "w",
                newline="",
                encoding="utf-8",
            ) as f:
                csv.writer(f).writerow(
                    [
                        "timestamp",
                        "class_id",
                        "class_name",
                        "confidence",
                        "x",
                        "y",
                        "pan_deg",
                        "tilt_deg",
                        "stable",
                        "crop_near_target",
                        "crop_zone",
                        "safety_state",
                        "verification_state",
                    ]
                )

    def log(
        self,
        *,
        class_id: int,
        class_name: str,
        confidence: float,
        x: float,
        y: float,
        pan: float,
        tilt: float,
        stable: bool,
        crop_near_target: bool,
        crop_zone: str | None,
        safety_state: str,
        verification_state: str = "NOT_RUN",
    ) -> None:

        with self.path.open(
            "a",
            newline="",
            encoding="utf-8",
        ) as f:
            csv.writer(f).writerow(
                [
                    datetime.now().isoformat(timespec="seconds"),
                    class_id,
                    class_name,
                    f"{confidence:.4f}",
                    f"{x:.2f}",
                    f"{y:.2f}",
                    f"{pan:.2f}",
                    f"{tilt:.2f}",
                    stable,
                    crop_near_target,
                    crop_zone or "",
                    safety_state,
                    verification_state,
                ]
            )
