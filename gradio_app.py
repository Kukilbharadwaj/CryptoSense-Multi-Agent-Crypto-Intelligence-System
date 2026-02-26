"""
CryptoSense Gradio UI - Clean Version
======================================
Minimalist web interface for the multi-agent system.
"""

import gradio as gr
from workflow import run_query_with_trace
from validation import validate_input, validate_output, rate_limiter


def process_query(query: str):
    """Process user query with validation."""
    
    # Rate limiting check
    if not rate_limiter.is_allowed():
        wait_time = rate_limiter.get_wait_time()
        return f"⏳ Rate limit reached. Please wait {wait_time} seconds."
    
    # Input validation
    is_valid, sanitized_query, error = validate_input(query)
    if not is_valid:
        return f"❌ {error}"
    
    try:
        # Run multi-agent workflow
        report, trace = run_query_with_trace(sanitized_query)
        
        # Output validation
        _, sanitized_report = validate_output(report)
        
        return sanitized_report
        
    except Exception as e:
        return f"❌ Error: {str(e)}"


def create_ui():
    """Create beautiful structured Gradio UI."""
    
    with gr.Blocks(title="CryptoSense") as app:
        
        # Header
        gr.Markdown("""
        <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px;">
            <h1 style="color: white; margin: 0; font-size: 42px;">🔮 CryptoSense</h1>
            <p style="color: #e8e8e8; margin: 10px 0 5px 0; font-size: 18px;">Multi-Agent Crypto Intelligence System</p>
            <p style="color: #d0d0d0; margin: 0; font-size: 13px;">Powered by LangGraph • Groq Cloud • CoinGecko • Wikipedia</p>
        </div>
        """)
        
        # Input Section
        query_input = gr.Textbox(
            label="",
            placeholder="💬 Ask anything about cryptocurrency... (e.g., What's Bitcoin's price? Tell me about Ethereum)",
            lines=3,
            max_lines=5
        )
        
        # Main Analyze Button
        submit_btn = gr.Button(
            "🚀 Generate Intelligence Report",
            variant="primary",
            size="lg"
        )
        
        # Quick Action Buttons
        gr.Markdown("""
        <div style="text-align: center; margin: 25px 0 15px 0;">
            <span style="color: #666; font-size: 14px; font-weight: 500;">⚡ Quick Actions</span>
        </div>
        """)
        
        with gr.Row():
            btn_btc = gr.Button("₿ Bitcoin", size="sm")
            btn_eth = gr.Button("Ξ Ethereum", size="sm")
            btn_sol = gr.Button("◎ Solana", size="sm")
            btn_trend = gr.Button("🔥 Trending", size="sm")
            btn_news = gr.Button("📰 News", size="sm")
        
        # Output Section with dynamic sizing
        gr.Markdown("""
        <div style="margin: 30px 0 15px 0;">
            <span style="color: #666; font-size: 15px; font-weight: 600;">📊 Intelligence Report</span>
        </div>
        """)
        
        report_output = gr.Textbox(
            label="",
            placeholder="Your intelligent crypto analysis will appear here...",
            lines=3,
            max_lines=30,
            interactive=False,
            autoscroll=False
        )
        
        # Footer
        gr.Markdown("""
        <div style="text-align: center; margin-top: 30px; padding: 15px; border-top: 1px solid #e0e0e0;">
            <p style="color: #999; font-size: 12px; margin: 0;">⚠️ For informational purposes only. Not financial advice.</p>
        </div>
        """)
        
        # Event Handlers
        submit_btn.click(fn=process_query, inputs=[query_input], outputs=[report_output])
        query_input.submit(fn=process_query, inputs=[query_input], outputs=[report_output])
        
        btn_btc.click(
            fn=lambda: "Tell me about Bitcoin",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output])
        
        btn_eth.click(
            fn=lambda: "Tell me about Ethereum",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output])
        
        btn_sol.click(
            fn=lambda: "Tell me about Solana",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output])
        
        btn_trend.click(
            fn=lambda: "What's trending in crypto?",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output])
        
        btn_news.click(
            fn=lambda: "Latest crypto news",
            outputs=[query_input]
        ).then(fn=process_query, inputs=[query_input], outputs=[report_output])
    
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
