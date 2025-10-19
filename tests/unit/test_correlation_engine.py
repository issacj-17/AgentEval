"""
Unit tests for CorrelationEngine - Root cause analysis via metric/trace correlation.

Tests correlation detection, root cause identification, and recommendation generation.
"""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from agenteval.analysis.correlation_engine import (
    ConfidenceLevel,
    Correlation,
    CorrelationEngine,
    CorrelationType,
    RootCause,
)
from agenteval.analysis.trace_analyzer import (
    AgentRouting,
    LLMCall,
    ParsedSpan,
    SpanType,
    TraceAnalysis,
)
from agenteval.evaluation.metrics import MetricType


class TestCorrelationTypeEnum:
    """Test suite for CorrelationType enum"""

    def test_correlation_type_values(self):
        """Test CorrelationType enum values"""
        assert CorrelationType.PERFORMANCE_IMPACT.value == "performance_impact"
        assert CorrelationType.ERROR_RELATED.value == "error_related"
        assert CorrelationType.TOKEN_LIMIT.value == "token_limit"
        assert CorrelationType.ROUTING_ISSUE.value == "routing_issue"
        assert CorrelationType.DATABASE_BOTTLENECK.value == "database_bottleneck"
        assert CorrelationType.MODEL_MISMATCH.value == "model_mismatch"
        assert CorrelationType.CONTEXT_LOSS.value == "context_loss"


class TestConfidenceLevelEnum:
    """Test suite for ConfidenceLevel enum"""

    def test_confidence_level_values(self):
        """Test ConfidenceLevel enum values"""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"
        assert ConfidenceLevel.LOW.value == "low"


class TestCorrelationEngineInitialization:
    """Test suite for CorrelationEngine initialization"""

    def test_init(self):
        """Test CorrelationEngine initialization"""
        engine = CorrelationEngine()
        assert engine is not None
        assert engine.HIGH_LATENCY_THRESHOLD_MS == 3000
        assert engine.HIGH_TOKEN_THRESHOLD == 8000
        assert engine.LOW_SCORE_THRESHOLD == 0.6


class TestCheckPerformanceCorrelation:
    """Test suite for performance correlation detection"""

    def test_check_performance_correlation_high_latency(self):
        """Test detection of high LLM latency correlation"""
        engine = CorrelationEngine()

        trace_insights = {"llm_usage": {"avg_latency_ms": 5000}}  # Above threshold

        correlation = engine._check_performance_correlation(
            metric_type=MetricType.COMPLETENESS, metric_score=0.4, trace_insights=trace_insights
        )

        assert correlation is not None
        assert correlation.correlation_type == CorrelationType.PERFORMANCE_IMPACT
        assert correlation.confidence == 0.8
        assert correlation.metric_type == MetricType.COMPLETENESS
        assert len(correlation.evidence) == 2
        assert "5000ms" in correlation.evidence[0]

    def test_check_performance_correlation_below_threshold(self):
        """Test no correlation when latency is acceptable"""
        engine = CorrelationEngine()

        trace_insights = {"llm_usage": {"avg_latency_ms": 1000}}  # Below threshold

        correlation = engine._check_performance_correlation(
            metric_type=MetricType.COMPLETENESS, metric_score=0.4, trace_insights=trace_insights
        )

        assert correlation is None

    def test_check_performance_correlation_unaffected_metric(self):
        """Test no correlation for metrics not affected by latency"""
        engine = CorrelationEngine()

        trace_insights = {"llm_usage": {"avg_latency_ms": 5000}}

        correlation = engine._check_performance_correlation(
            metric_type=MetricType.TOXICITY,  # Not in affected list
            metric_score=0.4,
            trace_insights=trace_insights,
        )

        assert correlation is None


class TestCheckErrorCorrelation:
    """Test suite for error correlation detection"""

    def test_check_error_correlation_high_error_rate(self):
        """Test detection of error correlation with high error rate"""
        engine = CorrelationEngine()

        trace_analysis = TraceAnalysis(
            trace_id="trace-errors",
            root_span=None,
            all_spans=[
                ParsedSpan(
                    span_id="span-1",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name="llm",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=1000.0,
                    error={"cause": "Rate limit"},
                ),
                ParsedSpan(
                    span_id="span-2",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name="llm2",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=1000.0,
                ),
            ],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=2000.0,
            error_count=1,  # 50% error rate
        )

        correlation = engine._check_error_correlation(
            metric_type=MetricType.ACCURACY, metric_score=0.3, trace_analysis=trace_analysis
        )

        assert correlation is not None
        assert correlation.correlation_type == CorrelationType.ERROR_RELATED
        assert correlation.metric_type == MetricType.ACCURACY
        assert "50.0%" in correlation.evidence[0]
        assert "Rate limit" in correlation.evidence[1]

    def test_check_error_correlation_no_errors(self):
        """Test no correlation when there are no errors"""
        engine = CorrelationEngine()

        trace_analysis = TraceAnalysis(
            trace_id="trace-clean",
            root_span=None,
            all_spans=[
                ParsedSpan(
                    span_id="span-1",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name="llm",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=1000.0,
                )
            ],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1000.0,
            error_count=0,
        )

        correlation = engine._check_error_correlation(
            metric_type=MetricType.ACCURACY, metric_score=0.3, trace_analysis=trace_analysis
        )

        assert correlation is None

    def test_check_error_correlation_low_error_rate(self):
        """Test no correlation when error rate is below threshold"""
        engine = CorrelationEngine()

        # 5% error rate (below 10% threshold)
        trace_analysis = TraceAnalysis(
            trace_id="trace-low-errors",
            root_span=None,
            all_spans=[
                ParsedSpan(
                    span_id=f"span-{i}",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name=f"llm-{i}",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=100.0,
                    error={"cause": "Error"} if i == 0 else None,
                )
                for i in range(20)
            ],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=2000.0,
            error_count=1,
        )

        correlation = engine._check_error_correlation(
            metric_type=MetricType.ACCURACY, metric_score=0.3, trace_analysis=trace_analysis
        )

        assert correlation is None


class TestCheckTokenLimitCorrelation:
    """Test suite for token limit correlation detection"""

    def test_check_token_limit_correlation_high_tokens(self):
        """Test detection of token limit correlation"""
        engine = CorrelationEngine()

        trace_analysis = TraceAnalysis(
            trace_id="trace-tokens",
            root_span=None,
            all_spans=[],
            llm_calls=[
                LLMCall(
                    span_id="llm-1",
                    model_id="claude-3",
                    prompt_tokens=5000,
                    completion_tokens=4000,
                    total_tokens=9000,  # Above threshold
                    latency_ms=2000.0,
                )
            ],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=2000.0,
            error_count=0,
        )

        correlation = engine._check_token_limit_correlation(
            metric_type=MetricType.COMPLETENESS, metric_score=0.4, trace_analysis=trace_analysis
        )

        assert correlation is not None
        assert correlation.correlation_type == CorrelationType.TOKEN_LIMIT
        assert correlation.confidence == 0.75
        assert "9000" in correlation.evidence[1]

    def test_check_token_limit_correlation_no_llm_calls(self):
        """Test no correlation when there are no LLM calls"""
        engine = CorrelationEngine()

        trace_analysis = TraceAnalysis(
            trace_id="trace-no-llm",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1000.0,
            error_count=0,
        )

        correlation = engine._check_token_limit_correlation(
            metric_type=MetricType.COMPLETENESS, metric_score=0.4, trace_analysis=trace_analysis
        )

        assert correlation is None

    def test_check_token_limit_correlation_below_threshold(self):
        """Test no correlation when tokens are below threshold"""
        engine = CorrelationEngine()

        trace_analysis = TraceAnalysis(
            trace_id="trace-low-tokens",
            root_span=None,
            all_spans=[],
            llm_calls=[
                LLMCall(
                    span_id="llm-1",
                    model_id="claude-3",
                    prompt_tokens=1000,
                    completion_tokens=500,
                    total_tokens=1500,  # Below threshold
                    latency_ms=1000.0,
                )
            ],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1000.0,
            error_count=0,
        )

        correlation = engine._check_token_limit_correlation(
            metric_type=MetricType.COMPLETENESS, metric_score=0.4, trace_analysis=trace_analysis
        )

        assert correlation is None


class TestCheckRoutingCorrelation:
    """Test suite for routing correlation detection"""

    def test_check_routing_correlation_low_success_rate(self):
        """Test detection of routing issue correlation"""
        engine = CorrelationEngine()

        trace_analysis = TraceAnalysis(
            trace_id="trace-routing",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[
                AgentRouting(
                    span_id="routing-1",
                    from_agent="orchestrator",
                    to_agent="persona",
                    routing_reason="Task",
                    latency_ms=100.0,
                    success=True,
                ),
                AgentRouting(
                    span_id="routing-2",
                    from_agent="persona",
                    to_agent="judge",
                    routing_reason="Eval",
                    latency_ms=100.0,
                    success=False,
                ),
                AgentRouting(
                    span_id="routing-3",
                    from_agent="orchestrator",
                    to_agent="redteam",
                    routing_reason="Attack",
                    latency_ms=100.0,
                    success=False,
                ),
            ],
            database_queries=[],
            total_duration_ms=300.0,
            error_count=0,
        )

        correlation = engine._check_routing_correlation(
            metric_type=MetricType.ROUTING_ACCURACY, metric_score=0.3, trace_analysis=trace_analysis
        )

        assert correlation is not None
        assert correlation.correlation_type == CorrelationType.ROUTING_ISSUE
        # Success rate is 1/3 = 0.33, so confidence = 1.0 - 0.33 = 0.67
        assert correlation.confidence > 0.6
        assert "33.3%" in correlation.evidence[0]

    def test_check_routing_correlation_high_success_rate(self):
        """Test no correlation when routing success rate is high"""
        engine = CorrelationEngine()

        trace_analysis = TraceAnalysis(
            trace_id="trace-good-routing",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[
                AgentRouting(
                    span_id="routing-1",
                    from_agent="a",
                    to_agent="b",
                    routing_reason=None,
                    latency_ms=100.0,
                    success=True,
                ),
                AgentRouting(
                    span_id="routing-2",
                    from_agent="b",
                    to_agent="c",
                    routing_reason=None,
                    latency_ms=100.0,
                    success=True,
                ),
            ],
            database_queries=[],
            total_duration_ms=200.0,
            error_count=0,
        )

        correlation = engine._check_routing_correlation(
            metric_type=MetricType.ROUTING_ACCURACY, metric_score=0.9, trace_analysis=trace_analysis
        )

        assert correlation is None


class TestCheckDatabaseCorrelation:
    """Test suite for database correlation detection"""

    def test_check_database_correlation_high_latency(self):
        """Test detection of database bottleneck correlation"""
        engine = CorrelationEngine()

        trace_insights = {
            "database_activity": {"avg_latency_ms": 750, "query_count": 5}  # Above 500ms threshold
        }

        correlation = engine._check_database_correlation(
            metric_type=MetricType.SESSION_HANDLING, metric_score=0.4, trace_insights=trace_insights
        )

        assert correlation is not None
        assert correlation.correlation_type == CorrelationType.DATABASE_BOTTLENECK
        assert correlation.confidence == 0.6
        assert "750ms" in correlation.evidence[0]
        assert "5" in correlation.evidence[1]

    def test_check_database_correlation_low_latency(self):
        """Test no correlation when DB latency is acceptable"""
        engine = CorrelationEngine()

        trace_insights = {
            "database_activity": {"avg_latency_ms": 100, "query_count": 3}  # Below threshold
        }

        correlation = engine._check_database_correlation(
            metric_type=MetricType.SESSION_HANDLING, metric_score=0.4, trace_insights=trace_insights
        )

        assert correlation is None


class TestIdentifyRootCauses:
    """Test suite for root cause identification"""

    def test_identify_root_causes_groups_by_type(self):
        """Test that correlations are grouped by type into root causes"""
        engine = CorrelationEngine()

        correlations = [
            Correlation(
                metric_type=MetricType.COMPLETENESS,
                metric_score=0.4,
                correlation_type=CorrelationType.PERFORMANCE_IMPACT,
                confidence=0.8,
                evidence=["High latency"],
                explanation="Latency issue",
                impact=0.6,
            ),
            Correlation(
                metric_type=MetricType.RELEVANCE,
                metric_score=0.3,
                correlation_type=CorrelationType.PERFORMANCE_IMPACT,
                confidence=0.7,
                evidence=["High latency"],
                explanation="Latency issue",
                impact=0.5,
            ),
            Correlation(
                metric_type=MetricType.ACCURACY,
                metric_score=0.3,
                correlation_type=CorrelationType.ERROR_RELATED,
                confidence=0.9,
                evidence=["Errors"],
                explanation="Error issue",
                impact=0.8,
            ),
        ]

        trace_analysis = TraceAnalysis(
            trace_id="trace-rc",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1000.0,
            error_count=0,
        )

        root_causes = engine._identify_root_causes(
            correlations=correlations, trace_analysis=trace_analysis, metric_results={}
        )

        assert len(root_causes) == 2  # 2 different correlation types
        # Should be sorted by severity (highest first)
        assert root_causes[0].severity > root_causes[1].severity

    def test_identify_root_causes_calculates_severity(self):
        """Test that severity is calculated as average impact"""
        engine = CorrelationEngine()

        correlations = [
            Correlation(
                metric_type=MetricType.COMPLETENESS,
                metric_score=0.4,
                correlation_type=CorrelationType.TOKEN_LIMIT,
                confidence=0.75,
                evidence=["High tokens"],
                explanation="Token issue",
                impact=0.6,
            ),
            Correlation(
                metric_type=MetricType.ACCURACY,
                metric_score=0.3,
                correlation_type=CorrelationType.TOKEN_LIMIT,
                confidence=0.75,
                evidence=["High tokens"],
                explanation="Token issue",
                impact=0.8,
            ),
        ]

        trace_analysis = TraceAnalysis(
            trace_id="trace-tokens",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1000.0,
            error_count=0,
        )

        root_causes = engine._identify_root_causes(
            correlations=correlations, trace_analysis=trace_analysis, metric_results={}
        )

        assert len(root_causes) == 1
        # Severity should be (0.6 + 0.8) / 2 = 0.7
        assert root_causes[0].severity == 0.7


class TestGenerateRootCauseDetails:
    """Test suite for root cause detail generation"""

    def test_generate_root_cause_details_performance(self):
        """Test generation of performance root cause details"""
        engine = CorrelationEngine()

        issue, recommendations = engine._generate_root_cause_details(
            correlation_type=CorrelationType.PERFORMANCE_IMPACT,
            correlations=[],
            trace_analysis=MagicMock(),
        )

        assert "latency" in issue.lower()
        assert len(recommendations) > 0
        assert any("faster model" in rec.lower() for rec in recommendations)

    def test_generate_root_cause_details_error(self):
        """Test generation of error root cause details"""
        engine = CorrelationEngine()

        issue, recommendations = engine._generate_root_cause_details(
            correlation_type=CorrelationType.ERROR_RELATED,
            correlations=[],
            trace_analysis=MagicMock(),
        )

        assert "error" in issue.lower()
        assert any("error handling" in rec.lower() for rec in recommendations)

    def test_generate_root_cause_details_token_limit(self):
        """Test generation of token limit root cause details"""
        engine = CorrelationEngine()

        issue, recommendations = engine._generate_root_cause_details(
            correlation_type=CorrelationType.TOKEN_LIMIT,
            correlations=[],
            trace_analysis=MagicMock(),
        )

        assert "token" in issue.lower()
        assert any("max_tokens" in rec.lower() for rec in recommendations)

    def test_generate_root_cause_details_routing(self):
        """Test generation of routing root cause details"""
        engine = CorrelationEngine()

        issue, recommendations = engine._generate_root_cause_details(
            correlation_type=CorrelationType.ROUTING_ISSUE,
            correlations=[],
            trace_analysis=MagicMock(),
        )

        assert "routing" in issue.lower()
        assert any("fallback" in rec.lower() for rec in recommendations)


class TestGenerateRecommendations:
    """Test suite for recommendation generation"""

    def test_generate_recommendations(self):
        """Test generation of prioritized recommendations"""
        engine = CorrelationEngine()

        root_causes = [
            RootCause(
                issue="High latency issue",
                severity=0.8,
                affected_metrics=[MetricType.COMPLETENESS],
                correlations=[],
                recommendations=["Use faster model", "Implement caching"],
                trace_evidence={"avg_confidence": 0.75},
            ),
            RootCause(
                issue="Token limit issue",
                severity=0.6,
                affected_metrics=[MetricType.ACCURACY],
                correlations=[],
                recommendations=["Increase max_tokens"],
                trace_evidence={"avg_confidence": 0.70},
            ),
        ]

        recommendations = engine._generate_recommendations(root_causes)

        assert len(recommendations) == 3  # 2 + 1 recommendations
        # First two should have priority 1 (higher severity)
        assert recommendations[0]["priority"] == 1
        assert recommendations[1]["priority"] == 1
        # Last one should have priority 2
        assert recommendations[2]["priority"] == 2
        assert recommendations[0]["severity"] == 0.8


class TestCalculateOverallConfidence:
    """Test suite for overall confidence calculation"""

    def test_calculate_overall_confidence_basic(self):
        """Test basic confidence calculation"""
        engine = CorrelationEngine()

        correlations = [
            Correlation(
                metric_type=MetricType.COMPLETENESS,
                metric_score=0.4,
                correlation_type=CorrelationType.PERFORMANCE_IMPACT,
                confidence=0.8,
                evidence=[],
                explanation="",
                impact=0.5,
            ),
            Correlation(
                metric_type=MetricType.ACCURACY,
                metric_score=0.3,
                correlation_type=CorrelationType.ERROR_RELATED,
                confidence=0.9,
                evidence=[],
                explanation="",
                impact=0.6,
            ),
        ]

        root_causes = [MagicMock(), MagicMock()]

        confidence = engine._calculate_overall_confidence(correlations, root_causes)

        # Average confidence: (0.8 + 0.9) / 2 = 0.85
        # Bonus: 2 root causes * 0.05 = 0.1
        # Total: 0.85 + 0.1 = 0.95
        assert confidence == pytest.approx(0.95)

    def test_calculate_overall_confidence_empty(self):
        """Test confidence is 0.0 when no correlations"""
        engine = CorrelationEngine()

        confidence = engine._calculate_overall_confidence([], [])

        assert confidence == 0.0

    def test_calculate_overall_confidence_max_cap(self):
        """Test confidence is capped at 1.0"""
        engine = CorrelationEngine()

        # Very high confidence correlations
        correlations = [
            Correlation(
                metric_type=MetricType.COMPLETENESS,
                metric_score=0.4,
                correlation_type=CorrelationType.PERFORMANCE_IMPACT,
                confidence=0.95,
                evidence=[],
                explanation="",
                impact=0.8,
            )
        ]

        # Many root causes for bonus
        root_causes = [MagicMock() for _ in range(10)]

        confidence = engine._calculate_overall_confidence(correlations, root_causes)

        assert confidence <= 1.0


class TestCorrelate:
    """Test suite for complete correlation workflow"""

    def test_correlate_basic(self):
        """Test basic correlation workflow"""
        engine = CorrelationEngine()

        evaluation_results = {
            "metric_results": {"completeness": {"score": 0.4}}  # Low score, below threshold
        }

        trace_analysis = TraceAnalysis(
            trace_id="trace-123",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1000.0,
            error_count=0,
        )

        trace_insights = {
            "llm_usage": {"avg_latency_ms": 5000},  # High latency
            "database_activity": {"avg_latency_ms": 100},
        }

        result = engine.correlate(
            evaluation_results=evaluation_results,
            trace_analysis=trace_analysis,
            trace_insights=trace_insights,
        )

        assert result.trace_id == "trace-123"
        assert len(result.correlations) > 0
        assert len(result.root_causes) > 0
        assert len(result.recommendations) > 0
        assert 0.0 <= result.overall_confidence <= 1.0

    def test_correlate_high_scores_no_correlation(self):
        """Test that high scores don't generate correlations"""
        engine = CorrelationEngine()

        evaluation_results = {
            "metric_results": {"completeness": {"score": 0.9}}  # High score, above threshold
        }

        trace_analysis = TraceAnalysis(
            trace_id="trace-good",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1000.0,
            error_count=0,
        )

        trace_insights = {"llm_usage": {"avg_latency_ms": 5000}}

        result = engine.correlate(
            evaluation_results=evaluation_results,
            trace_analysis=trace_analysis,
            trace_insights=trace_insights,
        )

        assert len(result.correlations) == 0
        assert len(result.root_causes) == 0
        assert len(result.recommendations) == 0

    def test_correlate_multiple_low_scores(self):
        """Test correlation with multiple low-scoring metrics"""
        engine = CorrelationEngine()

        evaluation_results = {
            "metric_results": {
                "completeness": {"score": 0.4},
                "accuracy": {"score": 0.3},
                "relevance": {"score": 0.5},
            }
        }

        # Create trace with high errors
        trace_analysis = TraceAnalysis(
            trace_id="trace-multi",
            root_span=None,
            all_spans=[
                ParsedSpan(
                    span_id="span-1",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name="llm",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=1000.0,
                    error={"cause": "Error"},
                ),
                ParsedSpan(
                    span_id="span-2",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name="llm2",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=1000.0,
                ),
            ],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=2000.0,
            error_count=1,
        )

        trace_insights = {
            "llm_usage": {"avg_latency_ms": 5000},
            "database_activity": {"avg_latency_ms": 100},
        }

        result = engine.correlate(
            evaluation_results=evaluation_results,
            trace_analysis=trace_analysis,
            trace_insights=trace_insights,
        )

        # Should find multiple correlations
        assert len(result.correlations) >= 2
        assert len(result.root_causes) >= 1
