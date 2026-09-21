from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import hypot
import time


@dataclass
class TrackState:
    point: tuple[float, float]
    confidence: float
    frames: int
    last_seen: float


class StableTargetTracker:
    def __init__(self, required_frames: int = 3, max_jump_px: float = 60.0, timeout_s: float = 1.0):
        self.required_frames = required_frames
        self.max_jump_px = max_jump_px
        self.timeout_s = timeout_s
        self._history = deque(maxlen=required_frames)
        self.state: TrackState | None = None

    def update(self, point: tuple[float, float], confidence: float) -> TrackState:
        now = time.monotonic()

        if self.state and now - self.state.last_seen > self.timeout_s:
            self._history.clear()

        if self._history:
            last = self._history[-1]
            if hypot(point[0] - last[0], point[1] - last[1]) > self.max_jump_px:
                self._history.clear()

        self._history.append(point)
        avg_x = sum(p[0] for p in self._history) / len(self._history)
        avg_y = sum(p[1] for p in self._history) / len(self._history)

        self.state = TrackState(
            point=(avg_x, avg_y),
            confidence=confidence,
            frames=len(self._history),
            last_seen=now,
        )
        return self.state

    def is_stable(self) -> bool:
        return self.state is not None and self.state.frames >= self.required_frames

    def reset(self) -> None:
        self._history.clear()
        self.state = None
