"""
Interactive pixel -> pan/tilt calibration for the laser turret.

    python scripts/calibrate_servos.py --config configs/config.yaml --source 0

Mount the camera and turret exactly as they will be used, then repeat:
  1. Jog the servos with W/A/S/D until the laser points somewhere new.
  2. Press SPACE to flash the laser and see the dot.
  3. Click on the dot in the video window to record that point.

Record at least 16 points in a rough 4x4 grid covering the whole image
(corners, edges, centre), press F to fit, check the error, then press C to save.
Points with a large error are drawn red; undo or re-record them. Press V to test: in verify mode a
click aims the laser at that pixel using the fitted mapping.

Keys:
  w / s     tilt + / -          a / d   pan - / +
  [ / ]     smaller / larger jog step
  SPACE     laser on/off (auto-off after 2.5 s)
  u         undo last point     r       clear all points
  f         fit                 c       fit and save
  v         toggle verify mode  q / ESC quit (laser off)

Use a low-power laser or the lowest power setting while calibrating, and
wear laser safety glasses.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from weedlaser.config import load_runtime_config  # noqa: E402
from weedlaser.hardware import (  # noqa: E402
    ServoLimits,
    SerialController,
    resolve_serial_port,
)
from weedlaser.servo_calibration import (  # noqa: E402
    MIN_AFFINE_SAMPLES,
    MIN_CUBIC_SAMPLES,
    CalibrationSample,
    ServoCalibration,
    fit_calibration,
)

STEPS_DEG = [0.25, 0.5, 1.0, 2.0, 5.0]
LASER_PULSE_S = 2.5
WINDOW = "Servo calibration"


def parse_source(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def main():
    parser = argparse.ArgumentParser(description="Laser turret calibration")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--source", default="0", help="Camera index or video path")
    parser.add_argument("--output", default=None, help="Defaults to calibration.file in config")
    args = parser.parse_args()

    cfg = load_runtime_config(args.config)
    output = Path(args.output or cfg.calibration.file or "configs/servo_calibration.json")

    port = resolve_serial_port(cfg.serial_port)
    print(f"[SERIAL] Using {port}")

    hardware = SerialController(
        port,
        cfg.baudrate,
        ServoLimits(cfg.pan_min_deg, cfg.pan_max_deg, cfg.tilt_min_deg, cfg.tilt_max_deg),
    )

    cap = cv2.VideoCapture(parse_source(args.source))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.calibration.camera_width_px)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.calibration.camera_height_px)

    if not cap.isOpened():
        hardware.close()
        raise RuntimeError(f"Could not open camera/source: {args.source}")

    pan = cfg.calibration.pan_center_deg
    tilt = cfg.calibration.tilt_center_deg
    step_index = 2

    samples: list[CalibrationSample] = []
    fitted: ServoCalibration | None = None

    if output.exists():
        fitted = ServoCalibration.load(output)
        samples = list(fitted.samples)
        print(f"Loaded {len(samples)} existing points from {output} (press r to clear)")

    laser_on = False
    laser_since = 0.0
    verify_mode = False
    message = "Jog with WASD, SPACE = laser, click the dot to record"
    frame_size = (0, 0)

    def on_mouse(event, x, y, _flags, _param):
        nonlocal pan, tilt, message

        if event != cv2.EVENT_LBUTTONDOWN:
            return

        if verify_mode:
            if fitted is None:
                message = "Fit first (f) before verifying"
                return
            pan, tilt = fitted.predict((x, y), frame_size)
            message = f"Aimed at ({x}, {y}) -> pan {pan:.1f} tilt {tilt:.1f}; SPACE to check"
            return

        samples.append(CalibrationSample(float(x), float(y), pan, tilt))
        message = f"Recorded #{len(samples)}: ({x}, {y}) -> pan {pan:.1f} tilt {tilt:.1f}"

    cv2.namedWindow(WINDOW)
    cv2.setMouseCallback(WINDOW, on_mouse)

    def do_fit() -> ServoCalibration | None:
        nonlocal message
        if len(samples) < MIN_AFFINE_SAMPLES:
            message = f"Need at least {MIN_AFFINE_SAMPLES} points (have {len(samples)})"
            return None
        result = fit_calibration(samples, frame_size)
        kind = {
            1: f"linear (add points: {MIN_CUBIC_SAMPLES}+ recommended)",
            2: f"quadratic (add points: {MIN_CUBIC_SAMPLES}+ recommended)",
            3: "cubic",
        }[result.degree]
        message = f"Fit {kind}: RMS error {result.rms_deg:.2f} deg over {len(samples)} points"
        print(message)
        return result

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            h, w = frame.shape[:2]
            frame_size = (w, h)

            if laser_on and time.time() - laser_since > LASER_PULSE_S:
                laser_on = False

            pan = min(max(pan, cfg.pan_min_deg), cfg.pan_max_deg)
            tilt = min(max(tilt, cfg.tilt_min_deg), cfg.tilt_max_deg)

            # Sent every frame: also the firmware watchdog heartbeat.
            hardware.move(pan, tilt)
            hardware.treatment(laser_on)

            for i, s in enumerate(samples, start=1):
                label = str(i)
                color = (0, 255, 255)

                # Per-point fit error; a large one usually means a mis-click.
                if fitted is not None:
                    p, t = fitted.predict((s.x, s.y), frame_size)
                    err = ((p - s.pan) ** 2 + (t - s.tilt) ** 2) ** 0.5
                    label += f" {err:.1f}"
                    if err > 2 * max(fitted.rms_deg, 0.5):
                        color = (0, 0, 255)

                cv2.circle(frame, (int(s.x), int(s.y)), 5, color, -1)
                cv2.putText(frame, label, (int(s.x) + 6, int(s.y) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            mode = "VERIFY" if verify_mode else "RECORD"
            status = (f"{mode} | PAN {pan:.2f} TILT {tilt:.2f} | step {STEPS_DEG[step_index]} deg"
                      f" | points {len(samples)} | {w}x{h}")
            cv2.putText(frame, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
            cv2.putText(frame, message, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            if laser_on:
                cv2.putText(frame, "LASER ON", (10, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

            cv2.imshow(WINDOW, frame)
            key = cv2.waitKey(1) & 0xFF
            step = STEPS_DEG[step_index]

            if key in (ord("q"), 27):
                break
            elif key == ord("a"):
                pan -= step
            elif key == ord("d"):
                pan += step
            elif key == ord("w"):
                tilt += step
            elif key == ord("s"):
                tilt -= step
            elif key == ord("["):
                step_index = max(0, step_index - 1)
            elif key == ord("]"):
                step_index = min(len(STEPS_DEG) - 1, step_index + 1)
            elif key == ord(" "):
                if laser_on:
                    laser_on = False
                else:
                    # LASER OFF first clears any firmware max-on-time lockout.
                    hardware.treatment(False)
                    laser_on = True
                    laser_since = time.time()
            elif key == ord("u") and samples:
                samples.pop()
                message = f"Removed last point ({len(samples)} left)"
            elif key == ord("r"):
                samples.clear()
                fitted = None
                message = "Cleared all points"
            elif key == ord("f"):
                fitted = do_fit() or fitted
            elif key == ord("c"):
                result = do_fit()
                if result is not None:
                    fitted = result
                    output.parent.mkdir(parents=True, exist_ok=True)
                    fitted.save(output)
                    message += f" | saved to {output}"
                    print(f"Saved {output}")
            elif key == ord("v"):
                verify_mode = not verify_mode
                message = "Verify: click anywhere to aim there" if verify_mode else "Record mode"

    finally:
        hardware.treatment(False)
        hardware.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
