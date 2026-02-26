"""
CryptoSense Gradio UI - Clean Version
======================================
Minimalist web interface for the multi-agent system.
"""

import gradio as gr
from workflow import run_query_with_trace
from validation import validate_input, validate_output, rate_limiter
from tools import (
    get_coin_price,
    get_trending_coins,
    get_crypto_news,
    get_general_crypto_news
)


def process_query(query: str):
    """Process user query with validation."""
    
    # Rate limiting check
    if not rate_limiter.is_allowed():
        wait_time = rate_limiter.get_wait_time()
        return f"⏳ Rate limit reached. Please wait {wait_time} seconds.", ""
    
    # Input validation
    is_valid, sanitized_query, error = validate_input(query)
    if not is_valid:
        return f"❌ {error}", ""
    
    try:
        # Run multi-agent workflow
        report, trace = run_query_with_trace(sanitized_query)
        
        # Output validation
        _, sanitized_report = validate_output(report)
        
        # Format trace info
        trace_text = format_trace(trace)
        
        return sanitized_report, trace_text
        
    except Exception as e:
        return f"❌ Error: {str(e)}", ""


def format_trace(trace: dict) -> str:
    """Format trace information cleanly."""
    lines = [
        "─" * 40,
        "EXECUTION TRACE",
        "─" * 40,
        f"Coin: {trace.get('coin_identified', 'N/A')}",
        f"Tasks: {', '.join(trace.get('tasks_executed', []))}",
        f"Steps: {trace.get('step_count', 0)}",
        "",
        "Agent Flow:",
    ]
    
    for msg in trace.get('messages', []):
        lines.append(f"  → {msg}")
    
    if trace.get('error'):
        lines.append(f"\n⚠️ Error: {trace['error']}")
    
    lines.append("─" * 40)
    return "\n".join(lines)


def quick_price(coin: str):
    """Get quick price for a coin."""
    is_valid, sanitized, error = validate_input(coin)
    if not is_valid:
        return f"❌ {error}"
    
    try:
        result = get_coin_price.invoke({"coin_id": sanitized.lower()})
        _, sanitized_result = validate_output(result)
        return sanitized_result
    except Exception as e:
        return f"❌ Error: {str(e)}"


def quick_trending():
    """Get trending coins."""
    try:
        result = get_trending_coins.invoke({})
        _, sanitized_result = validate_output(result)
        return sanitized_result
    except Exception as e:
        return f"❌ Error: {str(e)}"


def quick_news():
    """Get latest news."""
    try:
        result = get_general_crypto_news.invoke({})
        _, sanitized_result = validate_output(result)
        return sanitized_result
    except Exception as e:
        return f"❌ Error: {str(e)}"


def create_ui():
    """Create clean Gradio UI."""
    
    with gr.Blocks(title="CryptoSense") as app:
        
        # Header
        gr.Markdown("""
        # 🔮 CryptoSense
        **Multi-Agent Crypto Intelligence System**
        
        *Powered by LangGraph • Groq Cloud • CoinGecko • Wikipedia*
        """)
        
        gr.Markdown("---")
        
        # Main Query Section
        with gr.Row():
            with gr.Column(scale=4):
                query_input = gr.Textbox(
                    label="Ask about cryptocurrency",
                    placeholder="e.g., Tell me about Bitcoin, What's Ethereum's price?",
                    lines=2
                )
            with gr.Column(scale=1):
                submit_btn = gr.Button("🚀 Analyze", variant="primary", size="lg")
        
        # Quick Actions
        gr.Markdown("**Quick Actions:**")
        with gr.Row():
            btn_btc = gr.Button("₿ Bitcoin", size="sm")
            btn_eth = gr.Button("Ξ Ethereum", size="sm")
            btn_sol = gr.Button("◎ Solana", size="sm")
            btn_trend = gr.Button("🔥 Trending", size="sm")
            btn_news = gr.Button("📰 News", size="sm")
        
        gr.Markdown("---")
        
        # Output Section
        report_output = gr.Textbox(
            label="Intelligence Report",
            lines=18,
            interactive=False
        )
        
        with gr.Accordion("📋 Execution Trace", open=False):
            trace_output = gr.Textbox(
                label="Agent Workflow",
                lines=10,
                interactive=False
            )
        
        gr.Markdown("---")
        
        # Quick Tools Section
        with gr.Accordion("⚡ Quick Tools", open=False):
            with gr.Row():
                with gr.Column():
                    price_coin = gr.Dropdown(
                        label="Price Check",
                        choices=["bitcoin", "ethereum", "solana", "cardano", "ripple", "dogecoin"],
                        value="bitcoin"
                    )
                    price_btn = gr.Button("Check Price")
                    price_output = gr.Textbox(label="Result", lines=5, interactive=False)
                
                with gr.Column():
                    trend_btn = gr.Button("Get Trending Coins")
                    trend_output = gr.Textbox(label="Trending", lines=5, interactive=False)
                
                with gr.Column():
                    news_btn = gr.Button("Get Latest News")
                    news_output = gr.Textbox(label="News", lines=5, interactive=False)
        
        # Footer
        gr.Markdown("""
        ---
        <center>
        <small>⚠️ For informational purposes only. Not financial advice.</small>
        </center>
        """)
        
        # Event Handlers
        submit_btn.click(fn=process_query, inputs=[query_input], outputs=[report_output, trace_output])
        query_input.submit(fn=process_query, inputs=[query_input], outputs=[report_output, trace_output])
        
        btn_btc.click(
            fn=lambda: "Tell me about Bitcoin",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output, trace_output])
        
        btn_eth.click(
            fn=lambda: "Tell me about Ethereum",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output, trace_output])
        
        btn_sol.click(
            fn=lambda: "Tell me about Solana",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output, trace_output])
        
        btn_trend.click(
            fn=lambda: "What's trending in crypto?",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output, trace_output])
        
        btn_news.click(
            fn=lambda: "Latest crypto news",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output, trace_output])
        
        price_btn.click(fn=quick_price, inputs=[price_coin], outputs=[price_output])
        trend_btn.click(fn=quick_trending, outputs=[trend_output])
        news_btn.click(fn=quick_news, outputs=[news_output])
    
    return app


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("   🔮 CryptoSense - Web Interface")
    print("=" * 50)
    print("\nStarting server at http://localhost:7860\n")
    
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )
