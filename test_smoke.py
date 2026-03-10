"""Quick smoke test for monitoring + evaluation integration."""
from workflow import run_query_with_trace

report, trace = run_query_with_trace("What is Bitcoin price?")

print("=== REPORT (first 200 chars) ===")
print(report[:200])
print()

print("=== TRACE KEYS ===")
print(list(trace.keys()))
print()

print("=== MONITORING ===")
m = trace.get("monitoring", {})
print(f"Latency: {m.get('total_latency_ms', 0):.0f}ms")
print(f"Steps: {m.get('steps', 0)}")
print(f"Tool calls: {m.get('tool_calls', 0)}")
print(f"LLM calls: {m.get('llm_calls', 0)}")
print(f"Tokens: {m.get('total_tokens', 0)}")
print(f"Agents: {m.get('agents_invoked', [])}")
print(f"Tools: {m.get('tools_invoked', [])}")
print(f"Errors: {m.get('errors', [])}")
print()

print("=== EVALUATION ===")
ev = trace.get("evaluation", {})
print(f"Overall: {ev.get('overall_score', 0):.2%}")
print(f"Passed: {ev.get('passed')}")
for metric in ev.get("metrics", []):
    status = "PASS" if metric.get("passed") else "FAIL"
    print(f"  {metric['name']:<25} {metric['score']:.2f}  {metric['value']}  [{status}]")
