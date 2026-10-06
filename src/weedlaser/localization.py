from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox

        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0,
        )

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.bbox

        return max(
            0.0,
            float(x2 - x1),
        ) * max(
            0.0,
            float(y2 - y1),
        )


def bbox_center(
    detection: Detection,
) -> tuple[float, float]:
    return detection.center


def choose_target(
    detections: Iterable[Detection],
    frame_center: tuple[float, float],
) -> Detection | None:
    """
    Select a weed target using confidence and distance
    from the image center.

    Confidence has higher priority than position.
    """

    candidates = list(detections)

    if not candidates:
        return None

    fx, fy = frame_center

    diagonal = max(
        1.0,
        (fx * fx + fy * fy) ** 0.5,
    )

    def score(
        detection: Detection,
    ) -> float:
        x, y = detection.center

        distance = ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5

        normalized_distance = min(
            distance / diagonal,
            1.0,
        )

        center_score = 1.0 - normalized_distance

        return 0.75 * detection.confidence + 0.25 * center_score

    return max(
        candidates,
        key=score,
    )


def point_to_servo(
    point: tuple[float, float],
    calibration,
    pan_limits: tuple[float, float],
    tilt_limits: tuple[float, float],
) -> tuple[float, float]:
    x, y = point

    dx = x - calibration.camera_width_px / 2.0

    dy = y - calibration.camera_height_px / 2.0

    pan = calibration.pan_center_deg + dx * calibration.pan_deg_per_px

    # Image y increases downwards.
    # Invert it for conventional tilt.
    tilt = calibration.tilt_center_deg - dy * calibration.tilt_deg_per_px

    pan = float(
        np.clip(
            pan,
            *pan_limits,
        )
    )

    tilt = float(
        np.clip(
            tilt,
            *tilt_limits,
        )
    )

    return pan, tilt
