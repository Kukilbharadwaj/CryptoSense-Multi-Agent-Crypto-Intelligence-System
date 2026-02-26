"""
CryptoSense State Module
========================
Defines the shared state for the multi-agent LangGraph workflow.
"""

from typing import TypedDict, Annotated, List, Optional
from operator import add


class AgentState(TypedDict):
    """
    Shared state for all agents in the CryptoSense system.
    
    Attributes:
        query: Original user query
        coin_id: Extracted cryptocurrency identifier
        market_data: Data from Market Agent
        news_data: Data from News Agent
        knowledge_data: Data from Knowledge Agent
        analysis: Synthesized analysis from Analyst Agent
        final_report: Final intelligence report
        messages: Conversation history
        step_count: Counter to prevent infinite loops
        error: Any error messages
    """
    # Input
    query: str
    coin_id: str
    
    # Agent outputs
    market_data: str
    news_data: str
    knowledge_data: str
    analysis: str
    final_report: str
    
    # Control flow
    messages: Annotated[List[str], add]
    step_count: int
    error: Optional[str]
    
    # Task routing
    tasks: List[str]  # Which agents to invoke


def create_initial_state(query: str) -> AgentState:
    """Create initial state from user query."""
    return AgentState(
        query=query,
        coin_id="",
        market_data="",
        news_data="",
        knowledge_data="",
        analysis="",
        final_report="",
        messages=[],
        step_count=0,
        error=None,
        tasks=[]
    )
