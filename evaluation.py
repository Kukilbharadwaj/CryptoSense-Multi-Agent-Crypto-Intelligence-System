
import time
import json
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict



# 1. Metric Definitions


@dataclass
class MetricResult:
    """Single evaluation metric result."""
    name: str
    category: str
    score: float          # 0.0 – 1.0
    value: Any            # raw value (count, ms, etc.)
    threshold: Optional[float] = None
    passed: Optional[bool] = None
    reason: str = ""

    def __post_init__(self):
        if self.threshold is not None and self.passed is None:
            self.passed = self.score >= self.threshold


@dataclass
class EvaluationReport:
    """Complete evaluation report for one query execution."""
    query: str
    timestamp: str = ""
    metrics: List[MetricResult] = field(default_factory=list)
    overall_score: float = 0.0
    passed: bool = False
    summary: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "timestamp": self.timestamp,
            "overall_score": round(self.overall_score, 4),
            "passed": self.passed,
            "summary": self.summary,
            "metrics": [asdict(m) for m in self.metrics],
        }

    def to_display_string(self) -> str:
        """Human-readable evaluation summary."""
        lines = [
            "═" * 50,
            "   EVALUATION REPORT",
            "═" * 50,
            f"Query: {self.query}",
            f"Time:  {self.timestamp}",
            f"Overall Score: {self.overall_score:.2%}",
            f"Status: {'✅ PASSED' if self.passed else '❌ FAILED'}",
            "",
            f"{'Metric':<25} {'Category':<15} {'Score':<8} {'Value':<12} {'Status'}",
            "─" * 70,
        ]
        for m in self.metrics:
            status = "✅" if m.passed else ("❌" if m.passed is False else "—")
            lines.append(f"{m.name:<25} {m.category:<15} {m.score:<8.2f} {str(m.value):<12} {status}")
        lines.append("─" * 70)
        if self.summary:
            lines.append(f"\n{self.summary}")
        lines.append("═" * 50)
        return "\n".join(lines)



# 2. Core Evaluator


class CryptoSenseEvaluator:
    """
    Evaluates a single query execution given the collected metrics dict
    (from monitoring.TraceContext.get_metrics_summary()) and the final report.
    """

    # Thresholds — tune for your SLA
    THRESHOLDS = {
        "task_completion":    0.5,   # report must exist and be meaningful
        "tool_accuracy":      0.7,   # ≥ 70% tools succeed
        "step_correctness":   0.5,   # orchestrator identified coin + tasks
        "efficiency_steps":   0.5,   # ≤ 10 steps
        "token_budget":       0.5,   # ≤ 4096 total tokens
        "latency_budget":     0.5,   # ≤ 30s total
    }

    MAX_STEPS = 10
    MAX_TOKENS = 4096
    MAX_LATENCY_MS = 30000  # 30 seconds

    def evaluate(
        self,
        query: str,
        final_report: Optional[str],
        metrics: Dict[str, Any],
        coin_id: str = "",
        tasks: Optional[List[str]] = None,
    ) -> EvaluationReport:
        """Run all evaluation metrics and return a report."""

        results: List[MetricResult] = []

        # --- 1. Task Completion Rate ---
        results.append(self._eval_task_completion(final_report))

        # --- 2. Tool Accuracy ---
        results.append(self._eval_tool_accuracy(metrics))

        # --- 3. Step Correctness (routing) ---
        results.append(self._eval_step_correctness(query, coin_id, tasks, metrics))

        # --- 4. Efficiency (steps) ---
        results.append(self._eval_efficiency(metrics))

        # --- 5. Token Usage ---
        results.append(self._eval_token_usage(metrics))

        # --- 6. Latency ---
        results.append(self._eval_latency(metrics))

        # Compute overall
        scores = [m.score for m in results]
        overall = sum(scores) / len(scores) if scores else 0.0
        all_passed = all(m.passed for m in results if m.passed is not None)

        report = EvaluationReport(
            query=query,
            metrics=results,
            overall_score=overall,
            passed=all_passed,
            summary=self._generate_summary(results, overall),
        )
        return report

    # ---- Individual metric implementations ---

    def _eval_task_completion(self, report: Optional[str]) -> MetricResult:
        """Did the system produce a meaningful report?"""
        if not report or len(report.strip()) < 50:
            return MetricResult(
                name="Task Completion",
                category="Task Success",
                score=0.0,
                value="empty/short",
                threshold=self.THRESHOLDS["task_completion"],
                reason="Report is empty or too short (<50 chars).",
            )

        # Check for error indicators
        error_phrases = ["error:", "workflow error:", "analysis error:", "no report generated"]
        report_lower = report.lower()
        has_error = any(p in report_lower for p in error_phrases)

        if has_error:
            return MetricResult(
                name="Task Completion",
                category="Task Success",
                score=0.2,
                value="error_report",
                threshold=self.THRESHOLDS["task_completion"],
                reason="Report contains error messages.",
            )

        # Check for structural quality markers
        quality_markers = ["market", "news", "sentiment", "risk", "analysis", "report"]
        marker_hits = sum(1 for m in quality_markers if m in report_lower)
        quality_score = min(1.0, marker_hits / 3)

        return MetricResult(
            name="Task Completion",
            category="Task Success",
            score=quality_score,
            value=f"{len(report)} chars",
            threshold=self.THRESHOLDS["task_completion"],
            reason=f"Report has {marker_hits}/{len(quality_markers)} quality markers.",
        )

    def _eval_tool_accuracy(self, metrics: Dict[str, Any]) -> MetricResult:
        """What fraction of tool calls succeeded?"""
        total = metrics.get("tool_calls", 0)
        errors = metrics.get("tool_errors", 0)
        if total == 0:
            return MetricResult(
                name="Tool Accuracy",
                category="Tool Usage",
                score=1.0,
                value="0 calls",
                threshold=self.THRESHOLDS["tool_accuracy"],
                reason="No tool calls made.",
            )

        accuracy = (total - errors) / total
        return MetricResult(
            name="Tool Accuracy",
            category="Tool Usage",
            score=accuracy,
            value=f"{total - errors}/{total} ok",
            threshold=self.THRESHOLDS["tool_accuracy"],
            reason=f"{errors} tool error(s) out of {total} calls.",
        )

    def _eval_step_correctness(
        self, query: str, coin_id: str, tasks: Optional[List[str]], metrics: Dict[str, Any]
    ) -> MetricResult:
        """Did orchestrator correctly identify coin and route tasks?"""
        score = 0.0
        reasons = []

        # Check coin identification
        if coin_id and coin_id != "":
            score += 0.5
            reasons.append(f"coin_id='{coin_id}'")
        else:
            reasons.append("no coin identified")

        # Check task routing
        agents = metrics.get("agents_invoked", [])
        if agents:
            score += 0.5
            reasons.append(f"agents={agents}")
        else:
            reasons.append("no agents invoked")

        return MetricResult(
            name="Step Correctness",
            category="Reasoning",
            score=score,
            value=coin_id or "none",
            threshold=self.THRESHOLDS["step_correctness"],
            reason="; ".join(reasons),
        )

    def _eval_efficiency(self, metrics: Dict[str, Any]) -> MetricResult:
        """How many steps were used (lower is better)."""
        steps = metrics.get("steps", 0)
        # Score: 1.0 at 5 steps, 0.5 at 10 steps, 0.0 at 15+
        if steps <= 5:
            score = 1.0
        elif steps <= self.MAX_STEPS:
            score = 1.0 - ((steps - 5) / (self.MAX_STEPS - 5)) * 0.5
        else:
            score = max(0.0, 0.5 - ((steps - self.MAX_STEPS) / 5) * 0.5)

        return MetricResult(
            name="Efficiency (Steps)",
            category="Efficiency",
            score=round(score, 4),
            value=f"{steps} steps",
            threshold=self.THRESHOLDS["efficiency_steps"],
            reason=f"{steps} agent steps (target ≤ {self.MAX_STEPS}).",
        )

    def _eval_token_usage(self, metrics: Dict[str, Any]) -> MetricResult:
        """Token consumption relative to budget."""
        total = metrics.get("total_tokens", 0)
        if total == 0:
            # Tokens not tracked (Groq may not always report)
            return MetricResult(
                name="Token Usage",
                category="Cost",
                score=0.5,
                value="not tracked",
                threshold=self.THRESHOLDS["token_budget"],
                reason="Token counts not available from provider.",
            )

        if total <= self.MAX_TOKENS:
            score = 1.0
        else:
            overshoot = (total - self.MAX_TOKENS) / self.MAX_TOKENS
            score = max(0.0, 1.0 - overshoot)

        return MetricResult(
            name="Token Usage",
            category="Cost",
            score=round(score, 4),
            value=f"{total} tokens",
            threshold=self.THRESHOLDS["token_budget"],
            reason=f"{total} tokens (budget {self.MAX_TOKENS}).",
        )

    def _eval_latency(self, metrics: Dict[str, Any]) -> MetricResult:
        """End-to-end latency relative to SLA."""
        latency = metrics.get("total_latency_ms", 0)
        if latency <= 0:
            return MetricResult(
                name="Latency",
                category="Latency",
                score=0.5,
                value="not measured",
                threshold=self.THRESHOLDS["latency_budget"],
                reason="Latency not recorded.",
            )

        if latency <= self.MAX_LATENCY_MS:
            score = 1.0 - (latency / self.MAX_LATENCY_MS) * 0.5  # 1.0 at 0ms → 0.5 at budget
        else:
            overshoot = (latency - self.MAX_LATENCY_MS) / self.MAX_LATENCY_MS
            score = max(0.0, 0.5 - overshoot * 0.5)

        return MetricResult(
            name="Latency",
            category="Latency",
            score=round(score, 4),
            value=f"{round(latency)} ms",
            threshold=self.THRESHOLDS["latency_budget"],
            reason=f"{round(latency)} ms (SLA {self.MAX_LATENCY_MS} ms).",
        )

    def _generate_summary(self, results: List[MetricResult], overall: float) -> str:
        failed = [m for m in results if m.passed is False]
        if not failed:
            return f"All metrics passed. Overall score: {overall:.2%}"
        names = ", ".join(m.name for m in failed)
        return f"Failed metrics: {names}. Overall score: {overall:.2%}"



# 3. DeepEval Integration 


def run_deepeval_evaluation(
    query: str,
    final_report: str,
    expected_output: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Run DeepEval LLM-as-judge evaluation if the library is installed.
    Returns dict of metric scores or None if DeepEval is unavailable.
    """
    try:
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            FaithfulnessMetric,
        )
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=query,
            actual_output=final_report,
            expected_output=expected_output,
            retrieval_context=[],  # could add market_data, news_data etc.
        )

        results = {}

        # Answer Relevancy
        relevancy = AnswerRelevancyMetric(threshold=0.5)
        relevancy.measure(test_case)
        results["answer_relevancy"] = {
            "score": relevancy.score,
            "passed": relevancy.is_successful(),
            "reason": relevancy.reason,
        }

        # Faithfulness (if we had retrieval context)
        try:
            faithfulness = FaithfulnessMetric(threshold=0.5)
            faithfulness.measure(test_case)
            results["faithfulness"] = {
                "score": faithfulness.score,
                "passed": faithfulness.is_successful(),
                "reason": faithfulness.reason,
            }
        except Exception:
            pass  # May fail without retrieval context

        return results

    except ImportError:
        return None
    except Exception as exc:
        return {"error": str(exc)}



# 4. Evaluation Store (in-memory history)

class EvaluationStore:
    """Keeps recent evaluation reports for the dashboard."""

    def __init__(self, max_entries: int = 50):
        self._reports: List[Dict[str, Any]] = []
        self._max = max_entries

    def record(self, report: EvaluationReport):
        self._reports.append(report.to_dict())
        if len(self._reports) > self._max:
            self._reports.pop(0)

    @property
    def reports(self) -> List[Dict[str, Any]]:
        return list(self._reports)

    def get_aggregate(self) -> Dict[str, Any]:
        if not self._reports:
            return {"total_evals": 0, "avg_score": 0, "pass_rate": 0}

        n = len(self._reports)
        avg_score = sum(r["overall_score"] for r in self._reports) / n
        pass_rate = sum(1 for r in self._reports if r["passed"]) / n
        return {
            "total_evals": n,
            "avg_score": round(avg_score, 4),
            "pass_rate": round(pass_rate * 100, 2),
        }

    def get_metric_breakdown(self) -> Dict[str, Dict[str, float]]:
        """Average score per metric name across all evaluations."""
        if not self._reports:
            return {}

        from collections import defaultdict
        accum = defaultdict(list)
        for r in self._reports:
            for m in r.get("metrics", []):
                accum[m["name"]].append(m["score"])

        return {
            name: {
                "avg_score": round(sum(scores) / len(scores), 4),
                "min_score": round(min(scores), 4),
                "max_score": round(max(scores), 4),
                "count": len(scores),
            }
            for name, scores in accum.items()
        }


# Global instances
evaluator = CryptoSenseEvaluator()
evaluation_store = EvaluationStore()
