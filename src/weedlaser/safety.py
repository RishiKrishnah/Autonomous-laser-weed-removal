from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SafetyState(str, Enum):
    BLOCKED = "BLOCKED"
    READY = "READY"


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
    """
    Software safety gate.

    This gate never replaces physical safety systems.

    A READY state means that all configured software conditions
    have passed. It does not directly authorize hazardous actuation.
    """

    def __init__(
        self,
        minimum_confidence: float,
        require_stationary: bool = True,
    ):
        self.minimum_confidence = minimum_confidence
        self.require_stationary = require_stationary

    def evaluate(
        self,
        inputs: SafetyInputs,
    ) -> SafetyState:

        if inputs.emergency_stop:
            return SafetyState.BLOCKED

        if not inputs.interlock_closed:
            return SafetyState.BLOCKED

        if not inputs.treatment_enabled:
            return SafetyState.BLOCKED

        if inputs.confidence < self.minimum_confidence:
            return SafetyState.BLOCKED

        if not inputs.stable:
            return SafetyState.BLOCKED

        if inputs.crop_near_target:
            return SafetyState.BLOCKED

        if self.require_stationary and not inputs.stationary:
            return SafetyState.BLOCKED

        return SafetyState.READY

    def authorize(
        self,
        inputs: SafetyInputs,
    ) -> bool:
        return self.evaluate(inputs) == SafetyState.READY
