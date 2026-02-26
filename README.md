# 🔮 CryptoSense

**Multi-Agent Crypto Intelligence System**

AI-powered cryptocurrency analysis using LangGraph, Groq Cloud, and real-time data sources.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run
```bash
# CLI (verbose logging)
python main.py

# Web UI
python gradio_app.py
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE                           │
│                    (CLI / Gradio Web UI)                        │
└─────────────────────┬───────────────────────────────────────────┘
                      │ User Query
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION LAYER                             │
│  • Input sanitization (XSS, SQL injection protection)           │
│  • Rate limiting (20 req/min)                                   │
│  • Output sanitization                                          │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR AGENT                            │
│                  (Master Controller)                            │
│                                                                 │
│  • Parses user intent                                           │
│  • Extracts cryptocurrency identifier                           │
│  • Routes tasks to sub-agents                                   │
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
                           │
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
```

**Flow**: Parallel agent execution with LangGraph state management.

---

## 📦 Project Files

| File | Purpose |
|------|---------|
| `main.py` | CLI with verbose tool logging |
| `gradio_app.py` | Web UI interface |
| `workflow.py` | LangGraph workflow definition |
| `agents.py` | 5 specialized agents |
| `tools.py` | 7 API tools (CoinGecko, RSS, Wikipedia) |
| `state.py` | Workflow state schema |
| `validation.py` | Input/output security layer |

---

## 🔧 Usage Examples

### CLI
```bash
python main.py "What is Bitcoin's price?"
python main.py "Tell me about Ethereum"
```

### Web UI
```bash
python gradio_app.py
# Open http://localhost:7860
```

### Example Queries
- "What is Bitcoin's current price?"
- "Tell me about Ethereum"
- "What's trending in crypto?"
- "Latest crypto news"
- "Give me a full analysis of Solana"

---

## 🛠️ Tools & APIs

**No API keys needed** for data sources:

| Tool | Source | Data |
|------|--------|------|
| Market | CoinGecko | Price, volume, market cap, trending |
| News | CoinDesk RSS | Headlines, summaries |
| Knowledge | Wikipedia | History, technology, founders |

**AI Model**: Groq Cloud (Llama 3.3 70B) - requires API key

---

## 🛡️ Security Features

- ✅ Input validation (XSS, SQL injection protection)
- ✅ Output sanitization
- ✅ Rate limiting (20 requests/minute)
- ✅ Step counter (prevents infinite loops)
- ✅ Timeout handling (10s per API call)

---

## 📊 Output Format

```
CRYPTOSENSE INTELLIGENCE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Market Snapshot
📰 News Digest
📚 Background Brief
🎯 Analysis & Signals
📈 Sentiment: Bullish/Bearish/Neutral
🔒 Confidence: Low/Medium/High
⚠️ Risk Factors
```

---

## ⚙️ Configuration

**Adjust in `agents.py`:**
```python
MAX_STEPS = 10        # Prevent infinite loops
max_tokens = 1024     # Cost control
temperature = 0       # Deterministic output
```

---

## 📄 License

MIT License

---

**Built with** LangGraph • Groq • CoinGecko • Wikipedia

⚠️ *For informational purposes only. Not financial advice.*
