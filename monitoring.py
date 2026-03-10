"""
CryptoSense Monitoring Module
===============================
Production-level observability using Langfuse v4 (OpenTelemetry-based).

Tracks:
- Traces per query (end-to-end)
- Spans per agent (orchestrator, market, news, knowledge, analyst)
- Token usage & cost per LLM call
- Latency per agent and per tool
- Tool invocation details (inputs, outputs, errors)
- Custom metrics: step count, task routing, error rates
"""

import os
import time
from typing import Optional, Any, Dict
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# ------------------------------------
# Langfuse Client Singleton
# ------------------------------------

_langfuse_client = None
_langfuse_enabled = False
_langfuse_init_done = False


def _init_langfuse():
    """Lazy-init Langfuse client from env vars."""
    global _langfuse_client, _langfuse_enabled, _langfuse_init_done

    if _langfuse_init_done:
        return

    _langfuse_init_done = True

    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")
    host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

    if not public_key or not secret_key:
        _langfuse_enabled = False
        print("[Monitoring] Langfuse keys not found – monitoring disabled. Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY to enable.")
        return

    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host,
        )
        _langfuse_enabled = True
        print(f"[Monitoring] Langfuse v4 connected → {host}")
    except ImportError:
        _langfuse_enabled = False
        print("[Monitoring] langfuse package not installed – monitoring disabled.")
    except Exception as exc:
        _langfuse_enabled = False
        print(f"[Monitoring] Langfuse init error: {exc}")


def get_langfuse():
    """Return the Langfuse client (or None when disabled)."""
    _init_langfuse()
    return _langfuse_client


def is_monitoring_enabled() -> bool:
    _init_langfuse()
    return _langfuse_enabled


def flush():
    """Flush pending events to Langfuse."""
    if _langfuse_client is not None:
        try:
            _langfuse_client.flush()
        except Exception:
            pass


# ------------------------------------
# Trace Context Manager
# ------------------------------------

class TraceContext:
    """
    Holds the active Langfuse trace + span stack for one query execution.
    Uses Langfuse v4 API: start_as_current_observation / start_observation.
    """

    def __init__(self, query: str, user_id: Optional[str] = None, session_id: Optional[str] = None):
        self.query = query
        self._root_span = None   # The root agent span representing the full trace
        self._lf = get_langfuse()
        self.metrics: Dict[str, Any] = {
            "start_time": time.time(),
            "end_time": None,
            "total_latency_ms": 0,
            "agent_latencies_ms": {},
            "tool_latencies_ms": {},
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "llm_calls": 0,
            "tool_calls": 0,
            "tool_errors": 0,
            "steps": 0,
            "agents_invoked": [],
            "tools_invoked": [],
            "errors": [],
        }

        # Create root observation (acts as the trace root)
        if self._lf is not None:
            try:
                self._root_span = self._lf.start_observation(
                    name="cryptosense-query",
                    as_type="agent",
                    input={"query": query},
                    metadata={"system": "CryptoSense", "user_id": user_id, "session_id": session_id},
                )
            except Exception as exc:
                print(f"[Monitoring] Failed to create root span: {exc}")
                self._root_span = None

    # -- Agent span helpers --------------------------------------------------

    @contextmanager
    def agent_span(self, agent_name: str, input_data: Optional[dict] = None):
        """Context manager that creates a Langfuse observation for an agent."""
        start = time.time()
        span = None
        if self._root_span is not None:
            try:
                span = self._root_span.start_observation(
                    name=f"agent:{agent_name}",
                    as_type="agent",
                    input=input_data or {},
                )
            except Exception:
                span = None
        try:
            yield span
        except Exception as exc:
            self.metrics["errors"].append({"agent": agent_name, "error": str(exc)})
            if span is not None:
                try:
                    span.update(level="ERROR", status_message=str(exc))
                    span.end()
                except Exception:
                    pass
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self.metrics["agent_latencies_ms"][agent_name] = elapsed_ms
            self.metrics["agents_invoked"].append(agent_name)
            self.metrics["steps"] += 1
            if span is not None:
                try:
                    span.update(output={"latency_ms": round(elapsed_ms, 2)})
                    span.end()
                except Exception:
                    pass

    # -- Tool span helpers ---------------------------------------------------

    @contextmanager
    def tool_span(self, tool_name: str, input_data: Optional[dict] = None):
        """Context manager that creates a Langfuse observation for a tool call."""
        start = time.time()
        span = None
        if self._root_span is not None:
            try:
                span = self._root_span.start_observation(
                    name=f"tool:{tool_name}",
                    as_type="tool",
                    input=input_data or {},
                )
            except Exception:
                span = None
        error_occurred = False
        try:
            yield span
        except Exception as exc:
            error_occurred = True
            self.metrics["tool_errors"] += 1
            self.metrics["errors"].append({"tool": tool_name, "error": str(exc)})
            if span is not None:
                try:
                    span.update(level="ERROR", status_message=str(exc))
                    span.end()
                except Exception:
                    pass
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self.metrics["tool_latencies_ms"][tool_name] = elapsed_ms
            self.metrics["tool_calls"] += 1
            self.metrics["tools_invoked"].append(tool_name)
            if span is not None:
                try:
                    span.update(output={"latency_ms": round(elapsed_ms, 2), "error": error_occurred})
                    span.end()
                except Exception:
                    pass

    # -- LLM generation helper -----------------------------------------------

    @contextmanager
    def llm_generation(self, name: str, model: str = "llama-3.3-70b-versatile", input_messages: Optional[list] = None):
        """Context manager wrapping an LLM call as a Langfuse generation observation."""
        start = time.time()
        gen = None
        if self._root_span is not None:
            try:
                gen = self._root_span.start_observation(
                    name=name,
                    as_type="generation",
                    model=model,
                    input=input_messages or [],
                )
            except Exception:
                gen = None
        try:
            yield gen
        except Exception as exc:
            self.metrics["errors"].append({"llm": name, "error": str(exc)})
            if gen is not None:
                try:
                    gen.update(level="ERROR", status_message=str(exc))
                    gen.end()
                except Exception:
                    pass
            raise
        finally:
            elapsed_ms = (time.time() - start) * 1000
            self.metrics["llm_calls"] += 1
            if gen is not None:
                try:
                    gen.update(output={"latency_ms": round(elapsed_ms, 2)})
                    gen.end()
                except Exception:
                    pass

    def record_token_usage(self, prompt_tokens: int = 0, completion_tokens: int = 0):
        """Accumulate token usage from an LLM call."""
        self.metrics["prompt_tokens"] += prompt_tokens
        self.metrics["completion_tokens"] += completion_tokens
        self.metrics["total_tokens"] += prompt_tokens + completion_tokens

    # -- Finalize trace ------------------------------------------------------

    def finalize(self, output: Optional[str] = None, error: Optional[str] = None):
        """Close the root span and record final metrics."""
        self.metrics["end_time"] = time.time()
        self.metrics["total_latency_ms"] = (self.metrics["end_time"] - self.metrics["start_time"]) * 1000

        if self._root_span is not None:
            try:
                self._root_span.update(
                    output={"report_preview": (output or "")[:500]},
                    metadata={
                        "total_latency_ms": round(self.metrics["total_latency_ms"], 2),
                        "total_tokens": self.metrics["total_tokens"],
                        "llm_calls": self.metrics["llm_calls"],
                        "tool_calls": self.metrics["tool_calls"],
                        "tool_errors": self.metrics["tool_errors"],
                        "steps": self.metrics["steps"],
                        "agents": self.metrics["agents_invoked"],
                        "error": error,
                    },
                )
                # Score the trace
                if error:
                    self._root_span.score_trace(name="success", value=0.0, comment=error)
                elif output:
                    self._root_span.score_trace(name="success", value=1.0)

                self._root_span.end()
            except Exception as exc:
                print(f"[Monitoring] Error finalizing trace: {exc}")

        flush()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Return a clean metrics dict for display / evaluation."""
        return {
            "total_latency_ms": round(self.metrics["total_latency_ms"], 2),
            "agent_latencies_ms": {k: round(v, 2) for k, v in self.metrics["agent_latencies_ms"].items()},
            "tool_latencies_ms": {k: round(v, 2) for k, v in self.metrics["tool_latencies_ms"].items()},
            "total_tokens": self.metrics["total_tokens"],
            "prompt_tokens": self.metrics["prompt_tokens"],
            "completion_tokens": self.metrics["completion_tokens"],
            "llm_calls": self.metrics["llm_calls"],
            "tool_calls": self.metrics["tool_calls"],
            "tool_errors": self.metrics["tool_errors"],
            "steps": self.metrics["steps"],
            "agents_invoked": list(set(self.metrics["agents_invoked"])),
            "tools_invoked": list(set(self.metrics["tools_invoked"])),
            "errors": self.metrics["errors"],
        }


# ------------------------------------
# Metrics Store (in-memory for dashboard)
# ------------------------------------

class MetricsStore:
    """
    In-memory ring buffer of recent query metrics for the Gradio dashboard.
    Keeps the last N traces.
    """

    def __init__(self, max_entries: int = 100):
        self._entries: list[Dict[str, Any]] = []
        self._max = max_entries

    def record(self, query: str, metrics: Dict[str, Any], report_preview: str = ""):
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "report_preview": report_preview[:200],
            **metrics,
        }
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries.pop(0)

    @property
    def entries(self) -> list[Dict[str, Any]]:
        return list(self._entries)

    def get_aggregate(self) -> Dict[str, Any]:
        """Compute aggregate statistics over stored entries."""
        if not self._entries:
            return {
                "total_queries": 0,
                "avg_latency_ms": 0,
                "avg_tokens": 0,
                "avg_steps": 0,
                "total_errors": 0,
                "success_rate": 0,
            }

        n = len(self._entries)
        total_latency = sum(e.get("total_latency_ms", 0) for e in self._entries)
        total_tokens = sum(e.get("total_tokens", 0) for e in self._entries)
        total_steps = sum(e.get("steps", 0) for e in self._entries)
        total_errors = sum(1 for e in self._entries if e.get("errors"))
        success = sum(1 for e in self._entries if not e.get("errors"))

        return {
            "total_queries": n,
            "avg_latency_ms": round(total_latency / n, 2),
            "avg_tokens": round(total_tokens / n, 2),
            "avg_steps": round(total_steps / n, 2),
            "total_errors": total_errors,
            "success_rate": round((success / n) * 100, 2),
        }


# Global metrics store
metrics_store = MetricsStore()
