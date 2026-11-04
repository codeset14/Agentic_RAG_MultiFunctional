from __future__ import annotations

import asyncio
from typing import List

from src.agents.query_analyzer import QueryAnalyzerAgent
from src.agents.reasoning_agent import ReasoningAgent
from src.agents.retriever_agent import RetrieverAgent
from src.agents.tool_decision_agent import ToolDecisionAgent
from src.agents.validator_agent import ValidatorAgent
from src.config.settings import AppSettings
from src.core.models import AgentTrace, FinalResponse
from src.memory.conversation import ConversationMemory
from src.utils.scoring import confidence_score


class AgenticRAGOrchestrator:
    def __init__(
        self,
        settings: AppSettings,
        analyzer: QueryAnalyzerAgent,
        retriever: RetrieverAgent,
        reasoner: ReasoningAgent,
        validator: ValidatorAgent,
        decider: ToolDecisionAgent,
        memory: ConversationMemory,
    ) -> None:
        self.settings = settings
        self.analyzer = analyzer
        self.retriever = retriever
        self.reasoner = reasoner
        self.validator = validator
        self.decider = decider
        self.memory = memory

    async def run(self, query: str) -> FinalResponse:
        trace = AgentTrace()
        mem_messages = self.memory.to_messages()
        analysis = await self.analyzer.run(query, mem_messages)
        trace.analyzer = analysis

        current_query = analysis.rewritten_query or query
        exhausted = False
        latest_conf = 0.0
        latest_answer = "No answer generated."
        latest_citations = []

        for i in range(1, self.settings.max_iterations + 1):
            retrieval = self.retriever.retrieve(current_query, iteration=i, top_k=self.settings.top_k)
            trace.retrieval_steps.append(retrieval)
            if not retrieval.chunks:
                latest_answer = "I could not find relevant evidence in indexed documents."
                exhausted = True
                break

            reasoning = await self.reasoner.run(query, retrieval.chunks)
            trace.reasoning = reasoning

            validation = await self.validator.run(reasoning, retrieval.chunks)
            trace.validation = validation

            latest_conf = confidence_score(retrieval.chunks, validation)
            latest_answer = reasoning.answer_draft
            latest_citations = retrieval.chunks

            decision = self.decider.decide(
                validation=validation,
                confidence=latest_conf,
                iteration=i,
                max_iterations=self.settings.max_iterations,
            )
            trace.decisions.append(decision)
            if decision.action == "finalize":
                exhausted = i >= self.settings.max_iterations and latest_conf < self.settings.validation_threshold
                break

            current_query = self.retriever.refine_query(current_query, decision.next_query or decision.reason)
            await asyncio.sleep(0)

        self.memory.add("user", query)
        self.memory.add("assistant", latest_answer)
        return FinalResponse(
            answer=latest_answer,
            confidence=latest_conf,
            citations=latest_citations,
            trace=trace,
            exhausted_retries=exhausted,
        )
