

import time
import gradio as gr
from mcp_client import run_query, check_server
from validation import validate_input, validate_output, rate_limiter
from evaluation import evaluator, evaluation_store
from monitoring import metrics_store, is_monitoring_enabled


def process_query(query: str):
    """Process user query via MCP Client with evaluation."""

    # Check MCP Server connectivity
    if not check_server():
        return (
            " **MCP Server is not running!**\n\n"
            "Start the server first:\n```\npython mcp_server.py --transport sse\n```",
            "",
        )

    # Rate limiting
    if not rate_limiter.is_allowed():
        wait_time = rate_limiter.get_wait_time()
        return f" Rate limit reached. Please wait {wait_time} seconds.", ""

    # Input validation
    is_valid, sanitized_query, error = validate_input(query)
    if not is_valid:
        return f" {error}", ""

    try:
        # Run query via MCP Client → MCP Server
        result = run_query(sanitized_query)
        report = result.get("report", "No report generated.")
        mcp_metrics = result.get("metrics", {})

        # Output validation
        _, sanitized_report = validate_output(report)

        # Adapt MCP metrics for evaluator (add missing fields with defaults)
        eval_metrics = {
            "total_latency_ms": mcp_metrics.get("total_latency_ms", 0),
            "llm_calls": mcp_metrics.get("llm_calls", 0),
            "total_tokens": mcp_metrics.get("total_tokens", 0),
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "tool_calls": mcp_metrics.get("tool_calls", 0),
            "tool_errors": mcp_metrics.get("tool_errors", 0),
            "steps": mcp_metrics.get("llm_calls", 0) + mcp_metrics.get("tool_calls", 0),
            "agents_invoked": ["mcp-client"],
            "tools_invoked": mcp_metrics.get("tools_invoked", []),
            "errors": [t["error"] for t in mcp_metrics.get("tool_details", []) if t.get("error")],
        }

        # Run evaluation
        eval_report = evaluator.evaluate(
            query=sanitized_query,
            final_report=sanitized_report,
            metrics=eval_metrics,
            coin_id="",
            tasks=None,
        )
        evaluation_store.record(eval_report)
        metrics_store.record(sanitized_query, eval_metrics, report_preview=sanitized_report[:200])

        # Build metrics display
        eval_data = eval_report.to_dict()
        lines = []
        lines.append("═" * 50)
        lines.append("   METRICS & EVALUATION (MCP)")
        lines.append("═" * 50)
        lines.append(f"\n  Latency:          {mcp_metrics.get('total_latency_ms', 0):.0f} ms")
        lines.append(f" LLM Calls:        {mcp_metrics.get('llm_calls', 0)}")
        lines.append(f" Tool Calls:       {mcp_metrics.get('tool_calls', 0)}")
        lines.append(f" Tool Errors:       {mcp_metrics.get('tool_errors', 0)}")
        lines.append(f" Tokens:           {mcp_metrics.get('total_tokens', 0)}")
        lines.append(f" Tools Used:       {', '.join(mcp_metrics.get('tools_invoked', []))}")

        # Tool call details
        for td in mcp_metrics.get("tool_details", []):
            status = "✅" if not td.get("error") else ""
            lines.append(f"   {status} {td['tool']}({td.get('args', {})}) → {td['latency_ms']}ms")

        # Evaluation scores
        lines.append(f"\n{'─' * 50}")
        overall = eval_data.get("overall_score", 0)
        passed = eval_data.get("passed", False)
        lines.append(f"Overall Score:       {overall:.2%}  {' PASSED' if passed else ' FAILED'}")
        lines.append(f"{'─' * 50}")
        lines.append(f"{'Metric':<25} {'Score':<8} {'Value':<15} {'Status'}")
        lines.append(f"{'─' * 50}")
        for m in eval_data.get("metrics", []):
            status = "" if m.get("passed") else ""
            lines.append(f"{m['name']:<25} {m['score']:<8.2f} {str(m['value']):<15} {status}")
        lines.append("═" * 50)
        if eval_data.get("summary"):
            lines.append(eval_data["summary"])

        return sanitized_report, "\n".join(lines)

    except Exception as e:
        return f" Error: {str(e)}", ""


def get_dashboard_data():
    """Fetch aggregate monitoring and evaluation data."""
    mon_agg = metrics_store.get_aggregate()
    eval_agg = evaluation_store.get_aggregate()
    metric_breakdown = evaluation_store.get_metric_breakdown()

    lines = []
    lines.append("═" * 55)
    lines.append("   MONITORING & EVALUATION DASHBOARD (MCP)")
    lines.append("═" * 55)

    lines.append(f"\n📊 Query Aggregates ({mon_agg['total_queries']} queries)")
    lines.append(f"{'─' * 55}")
    lines.append(f"  Avg Latency:      {mon_agg['avg_latency_ms']:.0f} ms")
    lines.append(f"  Avg Tokens:       {mon_agg['avg_tokens']:.0f}")
    lines.append(f"  Total Errors:     {mon_agg['total_errors']}")
    lines.append(f"  Success Rate:     {mon_agg['success_rate']:.1f}%")

    lines.append(f"\n🎯 Evaluation Aggregates ({eval_agg['total_evals']} evaluations)")
    lines.append(f"{'─' * 55}")
    lines.append(f"  Avg Score:        {eval_agg['avg_score']:.2%}")
    lines.append(f"  Pass Rate:        {eval_agg['pass_rate']:.1f}%")

    if metric_breakdown:
        lines.append(f"\n📈 Per-Metric Breakdown")
        lines.append(f"{'─' * 55}")
        lines.append(f"{'Metric':<25} {'Avg':<8} {'Min':<8} {'Max':<8} {'N'}")
        lines.append(f"{'─' * 55}")
        for name, data in metric_breakdown.items():
            lines.append(f"{name:<25} {data['avg_score']:<8.2f} {data['min_score']:<8.2f} {data['max_score']:<8.2f} {data['count']}")

    # Recent queries
    recent = metrics_store.entries[-10:]
    if recent:
        lines.append(f"\n📝 Recent Queries (last {len(recent)})")
        lines.append(f"{'─' * 55}")
        for entry in reversed(recent):
            ts = entry.get("timestamp", "")
            q = entry.get("query", "")[:40]
            lat = entry.get("total_latency_ms", 0)
            tools = entry.get("tool_calls", 0)
            errs = len(entry.get("errors", []))
            lines.append(f"  [{ts}] {q:<40} {lat:.0f}ms  {tools}tools  {errs}err")

    langfuse_status = "✅ Connected" if is_monitoring_enabled() else "⚠️ Disabled (set LANGFUSE keys)"
    lines.append(f"\n🔗 Langfuse: {langfuse_status}")
    lines.append("═" * 55)

    return "\n".join(lines)


def create_ui():
    """Create beautiful structured Gradio UI with monitoring dashboard."""
    
    with gr.Blocks(title="CryptoSense") as app:
        
        with gr.Tabs():
            # ============================
            # Tab 1: Intelligence Report
            # ============================
            with gr.Tab("🔮 Intelligence"):
                # Header
                gr.Markdown("""
                <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; margin-bottom: 30px;">
                    <h1 style="color: white; margin: 0; font-size: 42px;">🔮 CryptoSense</h1>
                    <p style="color: #e8e8e8; margin: 10px 0 5px 0; font-size: 18px;">Multi-Agent Crypto Intelligence System</p>
                    <p style="color: #d0d0d0; margin: 0; font-size: 13px;">Powered by MCP Protocol • Groq Cloud • CoinGecko • Wikipedia • Langfuse • DeepEval</p>
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
                
                # Output Section
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

                # Evaluation output (per-query)
                gr.Markdown("""
                <div style="margin: 20px 0 10px 0;">
                    <span style="color: #666; font-size: 15px; font-weight: 600;">🎯 Evaluation & Metrics</span>
                </div>
                """)

                eval_output = gr.Textbox(
                    label="",
                    placeholder="Per-query evaluation metrics will appear here after each query...",
                    lines=3,
                    max_lines=25,
                    interactive=False,
                    autoscroll=False
                )
                
                # Footer
                gr.Markdown("""
                <div style="text-align: center; margin-top: 30px; padding: 15px; border-top: 1px solid #e0e0e0;">
                    <p style="color: #999; font-size: 12px; margin: 0;">⚠️ For informational purposes only. Not financial advice.</p>
                </div>
                """)
                
                # Event Handlers — now output both report and eval
                submit_btn.click(fn=process_query, inputs=[query_input], outputs=[report_output, eval_output])
                query_input.submit(fn=process_query, inputs=[query_input], outputs=[report_output, eval_output])
                
                btn_btc.click(
                    fn=lambda: "Tell me about Bitcoin",
                    outputs=[query_input]
                ).then(fn=process_query, inputs=[query_input], outputs=[report_output, eval_output])
                
                btn_eth.click(
                    fn=lambda: "Tell me about Ethereum",
                    outputs=[query_input]
                ).then(fn=process_query, inputs=[query_input], outputs=[report_output, eval_output])
                
                btn_sol.click(
                    fn=lambda: "Tell me about Solana",
                    outputs=[query_input]
                ).then(fn=process_query, inputs=[query_input], outputs=[report_output, eval_output])
                
                btn_trend.click(
                    fn=lambda: "What's trending in crypto?",
                    outputs=[query_input]
                ).then(fn=process_query, inputs=[query_input], outputs=[report_output, eval_output])
                
                btn_news.click(
                    fn=lambda: "Latest crypto news",
                    outputs=[query_input]
                ).then(fn=process_query, inputs=[query_input], outputs=[report_output, eval_output])

            # ============================
            # Tab 2: Monitoring Dashboard
            # ============================
            with gr.Tab("📈 Monitoring & Evaluation"):
                gr.Markdown("""
                <div style="text-align: center; padding: 15px; background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); border-radius: 12px; margin-bottom: 20px;">
                    <h2 style="color: white; margin: 0;">📈 Production Monitoring Dashboard</h2>
                    <p style="color: #e8e8e8; margin: 5px 0 0 0; font-size: 14px;">Langfuse traces • DeepEval metrics • Real-time analytics</p>
                </div>
                """)

                refresh_btn = gr.Button("🔄 Refresh Dashboard", variant="secondary")

                dashboard_output = gr.Textbox(
                    label="",
                    placeholder="Run some queries first, then refresh to see aggregate metrics...",
                    lines=5,
                    max_lines=40,
                    interactive=False,
                )

                refresh_btn.click(fn=get_dashboard_data, outputs=[dashboard_output])
    
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
