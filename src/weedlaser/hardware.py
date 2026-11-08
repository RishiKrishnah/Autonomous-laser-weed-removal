from __future__ import annotations

import glob
import os
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
    def move(
        self,
        pan_deg: float,
        tilt_deg: float,
    ) -> None:
        raise NotImplementedError

    def treatment(
        self,
        enabled: bool,
    ) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class SimulationController(HardwareController):
    """
    Safe software-only controller.

    Treatment is represented by a simulated indicator.
    """

    def __init__(self):
        self.pan = 90.0
        self.tilt = 70.0
        self.indicator_on = False

    def move(
        self,
        pan_deg: float,
        tilt_deg: float,
    ) -> None:

        self.pan = pan_deg
        self.tilt = tilt_deg

        print(f"[SIM] PAN={pan_deg:.1f} TILT={tilt_deg:.1f}")

    def treatment(
        self,
        enabled: bool,
    ) -> None:

        self.indicator_on = enabled

        print(f"[SIM] LASER={'ON' if enabled else 'OFF'}")

    def close(self) -> None:
        self.treatment(False)


class SerialController(HardwareController):
    """
    Serial controller for the Arduino pan/tilt laser
    firmware (firmware/arduino/pan_tilt_laser).

    The firmware switches the laser off by itself if
    commands stop arriving, so treatment() must be
    called every frame.
    """

    def __init__(
        self,
        port: str,
        baudrate: int,
        limits: ServoLimits,
    ):
        if serial is None:
            raise RuntimeError("pyserial is required for serial mode.")

        self.ser = serial.Serial(
            port,
            baudrate=baudrate,
            timeout=1.0,
        )

        self.limits = limits

        time.sleep(2.0)

        self.treatment(False)

    def _send(
        self,
        command: str,
    ) -> None:

        self.ser.write((command.strip() + "\n").encode("ascii"))

        # Discard firmware replies so the OS buffer never fills up.
        if self.ser.in_waiting:
            self.ser.reset_input_buffer()

    def move(
        self,
        pan_deg: float,
        tilt_deg: float,
    ) -> None:

        pan_deg = max(
            self.limits.pan_min,
            min(
                self.limits.pan_max,
                pan_deg,
            ),
        )

        tilt_deg = max(
            self.limits.tilt_min,
            min(
                self.limits.tilt_max,
                tilt_deg,
            ),
        )

        self._send(f"MOVE {pan_deg:.2f} {tilt_deg:.2f}")

    def treatment(
        self,
        enabled: bool,
    ) -> None:

        self._send("LASER ON" if enabled else "LASER OFF")

    def close(self) -> None:
        try:
            self.treatment(False)
            self.ser.close()
        except Exception:
            pass


def resolve_serial_port(
    candidates: str | list[str],
) -> str:
    """
    Return the first existing port from a name, a list
    of names, or glob patterns like /dev/cu.usbmodem*.
    """

    if isinstance(candidates, str):
        candidates = [candidates]

    for candidate in candidates:
        if any(ch in candidate for ch in "*?["):
            matches = sorted(glob.glob(candidate))

            if matches:
                return matches[0]

        elif not candidate.startswith("/dev/") or os.path.exists(candidate):
            return candidate

    raise RuntimeError(
        f"No serial port found (tried {candidates}). Is the Arduino plugged in?"
    )


def create_controller(
    config,
) -> HardwareController:

    if config.hardware_mode == "simulation":
        return SimulationController()

    if config.hardware_mode == "serial":
        port = resolve_serial_port(config.serial_port)

        print(f"[SERIAL] Using {port}")

        return SerialController(
            port,
            config.baudrate,
            ServoLimits(
                config.pan_min_deg,
                config.pan_max_deg,
                config.tilt_min_deg,
                config.tilt_max_deg,
            ),
        )

    raise ValueError(f"Unsupported hardware mode: {config.hardware_mode}")
