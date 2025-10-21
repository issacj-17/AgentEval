"""
Unit tests for Dashboard Service turn metrics rendering fix.

Tests the fix for empty turn-metrics div in campaign HTML reports.
The issue was that evaluations embedded in turn data were not being extracted
when building TurnDetail objects for template rendering.
"""

from unittest.mock import Mock

import pytest

from agenteval.application.dashboard_service import DashboardService
from agenteval.reporting.html_renderer import TurnDetail


@pytest.fixture
def mock_html_renderer():
    """Mock HTML renderer."""
    renderer = Mock()
    renderer.calculate_score_class = Mock(side_effect=lambda x: "high" if x >= 0.8 else "low")
    renderer.calculate_status_class = Mock(return_value="success")
    return renderer


@pytest.fixture
def dashboard_service(mock_html_renderer):
    """Create DashboardService instance."""
    mock_results_service = Mock()
    service = DashboardService(
        results_service=mock_results_service, html_renderer=mock_html_renderer
    )
    return service


class TestTurnDetailsWithEmbeddedEvaluation:
    """Test turn details building with embedded evaluation data."""

    def test_build_turn_details_with_embedded_evaluation(self, dashboard_service):
        """Test that embedded evaluation in turn data is properly extracted."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "Test message",
                "system_response": "Test response",
                "trace_id": "trace-123",
                "evaluation": {
                    "overall_score": 0.9,
                    "metric_results": {
                        "accuracy": {"score": 0.95, "passed": True, "reasoning": "Good"},
                        "relevance": {"score": 0.85, "passed": True, "reasoning": "Relevant"},
                        "completeness": {"score": 0.90, "passed": True, "reasoning": "Complete"},
                    },
                },
            }
        ]
        evaluations = []  # Empty evaluations list (evaluation is embedded in turn)

        result = dashboard_service._build_turn_details(turns, evaluations)

        assert len(result) == 1
        turn_detail = result[0]
        assert isinstance(turn_detail, TurnDetail)
        assert turn_detail.number == 1
        assert turn_detail.status == "completed"

        # Check that metrics were extracted from embedded evaluation
        assert len(turn_detail.metrics) == 3
        metric_names = {m.name for m in turn_detail.metrics}
        assert metric_names == {"accuracy", "relevance", "completeness"}

        # Check metric scores
        accuracy_metric = next(m for m in turn_detail.metrics if m.name == "accuracy")
        assert accuracy_metric.score == 0.95

        relevance_metric = next(m for m in turn_detail.metrics if m.name == "relevance")
        assert relevance_metric.score == 0.85

    def test_build_turn_details_with_separate_evaluations(self, dashboard_service):
        """Test that separate evaluations list still works correctly."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "Test message",
                "system_response": "Test response",
            }
        ]
        evaluations = [
            {
                "turn_number": 1,
                "overall_score": 0.9,
                "metric_results": {
                    "accuracy": {"score": 0.95, "passed": True},
                    "relevance": {"score": 0.85, "passed": True},
                },
            }
        ]

        result = dashboard_service._build_turn_details(turns, evaluations)

        assert len(result) == 1
        turn_detail = result[0]

        # Check that metrics were extracted from separate evaluations list
        assert len(turn_detail.metrics) == 2
        metric_names = {m.name for m in turn_detail.metrics}
        assert metric_names == {"accuracy", "relevance"}

    def test_build_turn_details_with_both_sources_prefers_separate(self, dashboard_service):
        """Test that separate evaluations list is preferred over embedded."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "Test message",
                "system_response": "Test response",
                "evaluation": {
                    "overall_score": 0.5,
                    "metric_results": {
                        "accuracy": {"score": 0.50, "passed": False},
                    },
                },
            }
        ]
        evaluations = [
            {
                "turn_number": 1,
                "overall_score": 0.9,
                "metric_results": {
                    "accuracy": {"score": 0.95, "passed": True},
                },
            }
        ]

        result = dashboard_service._build_turn_details(turns, evaluations)

        assert len(result) == 1
        turn_detail = result[0]

        # Should use evaluation from separate list (score 0.95, not 0.50)
        assert len(turn_detail.metrics) == 1
        assert turn_detail.metrics[0].score == 0.95

    def test_build_turn_details_with_no_evaluation(self, dashboard_service):
        """Test that turns without evaluation still create TurnDetail objects."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "Test message",
                "system_response": "Test response",
            }
        ]
        evaluations = []

        result = dashboard_service._build_turn_details(turns, evaluations)

        assert len(result) == 1
        turn_detail = result[0]
        assert turn_detail.number == 1
        assert turn_detail.metrics == []  # No metrics without evaluation
        assert turn_detail.evaluation is None

    def test_build_turn_details_with_legacy_flat_scores(self, dashboard_service):
        """Test backwards compatibility with flat score values (not dicts)."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "Test",
                "system_response": "Response",
                "evaluation": {
                    "overall_score": 0.8,
                    "metric_results": {
                        "accuracy": 0.85,  # Flat score (not a dict)
                        "relevance": {"score": 0.90, "passed": True},  # Dict format
                    },
                },
            }
        ]
        evaluations = []

        result = dashboard_service._build_turn_details(turns, evaluations)

        assert len(result) == 1
        turn_detail = result[0]
        assert len(turn_detail.metrics) == 2

        # Check both formats work
        accuracy = next(m for m in turn_detail.metrics if m.name == "accuracy")
        assert accuracy.score == 0.85

        relevance = next(m for m in turn_detail.metrics if m.name == "relevance")
        assert relevance.score == 0.90

    def test_build_turn_details_multiple_turns_with_mixed_sources(self, dashboard_service):
        """Test multiple turns with some having embedded and some separate evaluations."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "First",
                "system_response": "Response 1",
                "evaluation": {
                    "overall_score": 0.9,
                    "metric_results": {"accuracy": {"score": 0.95}},
                },
            },
            {
                "turn_number": 2,
                "status": "completed",
                "user_message": "Second",
                "system_response": "Response 2",
                # No embedded evaluation
            },
        ]
        evaluations = [
            {
                "turn_number": 2,
                "overall_score": 0.8,
                "metric_results": {"accuracy": {"score": 0.85}},
            }
        ]

        result = dashboard_service._build_turn_details(turns, evaluations)

        assert len(result) == 2

        # Turn 1 should use embedded evaluation
        assert len(result[0].metrics) == 1
        assert result[0].metrics[0].score == 0.95

        # Turn 2 should use separate evaluation
        assert len(result[1].metrics) == 1
        assert result[1].metrics[0].score == 0.85

    def test_build_turn_details_preserves_evaluation_object(self, dashboard_service):
        """Test that full evaluation object is preserved for template use."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "Test",
                "system_response": "Response",
                "evaluation": {
                    "overall_score": 0.9,
                    "metric_results": {
                        "accuracy": {
                            "score": 0.95,
                            "passed": True,
                            "reasoning": "Very accurate",
                            "confidence": 0.98,
                            "evidence": ["Point 1", "Point 2"],
                        }
                    },
                },
            }
        ]
        evaluations = []

        result = dashboard_service._build_turn_details(turns, evaluations)

        assert len(result) == 1
        turn_detail = result[0]

        # Check that full evaluation is preserved
        assert turn_detail.evaluation is not None
        assert "metric_results" in turn_detail.evaluation
        assert "accuracy" in turn_detail.evaluation["metric_results"]

        # Check detailed metric data is available for judge reasoning display
        accuracy_result = turn_detail.evaluation["metric_results"]["accuracy"]
        assert accuracy_result["reasoning"] == "Very accurate"
        assert accuracy_result["confidence"] == 0.98
        assert accuracy_result["evidence"] == ["Point 1", "Point 2"]


class TestTurnMetricsScoreCalculation:
    """Test score calculation and classification."""

    def test_metric_score_class_calculation(self, dashboard_service):
        """Test that metric score classes are calculated correctly."""
        turns = [
            {
                "turn_number": 1,
                "status": "completed",
                "user_message": "Test",
                "system_response": "Response",
                "evaluation": {
                    "overall_score": 0.9,
                    "metric_results": {
                        "high_score": {"score": 0.95},
                        "low_score": {"score": 0.50},
                    },
                },
            }
        ]
        evaluations = []

        result = dashboard_service._build_turn_details(turns, evaluations)

        high_metric = next(m for m in result[0].metrics if m.name == "high_score")
        low_metric = next(m for m in result[0].metrics if m.name == "low_score")

        # Verify score class was calculated
        assert high_metric.score_class == "high"
        assert low_metric.score_class == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
