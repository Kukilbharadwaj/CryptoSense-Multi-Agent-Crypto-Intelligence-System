"""
CryptoSense State Module
========================
Defines the shared state for the multi-agent LangGraph workflow.
Supports parallel agent execution with proper reducers.
"""

from typing import TypedDict, Annotated, Any, Dict, List, Optional
from operator import add


def keep_last(a: str, b: str) -> str:
    """Reducer that keeps the last non-empty value."""
    return b if b else a


def keep_last_int(a: int, b: int) -> int:
    """Reducer for integers - keeps the max."""
    return max(a, b)


def keep_first_list(a: List[str], b: List[str]) -> List[str]:
    """Reducer that keeps the first non-empty list."""
    return a if a else b


def merge_error(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Reducer that keeps any error."""
    if a and b:
        return f"{a}; {b}"
    return a or b


def keep_last_any(a: Any, b: Any) -> Any:
    """Reducer that keeps the last non-None value."""
    return b if b is not None else a


class AgentState(TypedDict):
    """
    Shared state for all agents in the CryptoSense system.
    
    All fields use reducers to support parallel agent execution.
    
    Attributes:
        query: Original user query
        coin_id: Extracted cryptocurrency identifier
        market_data: Data from Market Agent
        news_data: Data from News Agent
        knowledge_data: Data from Knowledge Agent
        analysis: Synthesized analysis from Analyst Agent
        final_report: Final intelligence report
        messages: Conversation history (appends)
        step_count: Counter to prevent infinite loops
        error: Any error messages
        tasks: Which agents to invoke
        trace_ctx: Monitoring TraceContext instance (passed through graph)
    """
    # Input - set by orchestrator, read by all
    query: Annotated[str, keep_last]
    coin_id: Annotated[str, keep_last]
    
    # Agent outputs - each agent writes its own field
    market_data: Annotated[str, keep_last]
    news_data: Annotated[str, keep_last]
    knowledge_data: Annotated[str, keep_last]
    analysis: Annotated[str, keep_last]
    final_report: Annotated[str, keep_last]
    
    # Control flow
    messages: Annotated[List[str], add]  # Appends messages
    step_count: Annotated[int, keep_last_int]
    error: Annotated[Optional[str], merge_error]
    
    # Task routing
    tasks: Annotated[List[str], keep_first_list]

    # Monitoring – TraceContext instance threaded through the graph
    trace_ctx: Annotated[Optional[Any], keep_last_any]


def create_initial_state(query: str, trace_ctx: Optional[Any] = None) -> dict:
    """Create initial state from user query."""
    return {
        "query": query,
        "coin_id": "",
        "market_data": "",
        "news_data": "",
        "knowledge_data": "",
        "analysis": "",
        "final_report": "",
        "messages": [],
        "step_count": 0,
        "error": None,
        "tasks": [],
        "trace_ctx": trace_ctx,
    }
