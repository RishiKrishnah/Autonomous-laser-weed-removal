from __future__ import annotations

import time
from dataclasses import dataclass

try:
    import serial
except ImportError:
    serial = None


@dataclass
class ServoLimits:
    pan_min: float
    pan_max: float
    tilt_min: float
    tilt_max: float


class HardwareController:
    def move(self, pan_deg: float, tilt_deg: float) -> None:
        raise NotImplementedError

    def treatment(self, enabled: bool) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class SimulationController(HardwareController):
    def __init__(self):
        self.pan = 90.0
        self.tilt = 70.0
        self.treatment_on = False

    def move(self, pan_deg: float, tilt_deg: float) -> None:
        self.pan, self.tilt = pan_deg, tilt_deg
        print(f"[SIM] PAN={pan_deg:.1f} TILT={tilt_deg:.1f}")

    def treatment(self, enabled: bool) -> None:
        self.treatment_on = enabled
        print(f"[SIM] SAFE_TREATMENT={'ON' if enabled else 'OFF'}")


class SerialController(HardwareController):
    def __init__(self, port: str, baudrate: int, limits: ServoLimits):
        if serial is None:
            raise RuntimeError("pyserial is required for serial hardware mode.")
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=1.0)
        self.limits = limits
        time.sleep(2.0)
        self.treatment(False)

    def _send(self, command: str) -> None:
        self.ser.write((command.strip() + "\n").encode("ascii"))

    def move(self, pan_deg: float, tilt_deg: float) -> None:
        pan_deg = max(self.limits.pan_min, min(self.limits.pan_max, pan_deg))
        tilt_deg = max(self.limits.tilt_min, min(self.limits.tilt_max, tilt_deg))
        self._send(f"PAN {pan_deg:.2f}")
        self._send(f"TILT {tilt_deg:.2f}")

    def treatment(self, enabled: bool) -> None:
        self._send("TREAT ON" if enabled else "TREAT OFF")

    def close(self) -> None:
        try:
            self.treatment(False)
            self.ser.close()
        except Exception:
            pass


def create_controller(config) -> HardwareController:
    if config.hardware_mode == "simulation":
        return SimulationController()

    if config.hardware_mode == "serial":
        return SerialController(
            config.serial_port,
            config.baudrate,
            ServoLimits(
                config.pan_min_deg,
                config.pan_max_deg,
                config.tilt_min_deg,
                config.tilt_max_deg,
            ),
        )

    raise ValueError(f"Unsupported hardware mode: {config.hardware_mode}")
