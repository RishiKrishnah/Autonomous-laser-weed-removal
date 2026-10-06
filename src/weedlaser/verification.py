from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VerificationResult:
    before_confidence: float
    after_confidence: float
    confidence_change: float
    verified: bool
    reason: str


class TargetVerifier:
    """
    Safe post-action verification.

    This does not claim that a weed was physically destroyed.
    It only determines whether the visual target confidence
    changed sufficiently after a safe simulated action.
    """

    def __init__(
        self,
        confidence_drop_threshold: float = 0.15,
    ):
        self.threshold = confidence_drop_threshold

    def compare(
        self,
        before_confidence: float,
        after_confidence: float,
    ) -> VerificationResult:

        change = round(before_confidence - after_confidence, 6)

        verified = change >= self.threshold

        if verified:
            reason = "Target confidence decreased beyond the configured threshold."
        else:
            reason = "Target confidence did not decrease sufficiently."

        return VerificationResult(
            before_confidence=before_confidence,
            after_confidence=after_confidence,
            confidence_change=change,
            verified=verified,
            reason=reason,
        )
