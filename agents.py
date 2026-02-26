"""
CryptoSense Agents Module
=========================
Defines all specialized agents for the multi-agent system.

Agents:
- Orchestrator Agent: Parses intent and routes tasks
- Market Agent: Fetches market data via CoinGecko
- News Agent: Fetches news via RSS
- Knowledge Agent: Fetches info via Wikipedia
- Analyst Agent: Synthesizes all data into intelligence report
"""

import os
from typing import Literal
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from state import AgentState
from tools import (
    get_market_tools,
    get_news_tools,
    get_knowledge_tools,
    get_coin_price,
    get_trending_coins,
    get_coin_details,
    get_crypto_news,
    get_general_crypto_news,
    get_wiki_summary,
    get_crypto_history
)

# Load environment variables
load_dotenv()

# Maximum steps to prevent infinite loops
MAX_STEPS = 10

# -----------------------------
# Initialize LLM
# -----------------------------

def get_llm():
    """Initialize Groq LLM with cost-efficient settings."""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        groq_api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
        max_tokens=1024  # Limit output tokens for cost efficiency
    )


# -----------------------------
# Orchestrator Agent
# -----------------------------

def orchestrator_agent(state: AgentState) -> AgentState:
    """
    Master controller agent that:
    1. Parses user intent
    2. Extracts coin identifier
    3. Determines which agents to invoke
    """
    # Check step count to prevent infinite loops
    if state["step_count"] >= MAX_STEPS:
        state["error"] = "Maximum steps exceeded. Terminating to prevent infinite loop."
        return state
    
    state["step_count"] = state["step_count"] + 1
    
    llm = get_llm()
    
    system_prompt = """You are the orchestrator for CryptoSense, a crypto intelligence system.

Your job is to:
1. Extract the cryptocurrency name/id from the user query
2. Determine what information the user wants

IMPORTANT: Respond in this EXACT format:
COIN_ID: <coin_id or 'general' if no specific coin>
TASKS: <comma-separated list from: market, news, knowledge>

Examples:
- "What is Bitcoin's price?" -> COIN_ID: bitcoin, TASKS: market
- "Tell me about Ethereum" -> COIN_ID: ethereum, TASKS: market, news, knowledge
- "Latest crypto news" -> COIN_ID: general, TASKS: news
- "What's trending?" -> COIN_ID: general, TASKS: market

Common coin mappings:
- BTC, Bitcoin -> bitcoin
- ETH, Ethereum -> ethereum  
- SOL, Solana -> solana
- ADA, Cardano -> cardano
- XRP, Ripple -> ripple
- DOGE, Dogecoin -> dogecoin
- DOT, Polkadot -> polkadot
- MATIC, Polygon -> matic-network
- AVAX, Avalanche -> avalanche-2
- LINK, Chainlink -> chainlink
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User query: {state['query']}")
    ]
    
    response = llm.invoke(messages)
    response_text = response.content
    
    # Parse response - handle both single-line and multi-line formats
    coin_id = "bitcoin"  # default
    tasks = ["market", "news", "knowledge"]  # default all
    
    # Normalize the response - replace common separators
    normalized_text = response_text.strip().upper()
    
    # Extract COIN_ID
    if "COIN_ID:" in normalized_text:
        # Find COIN_ID value
        coin_start = normalized_text.find("COIN_ID:") + len("COIN_ID:")
        coin_end = len(normalized_text)
        
        # Check for TASKS marker to know where coin_id ends
        if "TASKS:" in normalized_text:
            tasks_pos = normalized_text.find("TASKS:")
            if tasks_pos > coin_start:
                coin_end = tasks_pos
        
        # Also check for comma or newline
        remaining = normalized_text[coin_start:coin_end]
        if "," in remaining:
            coin_id = remaining.split(",")[0].strip().lower()
        elif "\n" in remaining:
            coin_id = remaining.split("\n")[0].strip().lower()
        else:
            coin_id = remaining.strip().lower()
    
    # Extract TASKS
    if "TASKS:" in normalized_text:
        tasks_start = normalized_text.find("TASKS:") + len("TASKS:")
        tasks_text = normalized_text[tasks_start:].strip()
        
        # Clean up the tasks text
        if "\n" in tasks_text:
            tasks_text = tasks_text.split("\n")[0]
        
        # Parse comma-separated tasks
        parsed_tasks = []
        for t in tasks_text.split(","):
            task = t.strip().lower()
            if task in ["market", "news", "knowledge"]:
                parsed_tasks.append(task)
        
        if parsed_tasks:
            tasks = parsed_tasks
    
    # Clean coin_id of any remaining artifacts
    coin_id = coin_id.replace("tasks:", "").replace(",", "").strip()
    
    state["coin_id"] = coin_id
    state["tasks"] = tasks
    state["messages"] = [f"Orchestrator: Identified coin '{coin_id}' with tasks {tasks}"]
    
    return state


# -----------------------------
# Market Agent
# -----------------------------

def market_agent(state: AgentState) -> AgentState:
    """
    Fetches market data using CoinGecko tools.
    Always runs in parallel architecture.
    """
    if state["step_count"] >= MAX_STEPS:
        return state
    
    state["step_count"] = state["step_count"] + 1
    
    coin_id = state["coin_id"]
    results = []
    
    try:
        if coin_id == "general":
            # Get trending coins for general queries
            trending_result = get_trending_coins.invoke({})
            results.append(trending_result)
        else:
            # Get specific coin data
            price_result = get_coin_price.invoke({"coin_id": coin_id})
            results.append(price_result)
            
            # Get detailed info
            details_result = get_coin_details.invoke({"coin_id": coin_id})
            results.append(details_result)
        
        state["market_data"] = "\n".join(results)
        state["messages"] = [f"Market Agent: Fetched data for {coin_id}"]
        
    except Exception as e:
        state["market_data"] = f"Market Agent Error: {str(e)}"
        state["messages"] = [f"Market Agent: Error - {str(e)}"]
    
    return state


# -----------------------------
# News Agent
# -----------------------------

def news_agent(state: AgentState) -> AgentState:
    """
    Fetches news using RSS feed tools.
    Always runs in parallel architecture.
    """
    if state["step_count"] >= MAX_STEPS:
        return state
    
    state["step_count"] = state["step_count"] + 1
    
    coin_id = state["coin_id"]
    
    try:
        if coin_id == "general":
            news_result = get_general_crypto_news.invoke({})
        else:
            news_result = get_crypto_news.invoke({"coin_name": coin_id})
        
        state["news_data"] = news_result
        state["messages"] = [f"News Agent: Fetched news for {coin_id}"]
        
    except Exception as e:
        state["news_data"] = f"News Agent Error: {str(e)}"
        state["messages"] = [f"News Agent: Error - {str(e)}"]
    
    return state


# -----------------------------
# Knowledge Agent
# -----------------------------

def knowledge_agent(state: AgentState) -> AgentState:
    """
    Fetches educational information using Wikipedia tools.
    Always runs in parallel architecture.
    """
    if state["step_count"] >= MAX_STEPS:
        return state
    
    state["step_count"] = state["step_count"] + 1
    
    coin_id = state["coin_id"]
    
    if coin_id == "general":
        state["knowledge_data"] = "General query - no specific coin knowledge needed."
        return state
    
    try:
        # Get Wikipedia summary
        wiki_result = get_wiki_summary.invoke({"topic": coin_id})
        
        # Get history
        history_result = get_crypto_history.invoke({"coin_name": coin_id})
        
        state["knowledge_data"] = f"{wiki_result}\n\n{history_result}"
        state["messages"] = [f"Knowledge Agent: Fetched info for {coin_id}"]
        
    except Exception as e:
        state["knowledge_data"] = f"Knowledge Agent Error: {str(e)}"
        state["messages"] = [f"Knowledge Agent: Error - {str(e)}"]
    
    return state


# -----------------------------
# Analyst Agent
# -----------------------------

def analyst_agent(state: AgentState) -> AgentState:
    """
    Synthesizes all gathered data into a comprehensive intelligence report.
    Detects conflicts, generates confidence scores, and produces structured output.
    """
    if state["step_count"] >= MAX_STEPS:
        state["final_report"] = "Analysis aborted due to step limit."
        return state
    
    state["step_count"] = state["step_count"] + 1
    
    llm = get_llm()
    
    system_prompt = """You are the Analyst Agent for CryptoSense, a crypto intelligence system.

Your job is to synthesize data from multiple sources and create a comprehensive intelligence report.

Guidelines:
1. Cross-reference market data with news sentiment
2. Identify any conflicting signals (e.g., price up but negative news)
3. Provide a confidence score (Low/Medium/High)
4. Generate actionable insights
5. Keep the report concise but informative

Format your response as:
═══════════════════════════════════════
     CRYPTOSENSE INTELLIGENCE REPORT
═══════════════════════════════════════

📊 MARKET SNAPSHOT
[Summarize key market metrics]

📰 NEWS DIGEST
[Summarize news sentiment and key stories]

📚 BACKGROUND BRIEF
[Key educational points]

🎯 ANALYSIS & SIGNALS
[Your synthesis and key observations]
[Note any conflicting signals]

📈 SENTIMENT: [Bullish/Bearish/Neutral]
🔒 CONFIDENCE: [Low/Medium/High]

⚠️ RISK FACTORS
[List key risks]

═══════════════════════════════════════
"""
    
    # Compile all data
    context = f"""
USER QUERY: {state['query']}
COIN: {state['coin_id']}

--- MARKET DATA ---
{state.get('market_data', 'No market data available')}

--- NEWS DATA ---
{state.get('news_data', 'No news data available')}

--- KNOWLEDGE DATA ---
{state.get('knowledge_data', 'No knowledge data available')}
"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=context)
    ]
    
    try:
        response = llm.invoke(messages)
        state["final_report"] = response.content
        state["messages"] = ["Analyst Agent: Generated intelligence report"]
        
    except Exception as e:
        state["final_report"] = f"Analysis Error: {str(e)}"
        state["messages"] = [f"Analyst Agent: Error - {str(e)}"]
    
    return state


# -----------------------------
# Router Functions
# -----------------------------

def should_continue(state: AgentState) -> Literal["continue", "end"]:
    """Determine if workflow should continue or end."""
    if state.get("error"):
        return "end"
    if state["step_count"] >= MAX_STEPS:
        return "end"
    return "continue"


def route_after_orchestrator(state: AgentState) -> Literal["market", "news", "knowledge", "analyst"]:
    """Route to first appropriate agent after orchestration."""
    tasks = state.get("tasks", [])
    
    if "market" in tasks:
        return "market"
    elif "news" in tasks:
        return "news"
    elif "knowledge" in tasks:
        return "knowledge"
    else:
        return "analyst"
