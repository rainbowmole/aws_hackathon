"""Typed policy wrapper around the local Strands Decider 2B service."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any


# These constants drive the "Human Review" flag in the UI
URGENCY_CONFIDENCE_THRESHOLD = 0.70
SPECIALTY_MARGIN_THRESHOLD = 0.10
MULTI_SPECIALTY_CUTOFF = 0.50
MULTI_SPECIALTY_RULE_ENABLED = False


DEFAULT_SPECIALTIES = (
    "cardiology",
    "neurology",
    "pediatrics",
    "obstetrics and gynecology",
    "orthopedics",
    "gastroenterology",
    "general medicine",
)

def needs_human_review(result) -> bool:
    p = result.get("urgency_confidence", 0.5)
    urgency_certainty = max(p, 1 - p)

    if urgency_certainty < URGENCY_CONFIDENCE_THRESHOLD:
        return True
    if result.get("margin", 0.0) < SPECIALTY_MARGIN_THRESHOLD:
        return True
    if MULTI_SPECIALTY_RULE_ENABLED:
        scores = result.get("raw_scores", {})
        if sum(1 for s in scores.values() if s >= MULTI_SPECIALTY_CUTOFF) >= 2:
            return True
    return False

@dataclass(frozen=True)
class DeciderResult:

    """Structured routing result returned by :class:`SpecialtyPolicyDecider`."""

    best_choice: str
    raw_scores: dict[str, float]
    confidence: float
    margin: float
    latency_ms: float | None
    is_emergency: bool
    urgency_confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "best_choice": self.best_choice,
            "raw_scores": self.raw_scores,
            "confidence": self.confidence,
            "margin": self.margin,
            "latency_ms": self.latency_ms,
            "is_emergency": self.is_emergency,
            "urgency_confidence": self.urgency_confidence,
        }


class SpecialtyPolicyDecider:
    """Classify a patient note into urgency and a medical specialty.

    Uses a fallback format of binary (noul) questions for both urgency
    and specialty to ensure compatibility with the local Decider server.
    """

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:8000/v1/systemone",
        specialties: tuple[str, ...] = DEFAULT_SPECIALTIES,
        timeout_seconds: float = 15.0,
    ) -> None:
        if not specialties:
            raise ValueError("specialties must contain at least one option")
        self.endpoint = endpoint
        self.specialties = specialties
        self.timeout_seconds = timeout_seconds

    def classify(self, state_text: str) -> dict[str, Any]:
        """Return the best specialty, urgency status, and performance metrics."""
        if not state_text.strip():
            raise ValueError("state_text must not be empty")

        questions = {
            "urgency": {
                "type": "noul",
                "instructions": (
                    "Does this note describe an immediate life-threatening emergency "
                    "(unresponsive, shock, severe breathing difficulty, stroke signs, "
                    "heart attack signs, severe bleeding) that needs emergency care now?"
                ),
            }
        }
        for s in self.specialties:
            questions[s] = {
                "type": "noul",
                "instructions": (
                    f"Is {s} the most appropriate first specialist for this patient note? "
                    f"Options: {', '.join(self.specialties)}."
                ),
            }

        body = {"state": state_text, "questions": questions}
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.load(response)

        try:
            # Process Urgency
            urgency_score = float(payload["answers"]["urgency"]["noul"])
            is_emergency = urgency_score >= 0.5

            # Process Specialties
            specialty_scores = {
                s: float(payload["answers"][s]["noul"])
                for s in self.specialties
            }

            ranked = sorted(specialty_scores.items(), key=lambda item: item[1], reverse=True)
            best_choice, confidence = ranked[0]
            second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Decider response did not contain valid routing scores") from error

        result = DeciderResult(
            best_choice=best_choice,
            raw_scores=specialty_scores,
            confidence=confidence,
            margin=confidence - second_score,
            latency_ms=payload.get("latency_ms"),
            is_emergency=is_emergency,
            urgency_confidence=urgency_score,
        )
        return result.as_dict()
