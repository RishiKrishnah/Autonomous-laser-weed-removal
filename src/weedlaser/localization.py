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
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def bbox_center(det: Detection) -> tuple[float, float]:
    return det.center


def choose_target(
    detections: Iterable[Detection],
    frame_center: tuple[float, float],
) -> Detection | None:
    """Choose the highest-confidence weed nearest the image center."""
    candidates = list(detections)
    if not candidates:
        return None

    fx, fy = frame_center
    diag = max(1.0, (fx * fx + fy * fy) ** 0.5)

    def score(d: Detection) -> float:
        x, y = d.center
        dist = ((x - fx) ** 2 + (y - fy) ** 2) ** 0.5 / diag
        return 0.75 * d.confidence + 0.25 * (1.0 - min(dist, 1.0))

    return max(candidates, key=score)


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
    # Image y increases downward; invert sign for conventional tilt.
    tilt = calibration.tilt_center_deg - dy * calibration.tilt_deg_per_px

    pan = float(np.clip(pan, *pan_limits))
    tilt = float(np.clip(tilt, *tilt_limits))
    return pan, tilt
