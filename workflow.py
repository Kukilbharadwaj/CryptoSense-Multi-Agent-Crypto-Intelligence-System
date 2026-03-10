"""
CryptoSense Workflow Module
============================
Defines the LangGraph workflow for the multi-agent system.

Architecture (Parallel Execution):
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                    (CLI / Gradio Web UI)                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ User Query + Validation
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                            │
│                  (Master Controller)                            │
│                                                                 │
│  • Parses user intent                                           │
│  • Extracts cryptocurrency identifier                           │
│  • Routes tasks to sub-agents (parallel)                        │
└────────┬──────────────────┬──────────────────┬─────────────────┘
         │                  │                  │
         ▼                  ▼                  ▼
┌────────────────┐ ┌────────────────┐ ┌────────────────────────┐
│  MARKET AGENT  │ │  NEWS AGENT    │ │  KNOWLEDGE AGENT       │
│                │ │                │ │                        │
│ CoinGecko API  │ │  CoinDesk RSS  │ │  Wikipedia API         │
│                │ │                │ │                        │
│ • Live prices  │ │ • Latest news  │ │ • Coin origin & history│
│ • Market cap   │ │ • Headlines    │ │ • Founder info         │
│ • Volume       │ │ • Summaries    │ │ • Use case & tech      │
│ • % changes    │ │                │ │                        │
│ • Trending     │ │                │ │                        │
└────────┬───────┘ └───────┬────────┘ └──────────┬─────────────┘
         │                 │                      │
         └─────────────────┴──────────────────────┘
                           │ (Parallel Aggregation)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYST AGENT                                │
│               (Synthesis & Reasoning Layer)                     │
│                                                                 │
│  • Cross-references market data + news sentiment + background   │
│  • Detects signal conflicts (e.g. price up, news negative)      │
│  • Generates confidence scores                                  │
│  • Produces structured intelligence report                      │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                               │
│                                                                 │
│  • Market Snapshot       • Sentiment Score (Bullish/Bearish)    │
│  • News Summary          • Background Brief                     │
│  • Risk Signals          • Final Intelligence Report            │
└─────────────────────────────────────────────────────────────────┘
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
from monitoring import TraceContext, metrics_store, flush
from evaluation import evaluator, evaluation_store


def create_workflow():
    """
    Create the LangGraph workflow with PARALLEL agent execution.
    
    Graph Structure:
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         │
                ┌────────▼────────┐
                │   Orchestrator  │
                │ (Parse Intent)  │
                └────────┬────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌───────────┐
    │ Market  │    │  News   │    │ Knowledge │
    │ Agent   │    │  Agent  │    │   Agent   │
    └────┬────┘    └────┬────┘    └─────┬─────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                ┌────────▼────────┐
                │  Analyst Agent  │
                │  (Synthesis)    │
                └────────┬────────┘
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
    
    # Define edges for PARALLEL execution
    # Step 1: Start -> Orchestrator
    workflow.add_edge(START, "orchestrator")
    
    # Step 2: Orchestrator fans out to 3 agents in PARALLEL
    workflow.add_edge("orchestrator", "market")
    workflow.add_edge("orchestrator", "news")
    workflow.add_edge("orchestrator", "knowledge")
    
    # Step 3: All 3 agents converge to Analyst
    workflow.add_edge("market", "analyst")
    workflow.add_edge("news", "analyst")
    workflow.add_edge("knowledge", "analyst")
    
    # Step 4: Analyst -> End
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
    # Create monitoring trace
    trace = TraceContext(query=query)

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
        "tasks": [],
        "trace_ctx": trace,
    }
    
    # Run the workflow
    try:
        result = app.invoke(initial_state)
        
        report = result.get("final_report", "No report generated.")
        error = result.get("error")

        # Finalize monitoring
        trace.finalize(output=report, error=error)

        # Run evaluation
        metrics = trace.get_metrics_summary()
        eval_report = evaluator.evaluate(
            query=query,
            final_report=report,
            metrics=metrics,
            coin_id=result.get("coin_id", ""),
            tasks=result.get("tasks"),
        )
        evaluation_store.record(eval_report)
        metrics_store.record(query, metrics, report_preview=report[:200])

        if error:
            return f"Error: {error}"
        
        return report
        
    except Exception as e:
        trace.finalize(error=str(e))
        return f"Workflow Error: {str(e)}"


def run_query_with_trace(query: str) -> tuple:
    """
    Run a query with full trace information for debugging,
    plus Langfuse monitoring and DeepEval evaluation.
    
    Args:
        query: User's question about cryptocurrency
        
    Returns:
        Tuple of (final_report, trace_info)
    """
    # Create monitoring trace
    trace = TraceContext(query=query)

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
        "tasks": [],
        "trace_ctx": trace,
    }
    
    try:
        result = app.invoke(initial_state)
        
        report = result.get("final_report", "No report generated.")
        error = result.get("error")

        # Finalize monitoring
        trace.finalize(output=report, error=error)

        # Collect monitoring metrics
        monitoring_metrics = trace.get_metrics_summary()

        # Run evaluation
        eval_report = evaluator.evaluate(
            query=query,
            final_report=report,
            metrics=monitoring_metrics,
            coin_id=result.get("coin_id", ""),
            tasks=result.get("tasks"),
        )
        evaluation_store.record(eval_report)
        metrics_store.record(query, monitoring_metrics, report_preview=report[:200])

        trace_info = {
            "coin_identified": result.get("coin_id"),
            "tasks_executed": result.get("tasks"),
            "step_count": result.get("step_count"),
            "messages": result.get("messages", []),
            "error": error,
            "monitoring": monitoring_metrics,
            "evaluation": eval_report.to_dict(),
        }
        
        return report, trace_info
        
    except Exception as e:
        trace.finalize(error=str(e))
        return f"Workflow Error: {str(e)}", {"error": str(e)}


# Test the workflow structure
if __name__ == "__main__":
    print("Creating CryptoSense Workflow...")
    app = create_workflow()
    print("Workflow created successfully!")
    
    # Print the graph structure
    print("\nWorkflow Nodes:", list(app.nodes.keys()))
