"""
Correlation Engine - SECRET SAUCE Core Component

Links evaluation scores with distributed traces to identify root causes.

This is AgentEval's unique differentiator:
- Correlates quality metrics with system behavior
- Identifies performance bottlenecks affecting quality
- Provides actionable root cause analysis
- Generates improvement recommendations

Example correlation:
- Low Accuracy score (0.4) →  Trace shows high LLM latency (5s) + token limit hit
  → Root cause: Context truncation due to token limits
  → Recommendation: Increase max_tokens or implement better summarization
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agenteval.analysis.trace_analyzer import TraceAnalysis
from agenteval.evaluation.metrics import MetricType

logger = logging.getLogger(__name__)


class CorrelationType(str, Enum):
    """Types of correlations between metrics and traces"""

    PERFORMANCE_IMPACT = "performance_impact"
    ERROR_RELATED = "error_related"
    TOKEN_LIMIT = "token_limit"
    ROUTING_ISSUE = "routing_issue"
    DATABASE_BOTTLENECK = "database_bottleneck"
    MODEL_MISMATCH = "model_mismatch"
    CONTEXT_LOSS = "context_loss"


class ConfidenceLevel(str, Enum):
    """Confidence levels for correlations"""

    HIGH = "high"  # >0.8
    MEDIUM = "medium"  # 0.5-0.8
    LOW = "low"  # <0.5


@dataclass
class Correlation:
    """
    A correlation between an evaluation metric and trace behavior

    Attributes:
        metric_type: The metric being correlated
        metric_score: The metric's score
        correlation_type: Type of correlation found
        confidence: Confidence in this correlation (0.0-1.0)
        evidence: Supporting evidence from trace
        explanation: Human-readable explanation
        impact: Estimated impact on metric (0.0-1.0)
    """

    metric_type: MetricType
    metric_score: float
    correlation_type: CorrelationType
    confidence: float
    evidence: list[str]
    explanation: str
    impact: float  # How much this affects the metric (0.0-1.0)


@dataclass
class RootCause:
    """
    Identified root cause for quality issues

    Attributes:
        issue: Description of the issue
        severity: Severity level (0.0-1.0)
        affected_metrics: Metrics affected by this root cause
        correlations: Supporting correlations
        recommendations: Actionable recommendations to fix
        trace_evidence: Evidence from trace analysis
    """

    issue: str
    severity: float
    affected_metrics: list[MetricType]
    correlations: list[Correlation]
    recommendations: list[str]
    trace_evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationResult:
    """
    Complete correlation analysis result

    Attributes:
        trace_id: Associated trace ID
        evaluation_summary: Evaluation scores
        trace_insights: Trace analysis insights
        correlations: All identified correlations
        root_causes: Identified root causes
        overall_confidence: Overall confidence in analysis
        recommendations: Prioritized recommendations
    """

    trace_id: str
    evaluation_summary: dict[str, Any]
    trace_insights: dict[str, Any]
    correlations: list[Correlation]
    root_causes: list[RootCause]
    overall_confidence: float
    recommendations: list[dict[str, Any]]


class CorrelationEngine:
    """
    Correlates evaluation metrics with trace data to identify root causes

    This is the SECRET SAUCE that makes AgentEval unique:
    - Goes beyond simple evaluation to explain WHY scores are low
    - Links quality metrics to system behavior
    - Provides actionable insights for improvement
    """

    # Correlation thresholds
    HIGH_LATENCY_THRESHOLD_MS = 3000
    HIGH_TOKEN_THRESHOLD = 8000
    LOW_SCORE_THRESHOLD = 0.6
    ERROR_CORRELATION_THRESHOLD = 0.7

    def __init__(self) -> None:
        logger.info("CorrelationEngine initialized")

    def correlate(
        self,
        evaluation_results: dict[str, Any],
        trace_analysis: TraceAnalysis,
        trace_insights: dict[str, Any],
    ) -> CorrelationResult:
        """
        Correlate evaluation results with trace analysis

        Args:
            evaluation_results: Results from JudgeAgent evaluation
            trace_analysis: Parsed trace from TraceAnalyzer
            trace_insights: High-level trace insights

        Returns:
            Comprehensive correlation analysis
        """
        logger.info(
            f"Correlating evaluation with trace {trace_analysis.trace_id}",
            extra={
                "trace_id": trace_analysis.trace_id,
                "num_metrics": len(evaluation_results.get("metric_results", {})),
            },
        )

        # Extract metric results
        metric_results = evaluation_results.get("metric_results", {})

        # Find correlations for each metric
        all_correlations = []

        for metric_name, metric_data in metric_results.items():
            metric_type = MetricType(metric_name)
            metric_score = metric_data["score"]

            # Only correlate low-scoring metrics
            if metric_score < self.LOW_SCORE_THRESHOLD:
                correlations = self._find_correlations_for_metric(
                    metric_type=metric_type,
                    metric_score=metric_score,
                    trace_analysis=trace_analysis,
                    trace_insights=trace_insights,
                )
                all_correlations.extend(correlations)

        # Identify root causes from correlations
        root_causes = self._identify_root_causes(
            correlations=all_correlations,
            trace_analysis=trace_analysis,
            metric_results=metric_results,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(root_causes)

        # Calculate overall confidence
        overall_confidence = self._calculate_overall_confidence(all_correlations, root_causes)

        logger.info(
            "Correlation complete",
            extra={
                "trace_id": trace_analysis.trace_id,
                "correlations_found": len(all_correlations),
                "root_causes": len(root_causes),
                "confidence": overall_confidence,
            },
        )

        return CorrelationResult(
            trace_id=trace_analysis.trace_id,
            evaluation_summary=evaluation_results,
            trace_insights=trace_insights,
            correlations=all_correlations,
            root_causes=root_causes,
            overall_confidence=overall_confidence,
            recommendations=recommendations,
        )

    def _find_correlations_for_metric(
        self,
        metric_type: MetricType,
        metric_score: float,
        trace_analysis: TraceAnalysis,
        trace_insights: dict[str, Any],
    ) -> list[Correlation]:
        """
        Find correlations between a specific metric and trace behavior

        Args:
            metric_type: Metric to correlate
            metric_score: Metric's score
            trace_analysis: Trace analysis
            trace_insights: Trace insights

        Returns:
            List of identified correlations
        """
        correlations = []

        # Check for performance impact
        perf_correlation = self._check_performance_correlation(
            metric_type, metric_score, trace_insights
        )
        if perf_correlation:
            correlations.append(perf_correlation)

        # Check for error correlation
        error_correlation = self._check_error_correlation(metric_type, metric_score, trace_analysis)
        if error_correlation:
            correlations.append(error_correlation)

        # Check for token limit issues
        token_correlation = self._check_token_limit_correlation(
            metric_type, metric_score, trace_analysis
        )
        if token_correlation:
            correlations.append(token_correlation)

        # Check for routing issues
        routing_correlation = self._check_routing_correlation(
            metric_type, metric_score, trace_analysis
        )
        if routing_correlation:
            correlations.append(routing_correlation)

        # Check for database bottlenecks
        db_correlation = self._check_database_correlation(metric_type, metric_score, trace_insights)
        if db_correlation:
            correlations.append(db_correlation)

        return correlations

    def _check_performance_correlation(
        self, metric_type: MetricType, metric_score: float, trace_insights: dict[str, Any]
    ) -> Correlation | None:
        """Check if high latency correlates with low metric score"""
        llm_usage = trace_insights.get("llm_usage", {})
        avg_latency = llm_usage.get("avg_latency_ms", 0)

        if avg_latency > self.HIGH_LATENCY_THRESHOLD_MS:
            # High latency can affect multiple metrics
            affected_metrics = [
                MetricType.COMPLETENESS,  # Might timeout before completing
                MetricType.RELEVANCE,  # Might not have time to refine
                MetricType.COHERENCE,  # Context might be lost due to retries
            ]

            if metric_type in affected_metrics:
                impact = min(1.0, avg_latency / 10000)  # Normalize
                confidence = 0.8

                return Correlation(
                    metric_type=metric_type,
                    metric_score=metric_score,
                    correlation_type=CorrelationType.PERFORMANCE_IMPACT,
                    confidence=confidence,
                    evidence=[
                        f"High LLM latency detected: {avg_latency:.0f}ms (threshold: {self.HIGH_LATENCY_THRESHOLD_MS}ms)",
                        f"Average latency exceeds threshold by {(avg_latency / self.HIGH_LATENCY_THRESHOLD_MS - 1) * 100:.0f}%",
                    ],
                    explanation=(
                        f"High LLM latency ({avg_latency:.0f}ms) likely contributed to low {metric_type.value} score. "
                        f"Slow responses can lead to timeouts, incomplete answers, or context loss."
                    ),
                    impact=impact,
                )

        return None

    def _check_error_correlation(
        self, metric_type: MetricType, metric_score: float, trace_analysis: TraceAnalysis
    ) -> Correlation | None:
        """Check if errors in trace correlate with low metric score"""
        if trace_analysis.error_count == 0:
            return None

        error_rate = trace_analysis.error_count / len(trace_analysis.all_spans)

        if error_rate > 0.1:  # More than 10% error rate
            # Errors can affect multiple metrics
            affected_metrics = [
                MetricType.ACCURACY,
                MetricType.COMPLETENESS,
                MetricType.SESSION_HANDLING,
            ]

            if metric_type in affected_metrics:
                confidence = min(0.9, error_rate * 2)  # Higher error rate = higher confidence

                error_spans = [s for s in trace_analysis.all_spans if s.error is not None]
                error_types = [s.error.get("cause", "Unknown") for s in error_spans if s.error]

                return Correlation(
                    metric_type=metric_type,
                    metric_score=metric_score,
                    correlation_type=CorrelationType.ERROR_RELATED,
                    confidence=confidence,
                    evidence=[
                        f"Error rate: {error_rate:.1%} ({trace_analysis.error_count} errors)",
                        f"Error types: {', '.join(set(str(e) for e in error_types[:3]))}",
                    ],
                    explanation=(
                        f"High error rate ({error_rate:.1%}) strongly correlates with low {metric_type.value} score. "
                        f"System errors prevent proper response generation."
                    ),
                    impact=error_rate,
                )

        return None

    def _check_token_limit_correlation(
        self, metric_type: MetricType, metric_score: float, trace_analysis: TraceAnalysis
    ) -> Correlation | None:
        """Check if token limits affect metric score"""
        llm_calls = trace_analysis.llm_calls

        if not llm_calls:
            return None

        # Check for high token usage
        high_token_calls = [
            call for call in llm_calls if call.total_tokens > self.HIGH_TOKEN_THRESHOLD
        ]

        if high_token_calls:
            # Token limits affect specific metrics
            affected_metrics = [
                MetricType.COMPLETENESS,  # Context truncation leads to incomplete answers
                MetricType.ACCURACY,  # Important context might be truncated
                MetricType.COHERENCE,  # Loss of conversation history
            ]

            if metric_type in affected_metrics:
                avg_tokens = sum(c.total_tokens for c in high_token_calls) / len(high_token_calls)
                confidence = 0.75

                return Correlation(
                    metric_type=metric_type,
                    metric_score=metric_score,
                    correlation_type=CorrelationType.TOKEN_LIMIT,
                    confidence=confidence,
                    evidence=[
                        f"{len(high_token_calls)} LLM calls exceeded {self.HIGH_TOKEN_THRESHOLD} tokens",
                        f"Average tokens in high-usage calls: {avg_tokens:.0f}",
                        "Potential context truncation detected",
                    ],
                    explanation=(
                        f"High token usage (avg {avg_tokens:.0f}) suggests context truncation, "
                        f"which likely contributed to low {metric_type.value} score. "
                        f"Important information may have been cut off."
                    ),
                    impact=0.6,
                )

        return None

    def _check_routing_correlation(
        self, metric_type: MetricType, metric_score: float, trace_analysis: TraceAnalysis
    ) -> Correlation | None:
        """Check if routing issues affect metric score"""
        routings = trace_analysis.agent_routings

        if not routings:
            return None

        # Check routing success rate
        success_rate = sum(1 for r in routings if r.success) / len(routings)

        if success_rate < 0.8:  # Less than 80% success rate
            affected_metrics = [
                MetricType.ROUTING_ACCURACY,
                MetricType.RELEVANCE,
                MetricType.SESSION_HANDLING,
            ]

            if metric_type in affected_metrics:
                confidence = 1.0 - success_rate  # Lower success = higher confidence in correlation

                failed_routings = [r for r in routings if not r.success]
                routing_path = " → ".join(r.to_agent for r in routings[:5])

                return Correlation(
                    metric_type=metric_type,
                    metric_score=metric_score,
                    correlation_type=CorrelationType.ROUTING_ISSUE,
                    confidence=confidence,
                    evidence=[
                        f"Routing success rate: {success_rate:.1%}",
                        f"Failed routings: {len(failed_routings)}",
                        f"Routing path: {routing_path}",
                    ],
                    explanation=(
                        f"Low routing success rate ({success_rate:.1%}) directly correlates with "
                        f"low {metric_type.value} score. Failed routings prevent proper task execution."
                    ),
                    impact=0.8,
                )

        return None

    def _check_database_correlation(
        self, metric_type: MetricType, metric_score: float, trace_insights: dict[str, Any]
    ) -> Correlation | None:
        """Check if database bottlenecks affect metric score"""
        db_activity = trace_insights.get("database_activity", {})
        avg_query_latency = db_activity.get("avg_latency_ms", 0)

        if avg_query_latency > 500:  # High DB latency
            affected_metrics = [
                MetricType.SESSION_HANDLING,
                MetricType.COHERENCE,
                MetricType.COMPLETENESS,
            ]

            if metric_type in affected_metrics:
                confidence = 0.6

                return Correlation(
                    metric_type=metric_type,
                    metric_score=metric_score,
                    correlation_type=CorrelationType.DATABASE_BOTTLENECK,
                    confidence=confidence,
                    evidence=[
                        f"High database latency: {avg_query_latency:.0f}ms",
                        f"Query count: {db_activity.get('query_count', 0)}",
                    ],
                    explanation=(
                        f"High database latency ({avg_query_latency:.0f}ms) may contribute to "
                        f"low {metric_type.value} score. Slow state retrieval affects response quality."
                    ),
                    impact=0.4,
                )

        return None

    def _identify_root_causes(
        self,
        correlations: list[Correlation],
        trace_analysis: TraceAnalysis,
        metric_results: dict[str, Any],
    ) -> list[RootCause]:
        """
        Identify root causes from correlations

        Groups related correlations into root causes
        """
        root_causes = []

        # Group correlations by type
        correlation_groups = {}
        for corr in correlations:
            corr_type = corr.correlation_type
            if corr_type not in correlation_groups:
                correlation_groups[corr_type] = []
            correlation_groups[corr_type].append(corr)

        # Create root cause for each group
        for corr_type, corrs in correlation_groups.items():
            # Calculate severity (average impact)
            severity = sum(c.impact for c in corrs) / len(corrs)

            # Get affected metrics
            affected_metrics = list(set(c.metric_type for c in corrs))

            # Generate issue description and recommendations
            issue, recommendations = self._generate_root_cause_details(
                corr_type, corrs, trace_analysis
            )

            # Extract trace evidence
            trace_evidence = {
                "correlation_count": len(corrs),
                "avg_confidence": sum(c.confidence for c in corrs) / len(corrs),
                "evidence": [e for c in corrs for e in c.evidence],
            }

            root_cause = RootCause(
                issue=issue,
                severity=severity,
                affected_metrics=affected_metrics,
                correlations=corrs,
                recommendations=recommendations,
                trace_evidence=trace_evidence,
            )

            root_causes.append(root_cause)

        # Sort by severity (highest first)
        root_causes.sort(key=lambda rc: rc.severity, reverse=True)

        return root_causes

    def _generate_root_cause_details(
        self,
        correlation_type: CorrelationType,
        correlations: list[Correlation],
        trace_analysis: TraceAnalysis,
    ) -> tuple[str, list[str]]:
        """Generate issue description and recommendations for a root cause"""

        if correlation_type == CorrelationType.PERFORMANCE_IMPACT:
            issue = "High LLM latency is degrading response quality"
            recommendations = [
                "Consider using a faster model (e.g., Nova Lite instead of Sonnet)",
                "Implement request caching for similar queries",
                "Reduce prompt size by optimizing context",
                "Add timeout handling with graceful degradation",
            ]

        elif correlation_type == CorrelationType.ERROR_RELATED:
            issue = "System errors are preventing proper response generation"
            recommendations = [
                "Investigate error logs for specific failure patterns",
                "Implement better error handling and retry logic",
                "Add circuit breakers to prevent cascade failures",
                "Monitor Bedrock and DynamoDB service health",
            ]

        elif correlation_type == CorrelationType.TOKEN_LIMIT:
            issue = "Token limits are causing context truncation"
            recommendations = [
                "Increase max_tokens parameter for LLM calls",
                "Implement better context summarization",
                "Use sliding window approach for long conversations",
                "Consider using models with larger context windows",
            ]

        elif correlation_type == CorrelationType.ROUTING_ISSUE:
            issue = "Agent routing failures are disrupting task execution"
            recommendations = [
                "Review routing logic for edge cases",
                "Add fallback routing strategies",
                "Implement routing confidence thresholds",
                "Add monitoring for routing patterns",
            ]

        elif correlation_type == CorrelationType.DATABASE_BOTTLENECK:
            issue = "Database latency is slowing down response generation"
            recommendations = [
                "Optimize DynamoDB table indexes",
                "Implement caching layer (e.g., ElastiCache)",
                "Use BatchGetItem for multiple queries",
                "Review table capacity and consider on-demand billing",
            ]

        else:
            issue = f"Issue detected: {correlation_type.value}"
            recommendations = ["Investigate trace for more details"]

        return issue, recommendations

    def _generate_recommendations(self, root_causes: list[RootCause]) -> list[dict[str, Any]]:
        """
        Generate prioritized list of recommendations

        Args:
            root_causes: Identified root causes

        Returns:
            Prioritized recommendations with metadata
        """
        recommendations = []

        for i, rc in enumerate(root_causes, 1):
            for rec in rc.recommendations:
                recommendations.append(
                    {
                        "priority": i,
                        "severity": rc.severity,
                        "issue": rc.issue,
                        "recommendation": rec,
                        "affected_metrics": [m.value for m in rc.affected_metrics],
                        "confidence": rc.trace_evidence.get("avg_confidence", 0.5),
                    }
                )

        return recommendations

    def _calculate_overall_confidence(
        self, correlations: list[Correlation], root_causes: list[RootCause]
    ) -> float:
        """Calculate overall confidence in correlation analysis"""
        if not correlations:
            return 0.0

        # Average confidence of all correlations
        avg_correlation_confidence = sum(c.confidence for c in correlations) / len(correlations)

        # Bonus for multiple correlations pointing to same root cause
        multi_correlation_bonus = min(0.2, len(root_causes) * 0.05)

        overall = min(1.0, avg_correlation_confidence + multi_correlation_bonus)

        return overall
