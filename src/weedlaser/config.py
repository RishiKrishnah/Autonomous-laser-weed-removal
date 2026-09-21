from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class Calibration:
    camera_width_px: int
    camera_height_px: int
    pan_center_deg: float
    tilt_center_deg: float
    pan_deg_per_px: float
    tilt_deg_per_px: float


@dataclass
class RuntimeConfig:
    confidence: float
    iou: float
    imgsz: int
    target_mode: str
    required_stable_frames: int
    max_center_jump_px: float
    target_timeout_s: float
    crop_exclusion_px: float
    require_stationary: bool
    minimum_confidence: float
    treatment_enabled: bool
    hardware_mode: str
    serial_port: str
    baudrate: int
    pan_min_deg: float
    pan_max_deg: float
    tilt_min_deg: float
    tilt_max_deg: float
    calibration: Calibration


def load_runtime_config(path: str | Path) -> RuntimeConfig:
    c = load_yaml(path)
    cal = c["calibration"]
    return RuntimeConfig(
        confidence=c["model"]["confidence"],
        iou=c["model"]["iou"],
        imgsz=c["model"]["imgsz"],
        target_mode=c["model"]["target_mode"],
        required_stable_frames=c["tracking"]["required_stable_frames"],
        max_center_jump_px=c["tracking"]["max_center_jump_px"],
        target_timeout_s=c["tracking"]["target_timeout_s"],
        crop_exclusion_px=c["safety"]["crop_exclusion_px"],
        require_stationary=c["safety"]["require_stationary"],
        minimum_confidence=c["safety"]["minimum_confidence"],
        treatment_enabled=c["hardware"]["treatment_enabled"],
        hardware_mode=c["hardware"]["mode"],
        serial_port=c["hardware"]["serial_port"],
        baudrate=c["hardware"]["baudrate"],
        pan_min_deg=c["hardware"]["pan_min_deg"],
        pan_max_deg=c["hardware"]["pan_max_deg"],
        tilt_min_deg=c["hardware"]["tilt_min_deg"],
        tilt_max_deg=c["hardware"]["tilt_max_deg"],
        calibration=Calibration(**cal),
    )
