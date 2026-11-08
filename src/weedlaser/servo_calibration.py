from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Polynomial degree grows with the number of samples so the fit never
# has fewer points than about 1.5x its coefficients. Cubic captures the
# perspective + camera/turret offset to ~0.2 deg on simulated rigs.
MIN_AFFINE_SAMPLES = 4
MIN_QUADRATIC_SAMPLES = 9
MIN_CUBIC_SAMPLES = 16


@dataclass
class CalibrationSample:
    x: float
    y: float
    pan: float
    tilt: float


def _features(
    u: np.ndarray,
    v: np.ndarray,
    degree: int,
) -> np.ndarray:
    columns = [u**i * v**j for i in range(degree + 1) for j in range(degree + 1 - i)]

    return np.stack(columns, axis=-1)


@dataclass
class ServoCalibration:
    """
    Pixel -> (pan, tilt) mapping fitted from laser-dot samples.

    Pixels are normalised by the frame size, so the fit still
    applies if the camera delivers a different resolution
    (same aspect ratio).
    """

    frame_width: int
    frame_height: int
    degree: int
    pan_coeffs: list[float]
    tilt_coeffs: list[float]
    rms_deg: float = 0.0
    samples: list[CalibrationSample] = field(default_factory=list)

    def predict(
        self,
        point: tuple[float, float],
        frame_size: tuple[int, int],
    ) -> tuple[float, float]:
        w, h = frame_size

        u = np.array([point[0] / w])
        v = np.array([point[1] / h])

        f = _features(u, v, self.degree)[0]

        return (
            float(f @ np.array(self.pan_coeffs)),
            float(f @ np.array(self.tilt_coeffs)),
        )

    def save(
        self,
        path: str | Path,
    ) -> None:
        data = {
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "degree": self.degree,
            "pan_coeffs": self.pan_coeffs,
            "tilt_coeffs": self.tilt_coeffs,
            "rms_deg": self.rms_deg,
            "samples": [s.__dict__ for s in self.samples],
        }

        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "ServoCalibration":
        data = json.loads(Path(path).read_text())

        return cls(
            frame_width=int(data["frame_width"]),
            frame_height=int(data["frame_height"]),
            degree=int(data["degree"]),
            pan_coeffs=[float(c) for c in data["pan_coeffs"]],
            tilt_coeffs=[float(c) for c in data["tilt_coeffs"]],
            rms_deg=float(data.get("rms_deg", 0.0)),
            samples=[CalibrationSample(**s) for s in data.get("samples", [])],
        )


def fit_calibration(
    samples: list[CalibrationSample],
    frame_size: tuple[int, int],
) -> ServoCalibration:
    if len(samples) < MIN_AFFINE_SAMPLES:
        raise ValueError(f"Need at least {MIN_AFFINE_SAMPLES} samples, have {len(samples)}.")

    w, h = frame_size

    if len(samples) >= MIN_CUBIC_SAMPLES:
        degree = 3
    elif len(samples) >= MIN_QUADRATIC_SAMPLES:
        degree = 2
    else:
        degree = 1

    u = np.array([s.x / w for s in samples])
    v = np.array([s.y / h for s in samples])

    a = _features(u, v, degree)

    pan = np.array([s.pan for s in samples])
    tilt = np.array([s.tilt for s in samples])

    pan_coeffs, *_ = np.linalg.lstsq(a, pan, rcond=None)
    tilt_coeffs, *_ = np.linalg.lstsq(a, tilt, rcond=None)

    residuals = np.concatenate([a @ pan_coeffs - pan, a @ tilt_coeffs - tilt])

    return ServoCalibration(
        frame_width=w,
        frame_height=h,
        degree=degree,
        pan_coeffs=pan_coeffs.tolist(),
        tilt_coeffs=tilt_coeffs.tolist(),
        rms_deg=float(np.sqrt(np.mean(residuals**2))),
        samples=list(samples),
    )
