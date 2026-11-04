from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class DocumentChunk:
    chunk_id: str
    source: str
    page: Optional[int]
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    semantic_score: float
    keyword_score: float = 0.0
    rerank_score: float = 0.0
    combined_score: float = 0.0


@dataclass
class AnalyzerResult:
    intent: str
    needs_multi_step: bool
    sub_questions: List[str]
    rewritten_query: str
    expected_evidence_count: int
    rationale: str


@dataclass
class RetrievalIteration:
    iteration: int
    query_used: str
    chunks: List[RetrievedChunk]
    notes: str


@dataclass
class ReasoningResult:
    answer_draft: str
    claims: List[str]
    claim_support: Dict[str, List[str]]
    reasoning_trace: str


@dataclass
class ValidationResult:
    is_valid: bool
    unsupported_claims: List[str]
    contradictions: List[str]
    confidence: float
    feedback: str


@dataclass
class AgentDecision:
    action: Literal["finalize", "reretrieve", "use_memory", "ask_clarification"]
    reason: str
    next_query: Optional[str] = None


@dataclass
class AgentTrace:
    analyzer: Optional[AnalyzerResult] = None
    retrieval_steps: List[RetrievalIteration] = field(default_factory=list)
    reasoning: Optional[ReasoningResult] = None
    validation: Optional[ValidationResult] = None
    decisions: List[AgentDecision] = field(default_factory=list)


@dataclass
class FinalResponse:
    answer: str
    confidence: float
    citations: List[RetrievedChunk]
    trace: AgentTrace
    exhausted_retries: bool = False
