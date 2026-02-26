"""
CryptoSense Workflow Module
============================
Defines the LangGraph workflow for the multi-agent system.

Workflow:
1. User Query -> Orchestrator (parse intent, extract coin)
2. Orchestrator -> Market/News/Knowledge Agents (parallel data collection)
3. All Data -> Analyst Agent (synthesis)
4. Analyst -> Final Report
"""

from langgraph.graph import StateGraph, START, END

from state import AgentState
from agents import (
    orchestrator_agent,
    market_agent,
    news_agent,
    knowledge_agent,
    analyst_agent,
    MAX_STEPS
)


def create_workflow():
    """
    Create the LangGraph workflow for CryptoSense.
    
    Graph Structure:
    ┌─────────┐
    │  START  │
    └────┬────┘
         │
    ┌────▼────────────┐
    │  Orchestrator   │
    │ (Parse Intent)  │
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │  Market Agent   │
    │  (CoinGecko)    │
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │  News Agent     │
    │  (RSS Feed)     │
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │  Knowledge Agent│
    │  (Wikipedia)    │
    └────┬────────────┘
         │
    ┌────▼────────────┐
    │  Analyst Agent  │
    │  (Synthesis)    │
    └────┬────────────┘
         │
    ┌────▼────┐
    │   END   │
    └─────────┘
    """
    
    # Initialize the graph with our state schema
    workflow = StateGraph(AgentState)
    
    # Add all agent nodes
    workflow.add_node("orchestrator", orchestrator_agent)
    workflow.add_node("market", market_agent)
    workflow.add_node("news", news_agent)
    workflow.add_node("knowledge", knowledge_agent)
    workflow.add_node("analyst", analyst_agent)
    
    # Define edges (sequential flow for reliability)
    workflow.add_edge(START, "orchestrator")
    workflow.add_edge("orchestrator", "market")
    workflow.add_edge("market", "news")
    workflow.add_edge("news", "knowledge")
    workflow.add_edge("knowledge", "analyst")
    workflow.add_edge("analyst", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


def run_query(query: str) -> str:
    """
    Run a query through the CryptoSense workflow.
    
    Args:
        query: User's question about cryptocurrency
        
    Returns:
        Final intelligence report
    """
    # Create the workflow
    app = create_workflow()
    
    # Initialize state
    initial_state = {
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
        "tasks": []
    }
    
    # Run the workflow
    try:
        result = app.invoke(initial_state)
        
        if result.get("error"):
            return f"Error: {result['error']}"
        
        return result.get("final_report", "No report generated.")
        
    except Exception as e:
        return f"Workflow Error: {str(e)}"


def run_query_with_trace(query: str) -> tuple:
    """
    Run a query with full trace information for debugging.
    
    Args:
        query: User's question about cryptocurrency
        
    Returns:
        Tuple of (final_report, trace_info)
    """
    app = create_workflow()
    
    initial_state = {
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
        "tasks": []
    }
    
    try:
        result = app.invoke(initial_state)
        
        trace_info = {
            "coin_identified": result.get("coin_id"),
            "tasks_executed": result.get("tasks"),
            "step_count": result.get("step_count"),
            "messages": result.get("messages", []),
            "error": result.get("error")
        }
        
        return result.get("final_report", "No report generated."), trace_info
        
    except Exception as e:
        return f"Workflow Error: {str(e)}", {"error": str(e)}


# Test the workflow structure
if __name__ == "__main__":
    print("Creating CryptoSense Workflow...")
    app = create_workflow()
    print("Workflow created successfully!")
    
    # Print the graph structure
    print("\nWorkflow Nodes:", list(app.nodes.keys()))
