"""Quick smoke test for MCP Client → MCP Server flow."""
from mcp_client import run_query, check_server

if not check_server():
    print("❌ MCP Server is NOT running! Start it first:")
    print("   python mcp_server.py --transport sse")
    exit(1)

result = run_query("What is Bitcoin price?")

report = result["report"]
metrics = result["metrics"]

print("=== REPORT (first 300 chars) ===")
print(report[:300])
print()

print("=== METRICS ===")
print(f"Latency: {metrics.get('total_latency_ms', 0):.0f}ms")
print(f"LLM calls: {metrics.get('llm_calls', 0)}")
print(f"Tool calls: {metrics.get('tool_calls', 0)}")
print(f"Tool errors: {metrics.get('tool_errors', 0)}")
print(f"Tokens: {metrics.get('total_tokens', 0)}")
print(f"Tools used: {metrics.get('tools_invoked', [])}")

print("\n=== TOOL DETAILS ===")
for td in metrics.get("tool_details", []):
    status = "OK" if not td.get("error") else f"ERR: {td['error']}"
    print(f"  {td['tool']}({td.get('args', {})}) → {td['latency_ms']}ms [{status}]")

print("\nSmoke test complete!")
