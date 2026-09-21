from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SafetyState(str, Enum):
    BLOCKED = "BLOCKED"
    READY = "READY"
    FIRE = "FIRE"


@dataclass
class SafetyInputs:
    confidence: float
    stable: bool
    crop_near_target: bool
    interlock_closed: bool
    emergency_stop: bool
    treatment_enabled: bool
    stationary: bool


class SafetyGate:
    """Software gate. Hardware interlocks must remain independent of this gate."""

    def __init__(self, minimum_confidence: float, require_stationary: bool = True):
        self.minimum_confidence = minimum_confidence
        self.require_stationary = require_stationary

    def evaluate(self, x: SafetyInputs) -> SafetyState:
        if x.emergency_stop:
            return SafetyState.BLOCKED
        if not x.interlock_closed:
            return SafetyState.BLOCKED
        if not x.treatment_enabled:
            return SafetyState.BLOCKED
        if x.confidence < self.minimum_confidence:
            return SafetyState.BLOCKED
        if not x.stable:
            return SafetyState.BLOCKED
        if x.crop_near_target:
            return SafetyState.BLOCKED
        if self.require_stationary and not x.stationary:
            return SafetyState.BLOCKED
        return SafetyState.READY

    def authorize_fire(self, x: SafetyInputs) -> bool:
        return self.evaluate(x) == SafetyState.READY
