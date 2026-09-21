from weedlaser.localization import Detection, point_to_servo
from weedlaser.safety import SafetyGate, SafetyInputs, SafetyState
from weedlaser.tracker import StableTargetTracker
from weedlaser.config import Calibration


def test_detection_center():
    d = Detection(0, "weed", 0.9, (10, 20, 30, 40))
    assert d.center == (20.0, 30.0)


def test_tracker_stability():
    t = StableTargetTracker(required_frames=3, max_jump_px=20)
    t.update((100, 100), 0.9)
    t.update((102, 101), 0.9)
    t.update((101, 100), 0.9)
    assert t.is_stable()


def test_tracker_jump_resets_history():
    t = StableTargetTracker(required_frames=3, max_jump_px=10)
    t.update((100, 100), 0.9)
    t.update((101, 101), 0.9)
    t.update((300, 300), 0.9)
    assert not t.is_stable()


def test_servo_mapping():
    cal = Calibration(640, 480, 90, 70, 0.1, 0.1)
    pan, tilt = point_to_servo((320, 240), cal, (20, 160), (20, 120))
    assert pan == 90
    assert tilt == 70


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
