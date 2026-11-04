from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from src.config.settings import AppSettings


def build_chat_runtime(
    settings: AppSettings,
    index_dir: str | Path,
    history: Iterable[Dict[str, Any]],
    encoder: Any,
    reranker: Any,
    llm: Any,
    top_k: int,
    max_iterations: int,
) -> Tuple[Any, Any, Any, Any]:
    from src.agents.query_analyzer import QueryAnalyzerAgent
    from src.agents.reasoning_agent import ReasoningAgent
    from src.agents.retriever_agent import RetrieverAgent
    from src.agents.tool_decision_agent import ToolDecisionAgent
    from src.agents.validator_agent import ValidatorAgent
    from src.memory.conversation import ConversationMemory
    from src.orchestration.agentic_rag import AgenticRAGOrchestrator
    from src.orchestration.indexing import IndexingService
    from src.retrieval.faiss_store import FaissStore
    from src.retrieval.keyword import KeywordRetriever

    chat_settings = replace(
        settings,
        top_k=top_k,
        max_iterations=max_iterations,
    )
    store = FaissStore(str(index_dir))
    store.load()

    keyword = KeywordRetriever()
    if store.chunks:
        keyword.fit(store.chunks)

    memory = ConversationMemory()
    for message in list(history)[-8:]:
        memory.add(message["role"], message["content"])

    indexing = IndexingService(
        encoder=encoder,
        faiss_store=store,
        keyword_retriever=keyword,
        chunk_size=chat_settings.chunk_size,
        chunk_overlap=chat_settings.chunk_overlap,
    )
    orchestrator = AgenticRAGOrchestrator(
        settings=chat_settings,
        analyzer=QueryAnalyzerAgent(llm),
        retriever=RetrieverAgent(encoder, store, keyword, reranker),
        reasoner=ReasoningAgent(llm),
        validator=ValidatorAgent(llm),
        decider=ToolDecisionAgent(),
        memory=memory,
    )
    return indexing, orchestrator, store, keyword
