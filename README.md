# 🔮 CryptoSense

**Multi-Agent Crypto Intelligence System**

AI-powered cryptocurrency analysis using **LangGraph agents, MCP architecture, Groq Cloud LLMs, and real-time crypto data sources** with **observability and evaluation**.

---

# 🚀 Quick Start

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set API Keys

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key_here

# Langfuse Monitoring
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## 3. Run the System

### Start MCP Server

```bash
python mcp_server.py --transport sse
```

### Start Web Interface

```bash
python gradio_app.py
```

System Flow:

```
Gradio UI
   ↓
MCP Client
   ↓
SSE Transport
   ↓
MCP Server
   ↓
Agent Tools
   ↓
External APIs
```

---

# 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACE                          │
│                (CLI / Gradio Web UI)                        │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                        MCP CLIENT                           │
│     Sends structured requests to MCP server                │
└───────────────────────┬─────────────────────────────────────┘
                        │ SSE Transport
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                        MCP SERVER                           │
│  Exposes tools via Model Context Protocol                  │
│  Handles tool execution                                    │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR AGENT                         │
│                   (LangGraph Controller)                    │
│                                                             │
│ • Parses user intent                                        │
│ • Extracts cryptocurrency identifier                        │
│ • Routes tasks to sub-agents                                │
└─────────────┬───────────────┬───────────────┬────────────────┘
              │               │               │
              ▼               ▼               ▼
┌────────────────┐ ┌────────────────┐ ┌──────────────────────┐
│  MARKET AGENT  │ │   NEWS AGENT   │ │   KNOWLEDGE AGENT    │
│                │ │                │ │                      │
│ CoinGecko API  │ │ CoinDesk RSS   │ │ Wikipedia API        │
│                │ │                │ │                      │
│ • Live prices  │ │ • Headlines    │ │ • Coin history       │
│ • Market cap   │ │ • Summaries    │ │ • Founder info       │
│ • Volume       │ │ • Sentiment    │ │ • Technology details │
│ • Trending     │ │                │ │                      │
└───────┬────────┘ └───────┬────────┘ └──────────┬───────────┘
        │                  │                     │
        └──────────────────┴─────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      ANALYST AGENT                          │
│                 (Reasoning & Synthesis)                     │
│                                                             │
│ • Combines market data + news + knowledge                   │
│ • Detects signal conflicts                                  │
│ • Generates structured intelligence reports                 │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                       OUTPUT LAYER                          │
│                                                             │
│ • Market Snapshot                                           │
│ • News Summary                                              │
│ • Background Brief                                          │
│ • Sentiment Score                                           │
│ • Risk Signals                                              │
│ • Final Intelligence Report                                 │
└─────────────────────────────────────────────────────────────┘
```

---

# 🔍 Observability & Monitoring

CryptoSense integrates **Langfuse** for LLM observability.

Langfuse tracks:

- User queries
- Agent reasoning traces
- Tool calls
- Token usage
- Latency
- Prompt versions

Monitoring pipeline:

```
User Query
   ↓
Agent Execution
   ↓
Langfuse Trace Logging
   ↓
Observability Dashboard
```

This helps debug issues like:

- hallucinations
- incorrect tool calls
- slow responses
- high token costs

---

# 📊 Evaluation

The system integrates **DeepEval** for automated evaluation of agent responses.

Evaluation metrics include:

| Metric | Description |
|------|-------------|
| Task Completion | Whether the agent solved the task |
| Tool Usage Accuracy | Correct tool selection |
| Answer Relevance | Response matches user intent |
| Faithfulness | Output grounded in retrieved data |
| Latency | Time taken per request |

Evaluation workflow:

```
Test Queries
     ↓
Agent Execution
     ↓
DeepEval Evaluation
     ↓
Evaluation Metrics
```

---

## 📦 Project Files

| File | Purpose |
|------|---------|
| `.env.example` | Template for environment setup |
| `evaluation.py` | RAGAS/DeepEval evaluation script |
| `gradio_app.py` | Web UI interface |
| `mcp_client.py` | MCP client for connecting to MCP server |
| `mcp_server.py` | MCP server exposing tools |
| `monitoring.py` | Backend monitoring & metrics logging |
| `validation.py` | Security & input validation layer |

---

# 🛠️ Tools & APIs

| Tool | Source | Data |
|-----|------|------|
| Market Data | CoinGecko API | Price, volume, market cap |
| Crypto News | CoinDesk RSS | Headlines, summaries |
| Knowledge | Wikipedia API | Coin history, technology |

**AI Model**

Groq Cloud  
Model: **Llama 3.3 70B**

---

# 🛡️ Security Features

- Input validation (XSS protection)
- Output sanitization
- Rate limiting (20 requests/min)
- Infinite loop prevention
- API timeout handling
- Structured tool validation

---

# 📊 Output Format

```
CRYPTOSENSE INTELLIGENCE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Market Snapshot
📰 News Digest
📚 Background Brief
🎯 Analysis & Signals
📈 Sentiment: Bullish / Bearish / Neutral
🔒 Confidence Score
⚠️ Risk Factors
```



---

# 📄 License

MIT License

---

**Built with**

LangGraph • MCP • Groq • Langfuse • DeepEval • CoinGecko • Wikipedia

---

⚠️ *For informational purposes only. Not financial advice.*
