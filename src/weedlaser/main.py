from __future__ import annotations

import argparse
import time

import cv2

from .config import load_runtime_config
from .crop_exclusion import CropExclusion
from .detector import WeedDetector
from .hardware import create_controller
from .localization import (
    choose_target,
    point_to_servo,
)
from .logger import EventLogger
from .safety import (
    SafetyGate,
    SafetyInputs,
)
from .tracker import StableTargetTracker
from .verification import TargetVerifier


def parse_source(
    value: str,
):
    try:
        return int(value)
    except ValueError:
        return value


def main():
    parser = argparse.ArgumentParser(description=("Vision-guided autonomous weed targeting system"))

    parser.add_argument(
        "--weights",
        required=True,
        help="Path to trained YOLO weights",
    )

    parser.add_argument(
        "--source",
        default="0",
        help="Camera index or video path",
    )

    parser.add_argument(
        "--config",
        default="configs/config.yaml",
        help="Runtime configuration",
    )

    parser.add_argument(
        "--no-display",
        action="store_true",
    )

    args = parser.parse_args()

    cfg = load_runtime_config(args.config)

    detector = WeedDetector(
        args.weights,
        cfg.confidence,
        cfg.iou,
        cfg.imgsz,
    )

    tracker = StableTargetTracker(
        required_frames=(cfg.required_stable_frames),
        max_jump_px=(cfg.max_center_jump_px),
        timeout_s=(cfg.target_timeout_s),
    )

    crop_exclusion = CropExclusion(
        enabled=(cfg.crop_exclusion_enabled),
        zones=cfg.crop_zones,
    )

    safety = SafetyGate(
        minimum_confidence=(cfg.minimum_confidence),
        require_stationary=(cfg.require_stationary),
    )

    verifier = TargetVerifier(cfg.verification.confidence_drop_threshold)

    hardware = create_controller(cfg)

    logger = EventLogger(cfg.logging_directory)

    source = parse_source(args.source)

    cap = cv2.VideoCapture(source)

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        cfg.calibration.camera_width_px,
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        cfg.calibration.camera_height_px,
    )

    if not cap.isOpened():
        hardware.close()

        raise RuntimeError(f"Could not open camera/source: {args.source}")

    previous_target_confidence = None

    try:
        while True:
            ok, frame = cap.read()

            if not ok:
                break

            h, w = frame.shape[:2]

            detections = detector.predict(frame)

            target = choose_target(
                detections,
                (
                    w / 2.0,
                    h / 2.0,
                ),
            )

            # Always keep the safe indicator off
            # until all runtime conditions have passed.
            hardware.treatment(False)

            crop_exclusion.draw(frame)

            safety_state = "BLOCKED"
            verification_state = "NOT_RUN"

            if target is None:
                tracker.reset()

                cv2.putText(
                    frame,
                    "NO TARGET | BLOCKED",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 0, 255),
                    2,
                )

            else:
                state = tracker.update(
                    target.center,
                    target.confidence,
                )

                point = state.point

                pan, tilt = point_to_servo(
                    point,
                    cfg.calibration,
                    (
                        cfg.pan_min_deg,
                        cfg.pan_max_deg,
                    ),
                    (
                        cfg.tilt_min_deg,
                        cfg.tilt_max_deg,
                    ),
                )

                hardware.move(
                    pan,
                    tilt,
                )

                crop_near_target, crop_zone = crop_exclusion.target_is_in_crop(point)

                stable = tracker.is_stable()

                safety_inputs = SafetyInputs(
                    confidence=(target.confidence),
                    stable=stable,
                    crop_near_target=(crop_near_target),
                    interlock_closed=(cfg.interlock_closed),
                    emergency_stop=(cfg.emergency_stop),
                    treatment_enabled=(cfg.treatment_enabled),
                    stationary=True,
                )

                safety_state = safety.evaluate(safety_inputs).value

                # Reference implementation never
                # performs hazardous treatment.
                #
                # A READY state is recorded only as
                # a software authorization state.
                #
                # Safe indicator activation can be
                # enabled only in a separately validated
                # safe hardware demonstration.

                if previous_target_confidence is not None and cfg.verification.enabled:
                    result = verifier.compare(
                        previous_target_confidence,
                        target.confidence,
                    )

                    verification_state = "VERIFIED" if result.verified else "NOT_VERIFIED"

                previous_target_confidence = target.confidence

                logger.log(
                    class_id=target.class_id,
                    class_name=target.class_name,
                    confidence=target.confidence,
                    x=point[0],
                    y=point[1],
                    pan=pan,
                    tilt=tilt,
                    stable=stable,
                    crop_near_target=(crop_near_target),
                    crop_zone=crop_zone,
                    safety_state=safety_state,
                    verification_state=(verification_state),
                )

                x1, y1, x2, y2 = target.bbox

                cv2.rectangle(
                    frame,
                    (x1, y1),
                    (x2, y2),
                    (0, 255, 0),
                    2,
                )

                cv2.circle(
                    frame,
                    (
                        int(point[0]),
                        int(point[1]),
                    ),
                    6,
                    (0, 0, 255),
                    -1,
                )

                label = f"{target.class_name} {target.confidence:.2f}"

                cv2.putText(
                    frame,
                    label,
                    (
                        x1,
                        max(20, y1 - 8),
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 0),
                    2,
                )

                status = f"PAN {pan:.1f} TILT {tilt:.1f} | {safety_state}"

                cv2.putText(
                    frame,
                    status,
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                )

                if crop_near_target:
                    cv2.putText(
                        frame,
                        ("CROP ZONE | TREATMENT BLOCKED"),
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 0, 255),
                        2,
                    )

                elif not stable:
                    cv2.putText(
                        frame,
                        "TARGET UNSTABLE",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 165, 255),
                        2,
                    )

                else:
                    cv2.putText(
                        frame,
                        "TARGET STABLE",
                        (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )

            # Absolute final output state.
            # This guarantees safe shutdown of the
            # treatment/indicator interface.
            hardware.treatment(False)

            if not args.no_display:
                cv2.imshow(
                    "Autonomous Weed Removal - SAFE MODE",
                    frame,
                )

                key = cv2.waitKey(1) & 0xFF

                if key == ord("q"):
                    break

            time.sleep(0.001)

    finally:
        hardware.treatment(False)

        hardware.close()

        cap.release()

        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
