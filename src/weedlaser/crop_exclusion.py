from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np


@dataclass
class CropZone:
    name: str
    points: list[tuple[float, float]]


class CropExclusion:
    """
    Image-space crop exclusion system.

    A target is considered unsafe if its target point lies inside
    a configured crop polygon.

    This is intentionally conservative.

    If crop exclusion is enabled but no zones have been calibrated,
    the system reports that crop protection is not configured.
    """

    def __init__(
        self,
        enabled: bool,
        zones: Iterable[CropZone],
    ):
        self.enabled = enabled
        self.zones = list(zones)

    @property
    def configured(self) -> bool:
        return bool(self.zones)

    def target_is_in_crop(
        self,
        point: tuple[float, float],
    ) -> tuple[bool, str | None]:
        if not self.enabled:
            return False, None

        if not self.zones:
            return False, None

        x, y = point

        for zone in self.zones:
            polygon = np.array(
                zone.points,
                dtype=np.float32,
            )

            inside = cv2.pointPolygonTest(
                polygon,
                (float(x), float(y)),
                False,
            )

            if inside >= 0:
                return True, zone.name

        return False, None

    def draw(
        self,
        frame,
    ):
        if not self.enabled:
            return frame

        for zone in self.zones:
            points = np.array(
                zone.points,
                dtype=np.int32,
            ).reshape((-1, 1, 2))

            cv2.polylines(
                frame,
                [points],
                True,
                (255, 0, 255),
                2,
            )

            if zone.points:
                x, y = zone.points[0]

                cv2.putText(
                    frame,
                    zone.name,
                    (int(x), int(y) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 0, 255),
                    2,
                )

        return frame
