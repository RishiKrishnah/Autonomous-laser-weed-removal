from weedlaser.config import Calibration
from weedlaser.crop_exclusion import CropExclusion, CropZone
from weedlaser.localization import (
    Detection,
    choose_target,
    point_to_servo,
)
from weedlaser.safety import (
    SafetyGate,
    SafetyInputs,
    SafetyState,
)
from weedlaser.tracker import StableTargetTracker
from weedlaser.verification import TargetVerifier


def test_detection_center():

    detection = Detection(
        0,
        "weed",
        0.9,
        (10, 20, 30, 40),
    )

    assert detection.center == (
        20.0,
        30.0,
    )


def test_detection_area():

    detection = Detection(
        0,
        "weed",
        0.9,
        (10, 20, 30, 40),
    )

    assert detection.area == 400


def test_target_selection():

    detections = [
        Detection(
            0,
            "weed_a",
            0.60,
            (0, 0, 50, 50),
        ),
        Detection(
            1,
            "weed_b",
            0.90,
            (300, 200, 350, 250),
        ),
    ]

    target = choose_target(
        detections,
        (320, 240),
    )

    assert target is not None
    assert target.class_name == "weed_b"


def test_tracker_stability():

    tracker = StableTargetTracker(
        required_frames=3,
        max_jump_px=20,
    )

    tracker.update(
        (100, 100),
        0.9,
    )

    tracker.update(
        (102, 101),
        0.9,
    )

    tracker.update(
        (101, 100),
        0.9,
    )

    assert tracker.is_stable()


def test_tracker_jump_resets_history():

    tracker = StableTargetTracker(
        required_frames=3,
        max_jump_px=10,
    )

    tracker.update(
        (100, 100),
        0.9,
    )

    tracker.update(
        (101, 101),
        0.9,
    )

    tracker.update(
        (300, 300),
        0.9,
    )

    assert not tracker.is_stable()


def test_tracker_timeout():

    tracker = StableTargetTracker(
        required_frames=3,
        max_jump_px=20,
        timeout_s=0.01,
    )

    tracker.update(
        (100, 100),
        0.9,
    )

    import time

    time.sleep(0.02)

    tracker.update(
        (101, 101),
        0.9,
    )

    assert not tracker.is_stable()


def test_servo_mapping_center():

    calibration = Calibration(
        640,
        480,
        90,
        70,
        0.1,
        0.1,
    )

    pan, tilt = point_to_servo(
        (320, 240),
        calibration,
        (20, 160),
        (20, 120),
    )

    assert pan == 90
    assert tilt == 70


def test_servo_mapping_clips():

    calibration = Calibration(
        640,
        480,
        90,
        70,
        0.1,
        0.1,
    )

    pan, tilt = point_to_servo(
        (5000, -5000),
        calibration,
        (20, 160),
        (20, 120),
    )

    assert pan == 160
    assert tilt == 120


def test_crop_zone_detection():

    zone = CropZone(
        name="crop_1",
        points=[
            (0, 0),
            (100, 0),
            (100, 100),
            (0, 100),
        ],
    )

    exclusion = CropExclusion(
        enabled=True,
        zones=[zone],
    )

    inside, name = exclusion.target_is_in_crop((50, 50))

    assert inside
    assert name == "crop_1"


def test_crop_zone_outside():

    zone = CropZone(
        name="crop_1",
        points=[
            (0, 0),
            (100, 0),
            (100, 100),
            (0, 100),
        ],
    )

    exclusion = CropExclusion(
        enabled=True,
        zones=[zone],
    )

    inside, name = exclusion.target_is_in_crop((200, 200))

    assert not inside
    assert name is None


def test_safety_blocks_when_disabled():

    gate = SafetyGate(0.55)

    inputs = SafetyInputs(
        confidence=0.95,
        stable=True,
        crop_near_target=False,
        interlock_closed=True,
        emergency_stop=False,
        treatment_enabled=False,
        stationary=True,
    )

    assert gate.evaluate(inputs) == SafetyState.BLOCKED


def test_safety_blocks_unstable():

    gate = SafetyGate(0.55)

    inputs = SafetyInputs(
        confidence=0.95,
        stable=False,
        crop_near_target=False,
        interlock_closed=True,
        emergency_stop=False,
        treatment_enabled=True,
        stationary=True,
    )

    assert gate.evaluate(inputs) == SafetyState.BLOCKED


def test_safety_blocks_crop():

    gate = SafetyGate(0.55)

    inputs = SafetyInputs(
        confidence=0.95,
        stable=True,
        crop_near_target=True,
        interlock_closed=True,
        emergency_stop=False,
        treatment_enabled=True,
        stationary=True,
    )

    assert gate.evaluate(inputs) == SafetyState.BLOCKED


def test_safety_blocks_estop():

    gate = SafetyGate(0.55)

    inputs = SafetyInputs(
        confidence=0.95,
        stable=True,
        crop_near_target=False,
        interlock_closed=True,
        emergency_stop=True,
        treatment_enabled=True,
        stationary=True,
    )

    assert gate.evaluate(inputs) == SafetyState.BLOCKED


def test_safety_ready():

    gate = SafetyGate(0.55)

    inputs = SafetyInputs(
        confidence=0.95,
        stable=True,
        crop_near_target=False,
        interlock_closed=True,
        emergency_stop=False,
        treatment_enabled=True,
        stationary=True,
    )

    assert gate.evaluate(inputs) == SafetyState.READY


def test_verification_success():

    verifier = TargetVerifier(confidence_drop_threshold=0.15)

    result = verifier.compare(
        0.90,
        0.60,
    )

    assert result.verified
    assert result.confidence_change == 0.30


def test_verification_failure():

    verifier = TargetVerifier(confidence_drop_threshold=0.15)

    result = verifier.compare(
        0.90,
        0.85,
    )

    assert not result.verified
