# 🔮 CryptoSense — Multi-Agent Crypto Intelligence System

<p align="center">
  <strong>AI-Powered Cryptocurrency Intelligence Platform</strong>
</p>

<p align="center">
  Built with LangGraph | Groq Cloud (Llama 3.3 70B) | CoinGecko | RSS News | Wikipedia
</p>

---

## 🎯 Overview

CryptoSense is a sophisticated multi-agent AI system that provides comprehensive cryptocurrency intelligence by combining real-time market data, news analysis, and educational content. The system uses LangGraph for orchestrating multiple specialized agents that work together to deliver actionable insights.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                         (CLI / API)                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │ User Query
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                            │
│                  (Master Controller)                            │
│                                                                 │
│  • Parses user intent                                           │
│  • Extracts cryptocurrency identifier                           │
│  • Routes tasks to appropriate agents                           │
│  • Controls workflow execution                                  │
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
│ • % changes    │ │ • Related news │ │ • Educational content  │
│ • Trending     │ │                │ │                        │
└────────┬───────┘ └───────┬────────┘ └──────────┬─────────────┘
         │                 │                      │
         └─────────────────┴──────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYST AGENT                                │
│               (Synthesis & Reasoning Layer)                     │
│                                                                 │
│  • Cross-references market data + news + knowledge              │
│  • Detects conflicting signals                                  │
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
```

## 🛠️ Features

### Multi-Agent System
- **Orchestrator Agent**: Parses user intent and coordinates all agents
- **Market Agent**: Fetches real-time data from CoinGecko
- **News Agent**: Aggregates crypto news via RSS feeds
- **Knowledge Agent**: Provides educational content from Wikipedia
- **Analyst Agent**: Synthesizes all data into actionable intelligence

### Tools (No API Keys Required)
| Tool | Source | Data |
|------|--------|------|
| `get_coin_price` | CoinGecko | Live prices, 24h change, market cap, volume |
| `get_trending_coins` | CoinGecko | Currently trending cryptocurrencies |
| `get_coin_details` | CoinGecko | Detailed coin information, ATH, supply |
| `get_crypto_news` | CoinDesk RSS | News specific to a cryptocurrency |
| `get_general_crypto_news` | CoinDesk RSS | Latest general crypto headlines |
| `get_wiki_summary` | Wikipedia | Educational summaries |
| `get_crypto_history` | Wikipedia | Historical and foundational info |

### System Design Features
- ✅ **Infinite Loop Prevention**: Maximum step counter prevents runaway execution
- ✅ **Cost Efficient**: Limited token usage, efficient tool calling
- ✅ **Error Handling**: Graceful error handling at every layer
- ✅ **Modular Architecture**: Clean separation of concerns
- ✅ **State Management**: LangGraph state tracking throughout workflow

## 📦 Installation

### 1. Clone the Repository
```bash
cd CryptoSense-Multi-Agent-Crypto-Intelligence-System
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
The `.env` file is already configured with your Groq API key.

## 🚀 Usage

### Interactive Mode (CLI)
```bash
python main.py
```

### Single Query Mode
```bash
python main.py "What is Bitcoin's current price?"
```

### Example Queries
- `"What is Ethereum's current price?"`
- `"Tell me about Solana"`
- `"Latest crypto news"`
- `"What's trending in crypto?"`
- `"Give me a full analysis of Cardano"`

## 📁 Project Structure

```
CryptoSense-Multi-Agent-Crypto-Intelligence-System/
├── main.py           # CLI entry point
├── workflow.py       # LangGraph workflow definition
├── agents.py         # Agent implementations
├── state.py          # State schema definitions
├── tools.py          # Tool implementations
├── requirements.txt  # Python dependencies
├── .env              # Environment variables (API keys)
└── README.md         # This file
```

## 🔧 File Descriptions

| File | Description |
|------|-------------|
| `main.py` | Main CLI interface with interactive and single-query modes |
| `workflow.py` | LangGraph workflow definition connecting all agents |
| `agents.py` | All agent implementations (Orchestrator, Market, News, Knowledge, Analyst) |
| `state.py` | TypedDict state schema for the workflow |
| `tools.py` | All tool implementations (CoinGecko, RSS, Wikipedia) |

## ⚙️ Configuration

### Environment Variables
```env
GROQ_API_KEY=your_groq_api_key_here
```

### Model Settings (in agents.py)
```python
ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
    max_tokens=1024  # Adjustable for cost control
)
```

### Safety Settings
```python
MAX_STEPS = 10  # Prevents infinite loops
```

## 📊 Sample Output

```
═══════════════════════════════════════
     CRYPTOSENSE INTELLIGENCE REPORT
═══════════════════════════════════════

📊 MARKET SNAPSHOT
Bitcoin is currently trading at $67,234.50
• 24h Change: +2.34%
• Market Cap: $1.32T
• 24h Volume: $28.5B

📰 NEWS DIGEST
Recent news sentiment: Neutral to Bullish
• Bitcoin ETF inflows continue strong momentum
• Institutional adoption growing

📚 BACKGROUND BRIEF
Bitcoin is a decentralized digital currency created in 2009 
by Satoshi Nakamoto. It operates on blockchain technology...

🎯 ANALYSIS & SIGNALS
Market indicators show continued strength with healthy volume.
No significant conflicting signals detected.

📈 SENTIMENT: Bullish
🔒 CONFIDENCE: Medium

⚠️ RISK FACTORS
• Market volatility remains high
• Regulatory uncertainty in some regions

═══════════════════════════════════════
```

## 🛡️ Safety Features

1. **Step Limiting**: Maximum 10 steps per query to prevent infinite loops
2. **Timeout Handling**: API calls have 10-second timeouts
3. **Error Recovery**: Graceful handling of API failures
4. **Token Limits**: Max tokens per LLM call for cost control

## 🤝 Contributing

Feel free to submit issues and pull requests!

## 📄 License

MIT License - see LICENSE file for details.

---

<p align="center">
  Built with ❤️ using LangGraph, Groq Cloud, and open APIs
</p>
