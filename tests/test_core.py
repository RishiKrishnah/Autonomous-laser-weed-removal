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


def _simulated_turret_samples(n_side: int, look_ahead_m: float = 0.4):
    """
    Ground-truth servo angles for a camera 0.6 m up looking at a point on
    the ground, with the turret offset 8 cm sideways and 3 cm up and aimed
    at the same point, so the true pixel -> angle mapping is non-linear.
    """

    import numpy as np

    from weedlaser.servo_calibration import CalibrationSample

    w, h, focal = 1280, 720, 900.0

    def look_at(pos, target):
        f = target - pos
        f = f / np.linalg.norm(f)
        up = np.array([0.0, 1.0, 0.0]) if look_ahead_m == 0 else np.array([0.0, 0.0, 1.0])
        r = np.cross(up, f)
        r = r / np.linalg.norm(r)
        return np.stack([r, np.cross(f, r), f])

    cam = np.array([0.0, 0.0, 0.6])
    turret = cam + np.array([0.08, 0.0, 0.03])
    centre = np.array([0.0, look_ahead_m, 0.0])
    cam_rot, turret_rot = look_at(cam, centre), look_at(turret, centre)

    samples = []

    for x in np.linspace(80, w - 80, n_side):
        for y in np.linspace(80, h - 80, n_side):
            ray = cam_rot.T @ np.array([(x - w / 2) / focal, -(y - h / 2) / focal, 1.0])
            ground = cam - cam[2] / ray[2] * ray
            d = turret_rot @ (ground - turret)
            pan = 90 + np.degrees(np.arctan2(d[0], d[2]))
            tilt = 70 + np.degrees(np.arctan2(d[1], np.hypot(d[0], d[2])))
            samples.append(CalibrationSample(float(x), float(y), float(pan), float(tilt)))

    return samples, (w, h)


def test_servo_calibration_fit_accuracy(tmp_path):
    from weedlaser.servo_calibration import ServoCalibration, fit_calibration

    samples, size = _simulated_turret_samples(4)
    fitted = fit_calibration(samples, size)

    assert fitted.degree == 3
    assert fitted.rms_deg < 0.3

    # Held-out points between the calibration grid.
    held_out, _ = _simulated_turret_samples(9)
    worst = max(
        max(abs(p - s.pan), abs(t - s.tilt))
        for s in held_out
        for p, t in [fitted.predict((s.x, s.y), size)]
    )
    assert worst < 0.75

    path = tmp_path / "cal.json"
    fitted.save(path)
    loaded = ServoCalibration.load(path)
    assert loaded.predict((640, 360), size) == fitted.predict((640, 360), size)

    # Resolution independence: same point in a half-size frame.
    p1 = fitted.predict((640, 360), size)
    p2 = fitted.predict((320, 180), (640, 360))
    assert abs(p1[0] - p2[0]) < 1e-9 and abs(p1[1] - p2[1]) < 1e-9


def test_point_to_servo_uses_actual_frame_centre():

    calibration = Calibration(640, 480, 90, 70, 0.1, 0.1)

    pan, tilt = point_to_servo(
        (640, 360),
        calibration,
        (20, 160),
        (20, 120),
        frame_size=(1280, 720),
    )

    assert pan == 90
    assert tilt == 70
