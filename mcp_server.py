"""
CryptoSense MCP Server
========================
Exposes CryptoSense as a Model Context Protocol (MCP) server using the
official `mcp` SDK (FastMCP).

Capabilities:
─────────────
Tools (7):
  • get_coin_price        – Live price, 24h change, market cap, volume
  • get_trending_coins    – Top trending coins from CoinGecko
  • get_coin_details      – Detailed stats (ATH, ATL, supply, rank)
  • get_crypto_news       – Coin-specific news via CoinDesk RSS
  • get_general_crypto_news – Latest crypto headlines
  • get_wiki_summary      – Wikipedia summary for any crypto topic
  • get_crypto_history    – Historical / foundational info

Resources (2):
  • cryptosense://status          – System health & monitoring status
  • cryptosense://dashboard       – Aggregate metrics & evaluation dashboard

Prompts (2):
  • crypto_analysis   – Full multi-agent intelligence report for a coin
  • quick_price       – Quick price check for a coin

Transports:
  • stdio   (default) – for Claude Desktop / VS Code / CLI
  • SSE     – for web clients
  • Streamable HTTP   – modern MCP transport

Usage:
  python mcp_server.py                    # stdio (default)
  python mcp_server.py --transport sse    # SSE on http://127.0.0.1:8000/sse
  python mcp_server.py --transport http   # Streamable HTTP on http://127.0.0.1:8000/mcp
"""

import os
import sys
import argparse
import requests
import feedparser
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

load_dotenv()

# ═══════════════════════════════════════════
# 1. Initialize FastMCP Server
# ═══════════════════════════════════════════

mcp = FastMCP(
    name="CryptoSense",
    instructions="""CryptoSense is a multi-agent crypto intelligence system.
You can use the available tools to fetch live market data, news, and
educational information about any cryptocurrency. Use the crypto_analysis
prompt for a full intelligence report, or call individual tools for
specific data points.""",
    host="127.0.0.1",
    port=8000,
)


# ═══════════════════════════════════════════
# 2. Tools – Market Data (CoinGecko)
# ═══════════════════════════════════════════

@mcp.tool()
def get_coin_price(coin_id: str) -> str:
    """Fetch live price data for a cryptocurrency from CoinGecko.
    
    Args:
        coin_id: Coin identifier like 'bitcoin', 'ethereum', 'solana', 'cardano'.
    
    Returns:
        Current price, 24h change, market cap, and volume.
    """
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id.lower().strip(),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data or coin_id.lower() not in data:
            return f"No data found for coin: {coin_id}. Try the full name like 'bitcoin' or 'ethereum'."

        d = data[coin_id.lower()]
        return (
            f"📊 Market Data for {coin_id.upper()}:\n"
            f"• Price: ${d.get('usd', 'N/A'):,.2f}\n"
            f"• 24h Change: {d.get('usd_24h_change', 0):.2f}%\n"
            f"• Market Cap: ${d.get('usd_market_cap', 0):,.0f}\n"
            f"• 24h Volume: ${d.get('usd_24h_vol', 0):,.0f}"
        )
    except requests.exceptions.Timeout:
        return f"Timeout fetching data for {coin_id}. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Market API Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def get_trending_coins() -> str:
    """Fetch the top trending cryptocurrencies from CoinGecko.
    
    Returns:
        List of currently trending coins with name, symbol, and rank.
    """
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "coins" not in data:
            return "Unable to fetch trending coins."

        lines = []
        for i, coin in enumerate(data["coins"][:7], 1):
            item = coin.get("item", {})
            lines.append(
                f"{i}. {item.get('name', 'Unknown')} "
                f"({item.get('symbol', '?').upper()}) – "
                f"Rank #{item.get('market_cap_rank', 'N/A')}"
            )
        return "🔥 Trending Coins:\n" + "\n".join(lines)
    except Exception as e:
        return f"Trending API Error: {e}"


@mcp.tool()
def get_coin_details(coin_id: str) -> str:
    """Fetch detailed information about a cryptocurrency from CoinGecko.
    
    Args:
        coin_id: Coin identifier like 'bitcoin', 'ethereum'.
    
    Returns:
        Detailed stats including ATH, ATL, supply, and rank.
    """
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower().strip()}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        m = data.get("market_data", {})

        return (
            f"📈 Detailed Info for {data.get('name', coin_id)}:\n"
            f"• Symbol: {data.get('symbol', 'N/A').upper()}\n"
            f"• Current Price: ${m.get('current_price', {}).get('usd', 'N/A'):,.2f}\n"
            f"• ATH: ${m.get('ath', {}).get('usd', 'N/A'):,.2f}\n"
            f"• ATL: ${m.get('atl', {}).get('usd', 'N/A'):,.2f}\n"
            f"• Circulating Supply: {m.get('circulating_supply', 'N/A'):,.0f}\n"
            f"• Total Supply: {m.get('total_supply', 'N/A') or 'Unlimited'}\n"
            f"• Market Cap Rank: #{data.get('market_cap_rank', 'N/A')}"
        )
    except Exception as e:
        return f"Coin Details Error: {e}"


# ═══════════════════════════════════════════
# 3. Tools – News (CoinDesk RSS)
# ═══════════════════════════════════════════

@mcp.tool()
def get_crypto_news(coin_name: str) -> str:
    """Fetch latest crypto news related to a specific coin via CoinDesk RSS.
    
    Args:
        coin_name: Coin name like 'bitcoin', 'ethereum', 'solana'.
    
    Returns:
        News articles matching the coin, or general headlines if none found.
    """
    try:
        feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
        if not feed.entries:
            return "Unable to fetch news feed."

        coin_lower = coin_name.lower().strip()
        articles = []
        for entry in feed.entries[:20]:
            if coin_lower in entry.title.lower() or coin_lower in entry.get("summary", "").lower():
                articles.append(
                    f"• {entry.title}\n"
                    f"  Published: {entry.get('published', 'Unknown')}\n"
                    f"  {entry.get('summary', '')[:200]}..."
                )

        if not articles:
            general = [f"• {e.title}" for e in feed.entries[:3]]
            return f"No specific news for '{coin_name}'. Latest headlines:\n" + "\n".join(general)

        return f"📰 News for {coin_name.upper()}:\n\n" + "\n\n".join(articles[:5])
    except Exception as e:
        return f"RSS News Error: {e}"


@mcp.tool()
def get_general_crypto_news() -> str:
    """Fetch the latest general cryptocurrency news headlines from CoinDesk RSS.
    
    Returns:
        Top 5 latest crypto news headlines.
    """
    try:
        feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
        if not feed.entries:
            return "Unable to fetch news feed."

        lines = []
        for i, entry in enumerate(feed.entries[:5], 1):
            lines.append(f"{i}. {entry.title}\n   Published: {entry.get('published', 'Unknown')}")
        return "📰 Latest Crypto News:\n\n" + "\n\n".join(lines)
    except Exception as e:
        return f"General News Error: {e}"


# ═══════════════════════════════════════════
# 4. Tools – Knowledge (Wikipedia)
# ═══════════════════════════════════════════

@mcp.tool()
def get_wiki_summary(topic: str) -> str:
    """Fetch a Wikipedia summary for a cryptocurrency or blockchain topic.
    
    Args:
        topic: Topic like 'Bitcoin', 'Ethereum', 'Blockchain', 'DeFi'.
    
    Returns:
        Educational summary from Wikipedia.
    """
    try:
        formatted = topic.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted}"
        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted}_(cryptocurrency)"
            response = requests.get(url, timeout=10)

        response.raise_for_status()
        data = response.json()

        if "extract" in data:
            source = data.get("content_urls", {}).get("desktop", {}).get("page", "Wikipedia")
            return (
                f"📚 Wikipedia – {data.get('title', topic)}:\n\n"
                f"{data['extract']}\n\n"
                f"Source: {source}"
            )
        return f"No Wikipedia summary found for '{topic}'."
    except requests.exceptions.RequestException as e:
        return f"Wikipedia Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


@mcp.tool()
def get_crypto_history(coin_name: str) -> str:
    """Fetch historical and foundational information about a cryptocurrency.
    
    Args:
        coin_name: Coin name like 'Bitcoin', 'Ethereum'.
    
    Returns:
        Origin story, founder info, and background.
    """
    try:
        formatted = coin_name.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted}"
        response = requests.get(url, timeout=10)

        if response.status_code == 404:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted}_(cryptocurrency)"
            response = requests.get(url, timeout=10)

        response.raise_for_status()
        data = response.json()

        if "extract" in data:
            return (
                f"📜 History – {data.get('title', coin_name)}:\n\n"
                f"{data['extract']}\n\n"
                f"Type: {data.get('description', 'Cryptocurrency')}"
            )
        return f"No historical info found for '{coin_name}'."
    except Exception as e:
        return f"History Lookup Error: {e}"


# ═══════════════════════════════════════════
# 5. Resources
# ═══════════════════════════════════════════

@mcp.resource("cryptosense://status")
def system_status() -> str:
    """Current system health and monitoring status."""
    try:
        from monitoring import is_monitoring_enabled, metrics_store
        langfuse = "Connected" if is_monitoring_enabled() else "Disabled"
        agg = metrics_store.get_aggregate()
        return (
            f"CryptoSense System Status\n"
            f"═════════════════════════\n"
            f"Langfuse Monitoring: {langfuse}\n"
            f"Total Queries: {agg['total_queries']}\n"
            f"Avg Latency: {agg['avg_latency_ms']:.0f} ms\n"
            f"Success Rate: {agg['success_rate']:.1f}%\n"
            f"APIs: CoinGecko ✅ | CoinDesk RSS ✅ | Wikipedia ✅"
        )
    except Exception:
        return "CryptoSense System Status\n═════════════════════════\nStatus: Running\nAPIs: CoinGecko ✅ | CoinDesk RSS ✅ | Wikipedia ✅"


@mcp.resource("cryptosense://dashboard")
def monitoring_dashboard() -> str:
    """Aggregate monitoring metrics and evaluation dashboard."""
    try:
        from monitoring import metrics_store
        from evaluation import evaluation_store

        mon = metrics_store.get_aggregate()
        ev = evaluation_store.get_aggregate()
        breakdown = evaluation_store.get_metric_breakdown()

        lines = [
            "CryptoSense Dashboard",
            "═" * 50,
            f"\n📊 Monitoring ({mon['total_queries']} queries)",
            f"  Avg Latency:  {mon['avg_latency_ms']:.0f} ms",
            f"  Avg Tokens:   {mon['avg_tokens']:.0f}",
            f"  Avg Steps:    {mon['avg_steps']:.1f}",
            f"  Success Rate: {mon['success_rate']:.1f}%",
            f"\n🎯 Evaluation ({ev['total_evals']} evals)",
            f"  Avg Score:    {ev['avg_score']:.2%}",
            f"  Pass Rate:    {ev['pass_rate']:.1f}%",
        ]
        if breakdown:
            lines.append(f"\n📈 Metric Breakdown")
            lines.append(f"{'Metric':<25} {'Avg':<8} {'Min':<8} {'Max':<8}")
            lines.append("─" * 50)
            for name, data in breakdown.items():
                lines.append(f"{name:<25} {data['avg_score']:<8.2f} {data['min_score']:<8.2f} {data['max_score']:<8.2f}")
        return "\n".join(lines)
    except Exception:
        return "Dashboard: No data yet. Run some queries first."


# ═══════════════════════════════════════════
# 6. Prompts
# ═══════════════════════════════════════════

@mcp.prompt()
def crypto_analysis(coin: str) -> str:
    """Generate a full multi-agent intelligence report for a cryptocurrency.
    
    Args:
        coin: The cryptocurrency to analyze (e.g. 'bitcoin', 'ethereum').
    """
    return (
        f"Please provide a comprehensive crypto intelligence report for {coin}. "
        f"Use the following tools in order:\n\n"
        f"1. Call get_coin_price with coin_id='{coin}' for live market data\n"
        f"2. Call get_coin_details with coin_id='{coin}' for detailed stats\n"
        f"3. Call get_crypto_news with coin_name='{coin}' for latest news\n"
        f"4. Call get_wiki_summary with topic='{coin}' for background info\n\n"
        f"Then synthesize all data into a structured report with:\n"
        f"• Market Snapshot (price, change, volume, cap)\n"
        f"• News Digest (sentiment & key stories)\n"
        f"• Background Brief (origin, tech, use case)\n"
        f"• Analysis & Signals (cross-reference data, conflicts)\n"
        f"• Sentiment: Bullish/Bearish/Neutral\n"
        f"• Confidence: Low/Medium/High\n"
        f"• Risk Factors"
    )


@mcp.prompt()
def quick_price(coin: str) -> str:
    """Quick price check for a cryptocurrency.
    
    Args:
        coin: The cryptocurrency to check (e.g. 'bitcoin', 'ethereum').
    """
    return f"Use the get_coin_price tool with coin_id='{coin}' and report the current price, 24h change, and volume."


# ═══════════════════════════════════════════
# 7. Run Server
# ═══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="CryptoSense MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host for SSE/HTTP (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port for SSE/HTTP (default: 8000)")
    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port

    if args.transport == "stdio":
        print("🔮 CryptoSense MCP Server starting (stdio)...", file=sys.stderr)
        mcp.run(transport="stdio")
    elif args.transport == "sse":
        print(f"🔮 CryptoSense MCP Server starting (SSE) → http://{args.host}:{args.port}/sse", file=sys.stderr)
        mcp.run(transport="sse")
    elif args.transport == "http":
        print(f"🔮 CryptoSense MCP Server starting (Streamable HTTP) → http://{args.host}:{args.port}/mcp", file=sys.stderr)
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
