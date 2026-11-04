from __future__ import annotations

from src.core.models import AgentDecision, ValidationResult


class ToolDecisionAgent:
    def decide(
        self,
        validation: ValidationResult,
        confidence: float,
        iteration: int,
        max_iterations: int,
    ) -> AgentDecision:
        if validation.is_valid and confidence >= 0.65:
            return AgentDecision(action="finalize", reason="Validation passed with sufficient confidence.")
        if iteration >= max_iterations:
            return AgentDecision(action="finalize", reason="Reached max iterations; return cautious answer.")
        if validation.unsupported_claims:
            return AgentDecision(
                action="reretrieve",
                reason="Unsupported claims detected; improving evidence coverage.",
                next_query="Focus on supporting facts for unsupported claims.",
            )
        return AgentDecision(
            action="reretrieve",
            reason="Confidence too low, trigger another retrieval cycle.",
            next_query=validation.feedback or "Fetch more specific supporting evidence.",
        )
