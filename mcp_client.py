"""
CryptoSense MCP Client
========================
Connects to a RUNNING CryptoSense MCP Server via SSE transport and
orchestrates crypto intelligence queries using Groq LLM with tool calling.

Architecture:
  1. Start MCP Server:  python mcp_server.py --transport sse
  2. Start Gradio:      python gradio_app.py
  3. Gradio → MCP Client → SSE → MCP Server → Tools → APIs

If the MCP server is not running, the client will return an error.
"""

import os
import sys
import json
import time
import asyncio
from typing import Any, Optional

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

load_dotenv()

# Default MCP Server URL (SSE transport)
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/sse")


# ═══════════════════════════════════════════
# 1. MCP Client Core
# ═══════════════════════════════════════════

class CryptoSenseMCPClient:
    """
    MCP Client that connects to a running MCP Server via SSE:
    1. Connects to MCP Server at the configured URL
    2. Discovers available tools via MCP protocol
    3. Uses Groq LLM with tool calling to orchestrate queries
    4. Calls tools through MCP and synthesizes a final report
    
    The server MUST be running before using this client.
    """

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.tools: list = []
        self._groq_tools: list = []  # Groq-compatible tool schemas

    async def connect(self, read_stream, write_stream):
        """Initialize the MCP session."""
        self.session = ClientSession(read_stream, write_stream)
        await self.session.initialize()

        # Discover tools
        tools_result = await self.session.list_tools()
        self.tools = tools_result.tools
        self._groq_tools = self._convert_tools_for_groq()

    def _convert_tools_for_groq(self) -> list:
        """Convert MCP tool schemas to Groq/OpenAI function-calling format."""
        groq_tools = []
        for tool in self.tools:
            func_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}},
                },
            }
            groq_tools.append(func_def)
        return groq_tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call an MCP tool and return the text result."""
        result = await self.session.call_tool(name, arguments)
        # Extract text from content blocks
        texts = []
        for block in result.content:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts) if texts else str(result.content)

    async def get_resource(self, uri: str) -> str:
        """Read an MCP resource."""
        from pydantic import AnyUrl
        result = await self.session.read_resource(AnyUrl(uri))
        texts = []
        for block in result.contents:
            if hasattr(block, "text"):
                texts.append(block.text)
        return "\n".join(texts) if texts else str(result.contents)

    async def get_prompt(self, name: str, arguments: dict) -> str:
        """Get an MCP prompt."""
        result = await self.session.get_prompt(name, arguments)
        texts = []
        for msg in result.messages:
            if hasattr(msg.content, "text"):
                texts.append(msg.content.text)
            elif isinstance(msg.content, str):
                texts.append(msg.content)
        return "\n".join(texts) if texts else str(result.messages)

    async def query(self, user_query: str) -> dict:
        """
        Run a full intelligence query:
        1. Send query + tool definitions to Groq LLM
        2. Execute tool calls via MCP
        3. Feed results back to LLM for synthesis
        4. Return structured result with report + metrics
        """
        from groq import AsyncGroq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return {"report": "Error: GROQ_API_KEY not set in .env", "metrics": {}}

        client = AsyncGroq(api_key=api_key)
        model = "llama-3.3-70b-versatile"

        start_time = time.time()
        tool_calls_log = []
        total_tokens = 0
        llm_calls = 0

        system_prompt = (
            "You are CryptoSense, a multi-agent crypto intelligence system.\n"
            "You have access to tools for fetching live market data, news, and educational information.\n\n"
            "For any crypto query:\n"
            "1. Call relevant tools to gather data (market prices, news, wiki info)\n"
            "2. For a specific coin: call get_coin_price, get_coin_details, get_crypto_news, get_wiki_summary\n"
            "3. For general queries: call get_trending_coins or get_general_crypto_news\n"
            "4. After gathering data, synthesize a comprehensive intelligence report\n\n"
            "Format your final report as:\n"
            "═══════════════════════════════════════\n"
            "     CRYPTOSENSE INTELLIGENCE REPORT\n"
            "═══════════════════════════════════════\n"
            "📊 MARKET SNAPSHOT\n"
            "📰 NEWS DIGEST\n"
            "📚 BACKGROUND BRIEF\n"
            "🎯 ANALYSIS & SIGNALS\n"
            "📈 SENTIMENT: [Bullish/Bearish/Neutral]\n"
            "🔒 CONFIDENCE: [Low/Medium/High]\n"
            "⚠️ RISK FACTORS\n"
            "═══════════════════════════════════════"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]

        # Agent loop: LLM decides which tools to call
        max_iterations = 10
        for _ in range(max_iterations):
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                tools=self._groq_tools if self._groq_tools else None,
                tool_choice="auto",
                max_tokens=1024,
                temperature=0,
            )
            llm_calls += 1
            total_tokens += response.usage.total_tokens if response.usage else 0

            msg = response.choices[0].message

            # If no tool calls, LLM has given the final answer
            if not msg.tool_calls:
                messages.append({"role": "assistant", "content": msg.content or ""})
                break

            # Process tool calls
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                tool_start = time.time()
                try:
                    result = await self.call_tool(tool_name, args)
                    tool_calls_log.append({
                        "tool": tool_name,
                        "args": args,
                        "latency_ms": round((time.time() - tool_start) * 1000, 2),
                        "error": None,
                    })
                except Exception as e:
                    result = f"Tool error: {e}"
                    tool_calls_log.append({
                        "tool": tool_name,
                        "args": args,
                        "latency_ms": round((time.time() - tool_start) * 1000, 2),
                        "error": str(e),
                    })

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        total_latency_ms = round((time.time() - start_time) * 1000, 2)

        # Extract final report
        final_content = ""
        for m in reversed(messages):
            if m["role"] == "assistant" and m.get("content"):
                final_content = m["content"]
                break

        metrics = {
            "total_latency_ms": total_latency_ms,
            "llm_calls": llm_calls,
            "total_tokens": total_tokens,
            "tool_calls": len(tool_calls_log),
            "tool_errors": sum(1 for t in tool_calls_log if t["error"]),
            "tools_invoked": [t["tool"] for t in tool_calls_log],
            "tool_details": tool_calls_log,
        }

        return {"report": final_content, "metrics": metrics}


# ═══════════════════════════════════════════
# 2. High-Level Runner (SSE Transport)
# ═══════════════════════════════════════════

async def _run_query_async(query: str, server_url: str = MCP_SERVER_URL) -> dict:
    """
    Connect to a running MCP Server via SSE, run the query, disconnect.
    Raises ConnectionError if the server is not reachable.
    """
    try:
        async with sse_client(url=server_url, timeout=5) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                client = CryptoSenseMCPClient()
                client.session = session
                tools_result = await session.list_tools()
                client.tools = tools_result.tools
                client._groq_tools = client._convert_tools_for_groq()

                result = await client.query(query)
                return result
    except (ConnectionError, OSError) as e:
        return {
            "report": f"❌ MCP Server is not running!\n\nStart it first:\n  python mcp_server.py --transport sse\n\nServer URL: {server_url}",
            "metrics": _empty_metrics(),
        }
    except BaseExceptionGroup as eg:
        # SSE client may wrap connection errors in ExceptionGroup
        for exc in eg.exceptions:
            if isinstance(exc, (ConnectionError, OSError)):
                return {
                    "report": f"❌ MCP Server is not running!\n\nStart it first:\n  python mcp_server.py --transport sse\n\nServer URL: {server_url}",
                    "metrics": _empty_metrics(),
                }
        raise


def _empty_metrics() -> dict:
    return {
        "total_latency_ms": 0,
        "llm_calls": 0,
        "total_tokens": 0,
        "tool_calls": 0,
        "tool_errors": 0,
        "tools_invoked": [],
        "tool_details": [],
    }


def run_query(query: str, server_url: str = MCP_SERVER_URL) -> dict:
    """
    Synchronous entry point: connects to a running MCP server via SSE.
    
    Args:
        query: User's crypto question
        server_url: MCP Server SSE endpoint (default: http://127.0.0.1:8000/sse)
    
    Returns:
        dict with keys: "report", "metrics"
        If server is down, report contains an error message.
    """
    try:
        return asyncio.run(_run_query_async(query, server_url))
    except BaseException as e:
        # Check if this is a connection-related error (possibly wrapped in ExceptionGroup)
        if _is_connection_error(e):
            return {
                "report": (
                    "❌ **MCP Server is not running!**\n\n"
                    "Start the server first:\n"
                    "```\npython mcp_server.py --transport sse\n```\n\n"
                    f"Server URL: {server_url}"
                ),
                "metrics": _empty_metrics(),
            }
        return {
            "report": f"❌ Error: {e}",
            "metrics": _empty_metrics(),
        }


def _is_connection_error(exc: BaseException) -> bool:
    """Check if an exception (possibly wrapped in ExceptionGroup) is connection-related."""
    if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
        return True
    err_str = str(exc).lower()
    if any(kw in err_str for kw in ("connect", "refused", "timeout", "unreachable", "taskgroup")):
        return True
    # Unwrap ExceptionGroups
    if isinstance(exc, BaseExceptionGroup):
        return any(_is_connection_error(sub) for sub in exc.exceptions)
    if hasattr(exc, "__cause__") and exc.__cause__:
        return _is_connection_error(exc.__cause__)
    return False


def check_server(server_url: str = MCP_SERVER_URL) -> bool:
    """Check if the MCP server is reachable."""
    import httpx
    try:
        with httpx.Client(timeout=3) as client:
            resp = client.get(server_url.replace("/sse", "/"))
            return resp.status_code < 500
    except Exception:
        return False


# ═══════════════════════════════════════════
# 3. CLI for quick testing
# ═══════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    else:
        q = "Tell me about Bitcoin"

    print(f"\n🔮 CryptoSense MCP Client")
    print(f"Server: {MCP_SERVER_URL}")

    if not check_server():
        print(f"\n❌ MCP Server is NOT running at {MCP_SERVER_URL}")
        print(f"Start it first:  python mcp_server.py --transport sse\n")
        sys.exit(1)

    print(f"✅ Server connected")
    print(f"Query: {q}\n")

    result = run_query(q)

    print(result["report"])
    print(f"\n--- Metrics ---")
    m = result["metrics"]
    print(f"Latency:     {m['total_latency_ms']} ms")
    print(f"LLM Calls:   {m['llm_calls']}")
    print(f"Tokens:      {m['total_tokens']}")
    print(f"Tool Calls:  {m['tool_calls']}")
    print(f"Tool Errors: {m['tool_errors']}")
    print(f"Tools Used:  {', '.join(m['tools_invoked'])}")
