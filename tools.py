"""
CryptoSense Tools Module
========================
Contains all tool definitions for the multi-agent system.
Tools: CoinGecko (Market), RSS News, Wikipedia (Knowledge)
No API keys required for these tools.
"""

import requests
import feedparser
from typing import Optional
from langchain_core.tools import tool


# -----------------------------
# 1️⃣ CoinGecko Market Tools
# -----------------------------

@tool
def get_coin_price(coin_id: str) -> str:
    """
    Fetch live price data for a cryptocurrency from CoinGecko.
    Input: coin id like 'bitcoin', 'ethereum', 'solana', 'cardano'.
    Returns: Current price, 24h change, market cap, and volume.
    """
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id.lower().strip(),
            "vs_currencies": "usd",
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if not data or coin_id.lower() not in data:
            return f"No data found for coin: {coin_id}. Try using the coin's full name like 'bitcoin' or 'ethereum'."
        
        coin_data = data[coin_id.lower()]
        
        return f"""
📊 Market Data for {coin_id.upper()}:
• Price: ${coin_data.get('usd', 'N/A'):,.2f}
• 24h Change: {coin_data.get('usd_24h_change', 0):.2f}%
• Market Cap: ${coin_data.get('usd_market_cap', 0):,.0f}
• 24h Volume: ${coin_data.get('usd_24h_vol', 0):,.0f}
"""
    except requests.exceptions.Timeout:
        return f"Timeout fetching data for {coin_id}. Please try again."
    except requests.exceptions.RequestException as e:
        return f"Market API Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool
def get_trending_coins() -> str:
    """
    Fetch top trending cryptocurrencies from CoinGecko.
    No input required.
    Returns: List of currently trending coins.
    """
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "coins" not in data:
            return "Unable to fetch trending coins."
        
        trending = []
        for i, coin in enumerate(data["coins"][:7], 1):
            item = coin.get("item", {})
            trending.append(
                f"{i}. {item.get('name', 'Unknown')} ({item.get('symbol', '?').upper()}) - "
                f"Rank #{item.get('market_cap_rank', 'N/A')}"
            )
        
        return "🔥 Trending Coins:\n" + "\n".join(trending)
        
    except Exception as e:
        return f"Trending API Error: {str(e)}"


@tool
def get_coin_details(coin_id: str) -> str:
    """
    Fetch detailed information about a cryptocurrency from CoinGecko.
    Input: coin id like 'bitcoin', 'ethereum'.
    Returns: Detailed coin information including description, links, and stats.
    """
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id.lower().strip()}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        market = data.get("market_data", {})
        
        return f"""
📈 Detailed Info for {data.get('name', coin_id)}:
• Symbol: {data.get('symbol', 'N/A').upper()}
• Current Price: ${market.get('current_price', {}).get('usd', 'N/A'):,.2f}
• ATH: ${market.get('ath', {}).get('usd', 'N/A'):,.2f}
• ATL: ${market.get('atl', {}).get('usd', 'N/A'):,.2f}
• Circulating Supply: {market.get('circulating_supply', 'N/A'):,.0f}
• Total Supply: {market.get('total_supply', 'N/A') or 'Unlimited'}
• Market Cap Rank: #{data.get('market_cap_rank', 'N/A')}
"""
    except Exception as e:
        return f"Coin Details Error: {str(e)}"


# -----------------------------
# 2️⃣ RSS News Tools
# -----------------------------

@tool
def get_crypto_news(coin_name: str) -> str:
    """
    Fetch latest crypto news related to a coin using CoinDesk RSS feed.
    Input: coin name like 'bitcoin', 'ethereum', 'solana'.
    Returns: Latest news articles related to the coin.
    """
    try:
        feed = feedparser.parse(
            "https://www.coindesk.com/arc/outboundfeeds/rss/"
        )
        
        if not feed.entries:
            return "Unable to fetch news feed."
        
        articles = []
        coin_lower = coin_name.lower().strip()
        
        for entry in feed.entries[:20]:
            title_lower = entry.title.lower()
            summary_lower = entry.get('summary', '').lower()
            
            if coin_lower in title_lower or coin_lower in summary_lower:
                articles.append({
                    "title": entry.title,
                    "summary": entry.get('summary', '')[:200] + "...",
                    "link": entry.link,
                    "published": entry.get('published', 'Unknown date')
                })
        
        if not articles:
            # Return general crypto news if no specific news found
            general_articles = []
            for entry in feed.entries[:3]:
                general_articles.append(f"• {entry.title}")
            return f"No specific news for '{coin_name}'. Latest crypto news:\n" + "\n".join(general_articles)
        
        news_text = f"📰 Latest News for {coin_name.upper()}:\n\n"
        for i, article in enumerate(articles[:5], 1):
            news_text += f"{i}. {article['title']}\n"
            news_text += f"   Published: {article['published']}\n"
            news_text += f"   Summary: {article['summary']}\n\n"
        
        return news_text
        
    except Exception as e:
        return f"RSS News Error: {str(e)}"


@tool
def get_general_crypto_news() -> str:
    """
    Fetch latest general cryptocurrency news from CoinDesk RSS.
    No input required.
    Returns: Top 5 latest crypto news headlines.
    """
    try:
        feed = feedparser.parse(
            "https://www.coindesk.com/arc/outboundfeeds/rss/"
        )
        
        if not feed.entries:
            return "Unable to fetch news feed."
        
        news_text = "📰 Latest Crypto News:\n\n"
        for i, entry in enumerate(feed.entries[:5], 1):
            news_text += f"{i}. {entry.title}\n"
            news_text += f"   Published: {entry.get('published', 'Unknown')}\n\n"
        
        return news_text
        
    except Exception as e:
        return f"General News Error: {str(e)}"


# -----------------------------
# 3️⃣ Wikipedia Knowledge Tools
# -----------------------------

@tool
def get_wiki_summary(topic: str) -> str:
    """
    Fetch Wikipedia summary for a cryptocurrency or blockchain topic.
    Input: topic like 'Bitcoin', 'Ethereum', 'Blockchain', 'DeFi'.
    Returns: Educational summary about the topic.
    """
    try:
        # Clean and format the topic
        formatted_topic = topic.strip().replace(" ", "_")
        
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_topic}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            # Try with cryptocurrency suffix
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_topic}_(cryptocurrency)"
            response = requests.get(url, timeout=10)
        
        response.raise_for_status()
        data = response.json()
        
        if "extract" in data:
            return f"""
📚 Wikipedia Summary - {data.get('title', topic)}:

{data['extract']}

Source: {data.get('content_urls', {}).get('desktop', {}).get('page', 'Wikipedia')}
"""
        
        return f"No Wikipedia summary found for '{topic}'."
        
    except requests.exceptions.RequestException as e:
        return f"Wikipedia Error: {str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"


@tool
def get_crypto_history(coin_name: str) -> str:
    """
    Fetch historical and foundational information about a cryptocurrency.
    Input: coin name like 'Bitcoin', 'Ethereum'.
    Returns: Origin story, founder info, and key milestones.
    """
    try:
        # Try to get the infobox and introduction
        formatted_name = coin_name.strip().replace(" ", "_")
        
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_name}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 404:
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_name}_(cryptocurrency)"
            response = requests.get(url, timeout=10)
        
        response.raise_for_status()
        data = response.json()
        
        if "extract" in data:
            extract = data['extract']
            return f"""
📜 History & Background - {data.get('title', coin_name)}:

{extract}

Type: {data.get('description', 'Cryptocurrency')}
"""
        
        return f"No historical information found for '{coin_name}'."
        
    except Exception as e:
        return f"History Lookup Error: {str(e)}"


# -----------------------------
# Tool Collections by Agent
# -----------------------------

def get_market_tools():
    """Return tools for the Market Agent."""
    return [get_coin_price, get_trending_coins, get_coin_details]


def get_news_tools():
    """Return tools for the News Agent."""
    return [get_crypto_news, get_general_crypto_news]


def get_knowledge_tools():
    """Return tools for the Knowledge Agent."""
    return [get_wiki_summary, get_crypto_history]


def get_all_tools():
    """Return all available tools."""
    return get_market_tools() + get_news_tools() + get_knowledge_tools()
