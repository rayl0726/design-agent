from __future__ import annotations

from dataclasses import dataclass

from app.services.learning.feedback_reader import IntentCorrectionRecord


@dataclass(frozen=True)
class AliasProposal:
    field: str
    alias: str
    canonical: str
    occurrences: int
    confidence: float = 1.0


class AliasExpansionService:
    def __init__(self, min_occurrences: int = 3):
        self.min_occurrences = min_occurrences

    def propose(self, corrections: list[IntentCorrectionRecord]) -> list[AliasProposal]:
        proposals: list[AliasProposal] = []
        seen = set()

        for record in corrections:
            if record.count < self.min_occurrences:
                continue
            if not record.original_value or not record.corrected_value:
                continue
            if record.original_value == record.corrected_value:
                continue

            key = (record.intent_field, record.original_value, record.corrected_value)
            if key in seen:
                continue
            seen.add(key)

            confidence = min(0.99, 0.5 + 0.1 * record.count)
            proposals.append(
                AliasProposal(
                    field=record.intent_field,
                    alias=record.original_value,
                    canonical=record.corrected_value,
                    occurrences=record.count,
                    confidence=confidence,
                )
            )

        return sorted(proposals, key=lambda p: p.occurrences, reverse=True)
