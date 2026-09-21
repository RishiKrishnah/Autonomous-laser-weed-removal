from __future__ import annotations

import argparse
import time

import cv2

from .config import load_runtime_config
from .detector import WeedDetector
from .hardware import create_controller
from .localization import choose_target, point_to_servo
from .logger import EventLogger
from .safety import SafetyGate, SafetyInputs
from .tracker import StableTargetTracker


def parse_source(value: str):
    try:
        return int(value)
    except ValueError:
        return value


def main():
    parser = argparse.ArgumentParser(description="Vision-guided weed targeting pipeline")
    parser.add_argument("--weights", required=True)
    parser.add_argument("--source", default="0")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--no-display", action="store_true")
    args = parser.parse_args()

    cfg = load_runtime_config(args.config)
    detector = WeedDetector(args.weights, cfg.confidence, cfg.iou, cfg.imgsz)
    tracker = StableTargetTracker(
        cfg.required_stable_frames,
        cfg.max_center_jump_px,
        cfg.target_timeout_s,
    )
    safety = SafetyGate(cfg.minimum_confidence, cfg.require_stationary)
    hardware = create_controller(cfg)
    logger = EventLogger()

    cap = cv2.VideoCapture(parse_source(args.source))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.calibration.camera_width_px)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.calibration.camera_height_px)

    if not cap.isOpened():
        hardware.close()
        raise RuntimeError(f"Could not open camera/source: {args.source}")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            h, w = frame.shape[:2]
            detections = detector.predict(frame)
            target = choose_target(detections, (w / 2, h / 2))

            safe_state = "BLOCKED"
            if target is not None:
                state = tracker.update(target.center, target.confidence)
                point = state.point
                pan, tilt = point_to_servo(
                    point,
                    cfg.calibration,
                    (cfg.pan_min_deg, cfg.pan_max_deg),
                    (cfg.tilt_min_deg, cfg.tilt_max_deg),
                )

                hardware.move(pan, tilt)

                # Crop proximity is intentionally conservative. The detector is
                # expected to be extended with a crop detector/segmentation model.
                crop_near_target = False

                safety_state = safety.evaluate(
                    SafetyInputs(
                        confidence=target.confidence,
                        stable=tracker.is_stable(),
                        crop_near_target=crop_near_target,
                        interlock_closed=False if cfg.hardware_mode == "simulation" else False,
                        emergency_stop=False,
                        treatment_enabled=cfg.treatment_enabled,
                        stationary=True,
                    )
                )
                safe_state = safety_state.value

                logger.log(
                    target.class_name,
                    target.confidence,
                    point[0],
                    point[1],
                    pan,
                    tilt,
                    safe_state,
                )

                x1, y1, x2, y2 = target.bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (int(point[0]), int(point[1])), 6, (0, 0, 255), -1)
                cv2.putText(
                    frame,
                    f"{target.class_name} {target.confidence:.2f}",
                    (x1, max(20, y1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    frame,
                    f"PAN {pan:.1f} TILT {tilt:.1f} | {safe_state}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                )
            else:
                tracker.reset()
                hardware.treatment(False)
                cv2.putText(
                    frame,
                    "NO TARGET | TREATMENT BLOCKED",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                )

            # Never activate treatment from this reference application unless
            # a separately implemented, independently verified safety controller
            # supplies the required hardware interlock state.
            hardware.treatment(False)

            if not args.no_display:
                cv2.imshow("Autonomous Weed Removal - Safe Mode", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            time.sleep(0.001)
    finally:
        hardware.treatment(False)
        hardware.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
