from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid configuration file: {path}")

    return data


@dataclass
class Calibration:
    camera_width_px: int
    camera_height_px: int
    pan_center_deg: float
    tilt_center_deg: float
    pan_deg_per_px: float
    tilt_deg_per_px: float


@dataclass
class CropZone:
    name: str
    points: list[tuple[float, float]]


@dataclass
class VerificationConfig:
    enabled: bool
    verification_frames: int
    confidence_drop_threshold: float


@dataclass
class RuntimeConfig:
    confidence: float
    iou: float
    imgsz: int
    target_mode: str

    required_stable_frames: int
    max_center_jump_px: float
    target_timeout_s: float

    minimum_confidence: float
    require_stationary: bool

    treatment_enabled: bool
    hardware_mode: str

    serial_port: str
    baudrate: int

    pan_min_deg: float
    pan_max_deg: float
    tilt_min_deg: float
    tilt_max_deg: float

    interlock_closed: bool
    emergency_stop: bool

    crop_exclusion_enabled: bool
    crop_zones: list[CropZone]

    verification: VerificationConfig

    calibration: Calibration

    logging_directory: str


def load_runtime_config(path: str | Path) -> RuntimeConfig:
    c = load_yaml(path)

    cal = c["calibration"]
    tracking = c["tracking"]
    model = c["model"]
    safety = c["safety"]
    hardware = c["hardware"]
    crop = c.get("crop_exclusion", {})
    verification = c.get("verification", {})
    logging = c.get("logging", {})

    zones: list[CropZone] = []

    for zone in crop.get("zones", []):
        points = [(float(point[0]), float(point[1])) for point in zone.get("points", [])]

        if len(points) >= 3:
            zones.append(
                CropZone(
                    name=str(zone.get("name", "crop_zone")),
                    points=points,
                )
            )

    return RuntimeConfig(
        confidence=float(model["confidence"]),
        iou=float(model["iou"]),
        imgsz=int(model["imgsz"]),
        target_mode=str(model["target_mode"]),
        required_stable_frames=int(tracking["required_stable_frames"]),
        max_center_jump_px=float(tracking["max_center_jump_px"]),
        target_timeout_s=float(tracking["target_timeout_s"]),
        minimum_confidence=float(safety["minimum_confidence"]),
        require_stationary=bool(safety["require_stationary"]),
        treatment_enabled=bool(hardware.get("treatment_enabled", False)),
        hardware_mode=str(hardware["mode"]),
        serial_port=str(hardware["serial_port"]),
        baudrate=int(hardware["baudrate"]),
        pan_min_deg=float(hardware["pan_min_deg"]),
        pan_max_deg=float(hardware["pan_max_deg"]),
        tilt_min_deg=float(hardware["tilt_min_deg"]),
        tilt_max_deg=float(hardware["tilt_max_deg"]),
        interlock_closed=bool(safety.get("interlock_closed", False)),
        emergency_stop=bool(safety.get("emergency_stop", True)),
        crop_exclusion_enabled=bool(crop.get("enabled", True)),
        crop_zones=zones,
        verification=VerificationConfig(
            enabled=bool(verification.get("enabled", True)),
            verification_frames=int(verification.get("verification_frames", 5)),
            confidence_drop_threshold=float(
                verification.get(
                    "confidence_drop_threshold",
                    0.15,
                )
            ),
        ),
        calibration=Calibration(
            camera_width_px=int(cal["camera_width_px"]),
            camera_height_px=int(cal["camera_height_px"]),
            pan_center_deg=float(cal["pan_center_deg"]),
            tilt_center_deg=float(cal["tilt_center_deg"]),
            pan_deg_per_px=float(cal["pan_deg_per_px"]),
            tilt_deg_per_px=float(cal["tilt_deg_per_px"]),
        ),
        logging_directory=str(logging.get("directory", "logs")),
    )
