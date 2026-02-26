"""
CryptoSense - Main Entry Point with Verbose Logging
=====================================================
Shows detailed tool execution, inputs, and outputs.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Color codes for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_banner():
    """Print the CryptoSense banner."""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                      CRYPTOSENSE                              ║
║          Multi-Agent Crypto Intelligence System               ║
╠═══════════════════════════════════════════════════════════════╣
║  Agents: Orchestrator | Market | News | Knowledge | Analyst   ║
║  Data: CoinGecko | RSS News | Wikipedia                       ║
║  AI: Groq Cloud (Llama 3.3 70B)                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.END}
    """)


def log_step(step: str, message: str, color: str = Colors.GREEN):
    """Log a step with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.CYAN}[{timestamp}]{Colors.END} {color}{step}{Colors.END}: {message}")


def log_tool(tool_name: str, search_term: str, source: str):
    """Log tool invocation."""
    print(f"\n{Colors.YELLOW}┌─ TOOL CALL ──────────────────────────────────────┐{Colors.END}")
    print(f"{Colors.YELLOW}│{Colors.END} Tool: {Colors.BOLD}{tool_name}{Colors.END}")
    print(f"{Colors.YELLOW}│{Colors.END} Search: {search_term}")
    print(f"{Colors.YELLOW}│{Colors.END} Source: {source}")
    print(f"{Colors.YELLOW}└──────────────────────────────────────────────────┘{Colors.END}")


def log_tool_output(output: str, max_lines: int = 10):
    """Log tool output."""
    lines = output.strip().split('\n')
    print(f"\n{Colors.GREEN}┌─ TOOL OUTPUT ────────────────────────────────────┐{Colors.END}")
    for i, line in enumerate(lines[:max_lines]):
        print(f"{Colors.GREEN}│{Colors.END} {line[:60]}")
    if len(lines) > max_lines:
        print(f"{Colors.GREEN}│{Colors.END} ... ({len(lines) - max_lines} more lines)")
    print(f"{Colors.GREEN}└──────────────────────────────────────────────────┘{Colors.END}")


def log_agent(agent_name: str, status: str):
    """Log agent status."""
    icon = "🟢" if status == "complete" else "🔄" if status == "running" else "⏳"
    print(f"\n{Colors.BLUE}═══ {icon} {agent_name.upper()} AGENT {status.upper()} ═══{Colors.END}")


def run_verbose_workflow(query: str):
    """Run workflow with verbose logging of each tool call."""
    from validation import validate_input, validate_output
    from tools import (
        get_coin_price, get_trending_coins, get_coin_details,
        get_crypto_news, get_general_crypto_news,
        get_wiki_summary, get_crypto_history
    )
    from agents import get_llm, MAX_STEPS
    from langchain_core.messages import HumanMessage, SystemMessage
    
    print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}   CRYPTOSENSE VERBOSE EXECUTION LOG{Colors.END}")
    print(f"{Colors.HEADER}{'='*60}{Colors.END}")
    
    # Step 1: Input Validation
    log_step("VALIDATION", "Checking user input...")
    is_valid, sanitized_query, error = validate_input(query)
    
    if not is_valid:
        print(f"{Colors.RED}❌ Validation Failed: {error}{Colors.END}")
        return
    
    print(f"   ✓ Input sanitized: '{sanitized_query}'")
    
    # Step 2: Orchestrator Agent
    log_agent("Orchestrator", "running")
    log_step("ORCHESTRATOR", "Parsing user intent and extracting coin...")
    
    llm = get_llm()
    
    system_prompt = """You are the orchestrator for CryptoSense.
Extract: COIN_ID: <coin_id or 'general'>
Tasks: TASKS: <market, news, knowledge>"""
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"User query: {sanitized_query}")
    ]
    
    response = llm.invoke(messages)
    response_text = response.content
    
    # Parse coin and tasks
    coin_id = "bitcoin"
    tasks = ["market", "news", "knowledge"]
    
    normalized = response_text.upper()
    if "COIN_ID:" in normalized:
        start = normalized.find("COIN_ID:") + 8
        end = normalized.find("TASKS:") if "TASKS:" in normalized else len(normalized)
        coin_id = normalized[start:end].split(",")[0].strip().lower()
        coin_id = coin_id.replace("tasks:", "").strip()
    
    if "TASKS:" in normalized:
        start = normalized.find("TASKS:") + 6
        tasks_text = normalized[start:].split("\n")[0]
        parsed = [t.strip().lower() for t in tasks_text.split(",")]
        tasks = [t for t in parsed if t in ["market", "news", "knowledge"]]
    
    log_step("ORCHESTRATOR", f"Identified coin: '{coin_id}'")
    log_step("ORCHESTRATOR", f"Tasks to execute: {tasks}")
    log_agent("Orchestrator", "complete")
    
    # Collect data from each agent
    market_data = ""
    news_data = ""
    knowledge_data = ""
    
    # Step 3: Market Agent
    if "market" in tasks:
        log_agent("Market", "running")
        
        if coin_id == "general":
            log_tool("get_trending_coins", "trending cryptocurrencies", "CoinGecko API")
            try:
                result = get_trending_coins.invoke({})
                market_data = result
                log_tool_output(result)
            except Exception as e:
                log_step("ERROR", f"get_trending_coins failed: {e}", Colors.RED)
        else:
            # Get price
            log_tool("get_coin_price", f"coin_id='{coin_id}'", "CoinGecko API")
            try:
                result = get_coin_price.invoke({"coin_id": coin_id})
                market_data = result
                log_tool_output(result)
            except Exception as e:
                log_step("ERROR", f"get_coin_price failed: {e}", Colors.RED)
            
            # Get details
            log_tool("get_coin_details", f"coin_id='{coin_id}'", "CoinGecko API")
            try:
                result = get_coin_details.invoke({"coin_id": coin_id})
                market_data += "\n" + result
                log_tool_output(result)
            except Exception as e:
                log_step("ERROR", f"get_coin_details failed: {e}", Colors.RED)
        
        log_agent("Market", "complete")
    
    # Step 4: News Agent
    if "news" in tasks:
        log_agent("News", "running")
        
        if coin_id == "general":
            log_tool("get_general_crypto_news", "latest crypto headlines", "CoinDesk RSS")
            try:
                result = get_general_crypto_news.invoke({})
                news_data = result
                log_tool_output(result)
            except Exception as e:
                log_step("ERROR", f"get_general_crypto_news failed: {e}", Colors.RED)
        else:
            log_tool("get_crypto_news", f"coin_name='{coin_id}'", "CoinDesk RSS")
            try:
                result = get_crypto_news.invoke({"coin_name": coin_id})
                news_data = result
                log_tool_output(result)
            except Exception as e:
                log_step("ERROR", f"get_crypto_news failed: {e}", Colors.RED)
        
        log_agent("News", "complete")
    
    # Step 5: Knowledge Agent
    if "knowledge" in tasks and coin_id != "general":
        log_agent("Knowledge", "running")
        
        log_tool("get_wiki_summary", f"topic='{coin_id}'", "Wikipedia API")
        try:
            result = get_wiki_summary.invoke({"topic": coin_id})
            knowledge_data = result
            log_tool_output(result)
        except Exception as e:
            log_step("ERROR", f"get_wiki_summary failed: {e}", Colors.RED)
        
        log_tool("get_crypto_history", f"coin_name='{coin_id}'", "Wikipedia API")
        try:
            result = get_crypto_history.invoke({"coin_name": coin_id})
            knowledge_data += "\n" + result
            log_tool_output(result, max_lines=5)
        except Exception as e:
            log_step("ERROR", f"get_crypto_history failed: {e}", Colors.RED)
        
        log_agent("Knowledge", "complete")
    
    # Step 6: Analyst Agent
    log_agent("Analyst", "running")
    log_step("ANALYST", "Synthesizing all data into intelligence report...")
    
    analyst_prompt = """Create a concise crypto intelligence report with:
- Market Snapshot
- News Summary  
- Background (if available)
- Sentiment (Bullish/Bearish/Neutral)
- Risk Factors"""
    
    context = f"""
Query: {sanitized_query}
Coin: {coin_id}

MARKET DATA:
{market_data or 'No data'}

NEWS DATA:
{news_data or 'No data'}

KNOWLEDGE DATA:
{knowledge_data or 'No data'}
"""
    
    messages = [
        SystemMessage(content=analyst_prompt),
        HumanMessage(content=context)
    ]
    
    try:
        response = llm.invoke(messages)
        final_report = response.content
        
        # Output validation
        log_step("VALIDATION", "Sanitizing LLM output...")
        _, final_report = validate_output(final_report)
        
        log_agent("Analyst", "complete")
        
        # Final Output
        print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
        print(f"{Colors.HEADER}   FINAL INTELLIGENCE REPORT{Colors.END}")
        print(f"{Colors.HEADER}{'='*60}{Colors.END}\n")
        print(final_report)
        print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
        
    except Exception as e:
        log_step("ERROR", f"Analyst failed: {e}", Colors.RED)


def print_help():
    """Print help information."""
    print("""
Commands:
  help  - Show this help
  clear - Clear screen
  exit  - Exit program

Example queries:
  "What is Bitcoin's price?"
  "Tell me about Ethereum"
  "What's trending?"
    """)


def clear_screen():
    """Clear terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def validate_environment():
    """Check for API key."""
    if not os.getenv("GROQ_API_KEY"):
        print(f"{Colors.RED}⚠️  GROQ_API_KEY not found in .env file{Colors.END}")
        return False
    return True


def run_interactive():
    """Run interactive mode."""
    print_banner()
    
    if not validate_environment():
        print("Set GROQ_API_KEY in .env file to continue.\n")
        return
    
    print("Type 'help' for commands or 'exit' to quit.\n")
    
    while True:
        try:
            query = input(f"\n{Colors.CYAN}🔍 Ask about crypto >{Colors.END} ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['exit', 'quit', 'q']:
                print(f"\n{Colors.GREEN}👋 Thanks for using CryptoSense!{Colors.END}\n")
                break
            
            if query.lower() == 'help':
                print_help()
                continue
            
            if query.lower() == 'clear':
                clear_screen()
                print_banner()
                continue
            
            run_verbose_workflow(query)
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.GREEN}👋 Interrupted. Goodbye!{Colors.END}\n")
            break
        except Exception as e:
            print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")


def run_single_query(query: str):
    """Run single query mode."""
    print_banner()
    if validate_environment():
        run_verbose_workflow(query)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_single_query(query)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
