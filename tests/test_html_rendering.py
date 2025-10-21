"""
Unit tests for HTML template rendering with focus on judge reasoning display.

These tests verify that:
1. Templates correctly render evaluation data with dict access
2. Judge reasoning sections display with all required fields
3. Missing data is handled gracefully
"""

import pytest

from agenteval.reporting.html_renderer import (
    CampaignContext,
    HTMLRenderer,
    MetricSummary,
    TurnDetail,
)


@pytest.fixture
def sample_evaluation_data():
    """Sample evaluation data matching actual DynamoDB structure."""
    return {
        "eval_id": "test-campaign-turn-1",
        "turn_number": 1,
        "timestamp": "2025-10-21T00:00:00",
        "user_message": "I need help",
        "system_response": "I'm here to help you.",
        "metric_results": {
            "toxicity": {
                "score": 1.0,
                "passed": True,
                "confidence": 0.95,
                "reasoning": "The response is professional and helpful with no toxic content.",
                "evidence": ["I'm here to help you."],
            },
            "accuracy": {
                "score": 0.9,
                "passed": True,
                "confidence": 0.88,
                "reasoning": "Response addresses the user's request appropriately.",
                "evidence": ["I'm here to help"],
            },
            "relevance": {
                "score": 0.85,
                "passed": True,
                "confidence": 0.90,
                "reasoning": "Response is relevant to the user inquiry.",
                "evidence": [],
            },
        },
        "aggregate_scores": {"overall": 0.92, "safety": 1.0, "quality": 0.88},
        "pass_fail": {"all_passed": True, "failed_metrics": [], "critical_failures": []},
    }


@pytest.fixture
def html_renderer(tmp_path):
    """Create HTMLRenderer with temporary output directory."""
    return HTMLRenderer(output_dir=tmp_path)


def test_turn_detail_with_evaluation_dict(sample_evaluation_data):
    """Test that TurnDetail correctly stores evaluation as dict."""
    turn_detail = TurnDetail(
        number=1,
        status="completed",
        status_class="success",
        score=0.92,
        user_message="I need help",
        system_response="I'm here to help you.",
        metrics=[],
        trace_id="test-trace-id",
        evaluation=sample_evaluation_data,
    )

    assert turn_detail.evaluation is not None
    assert isinstance(turn_detail.evaluation, dict)
    assert "metric_results" in turn_detail.evaluation
    assert len(turn_detail.evaluation["metric_results"]) == 3


def test_dataclass_to_dict_preserves_evaluation(html_renderer, sample_evaluation_data):
    """Test that _dataclass_to_dict preserves evaluation field correctly."""
    turn_detail = TurnDetail(
        number=1,
        status="completed",
        status_class="success",
        score=0.92,
        user_message="Test",
        system_response="Response",
        metrics=[],
        evaluation=sample_evaluation_data,
    )

    turn_dict = html_renderer._dataclass_to_dict(turn_detail)

    assert "evaluation" in turn_dict
    assert turn_dict["evaluation"] is not None
    assert isinstance(turn_dict["evaluation"], dict)
    assert "metric_results" in turn_dict["evaluation"]
    assert len(turn_dict["evaluation"]["metric_results"]) == 3


def test_campaign_template_renders_judge_reasoning(html_renderer, sample_evaluation_data, tmp_path):
    """Test that campaign.html template renders judge reasoning section."""
    # Create a minimal campaign context
    context = CampaignContext(
        campaign_id="test-campaign-123",
        campaign_type="persona",
        status="completed",
        status_class="success",
        overall_score=0.92,
        completed_turns=1,
        total_turns=1,
        duration="00:05:30",
        created_at="2025-10-21 00:00:00",
        region="us-east-1",
        metrics=[
            MetricSummary(name="toxicity", score=1.0, score_class="high"),
            MetricSummary(name="accuracy", score=0.9, score_class="high"),
            MetricSummary(name="relevance", score=0.85, score_class="high"),
        ],
        turns=[
            TurnDetail(
                number=1,
                status="completed",
                status_class="success",
                score=0.92,
                user_message="I need help",
                system_response="I'm here to help you.",
                metrics=[
                    MetricSummary(name="toxicity", score=1.0, score_class="high"),
                    MetricSummary(name="accuracy", score=0.9, score_class="high"),
                ],
                trace_id="test-trace-id",
                evaluation=sample_evaluation_data,  # Include full evaluation
            )
        ],
        metric_labels=["toxicity", "accuracy", "relevance"],
        metric_scores=[1.0, 0.9, 0.85],
        turn_labels=["Turn 1"],
        turn_scores=[0.92],
    )

    # Render the campaign detail page
    output_path = html_renderer.render_campaign_detail(context)

    # Read the generated HTML
    with open(output_path) as f:
        html_content = f.read()

    # Verify judge reasoning section exists
    assert '<div class="judge-reasoning-section">' in html_content, (
        "Judge reasoning section should be present in HTML"
    )

    # Verify metric cards are rendered
    assert '<div class="reasoning-card">' in html_content, "Reasoning cards should be present"

    # Verify specific metric data is rendered
    assert '<span class="reasoning-metric-name">toxicity</span>' in html_content, (
        "Metric name should be rendered"
    )

    assert "100.0%" in html_content, "Toxicity score (100%) should be rendered"

    assert "The response is professional and helpful" in html_content, (
        "Reasoning text should be rendered"
    )

    assert "<strong>Confidence:</strong> 95%" in html_content, "Confidence should be rendered"

    assert "<strong>Evidence:</strong>" in html_content, "Evidence section should be rendered"

    # Check for HTML-escaped version of evidence
    assert "I&#39;m here to help you." in html_content or "I'm here to help you." in html_content, (
        "Evidence items should be rendered"
    )


def test_campaign_template_handles_missing_evaluation(html_renderer):
    """Test that template gracefully handles turns without evaluation data."""
    context = CampaignContext(
        campaign_id="test-campaign-456",
        campaign_type="persona",
        status="completed",
        status_class="success",
        overall_score=0.0,
        completed_turns=1,
        total_turns=1,
        duration="00:01:00",
        created_at="2025-10-21 00:00:00",
        region="us-east-1",
        metrics=[],
        turns=[
            TurnDetail(
                number=1,
                status="completed",
                status_class="success",
                score=0.0,
                user_message="Test",
                system_response="Response",
                metrics=[],
                evaluation=None,  # No evaluation data
            )
        ],
        metric_labels=[],
        metric_scores=[],
        turn_labels=["Turn 1"],
        turn_scores=[0.0],
    )

    # Should not raise an error
    output_path = html_renderer.render_campaign_detail(context)

    with open(output_path) as f:
        html_content = f.read()

    # Judge reasoning section should NOT be present
    assert '<div class="judge-reasoning-section">' not in html_content, (
        "Judge reasoning section should not be present when evaluation is None"
    )


def test_campaign_template_handles_empty_metric_results(html_renderer):
    """Test that template handles evaluation with empty metric_results."""
    evaluation_data = {
        "eval_id": "test-eval",
        "metric_results": {},  # Empty
        "aggregate_scores": {},
        "pass_fail": {},
    }

    context = CampaignContext(
        campaign_id="test-campaign-789",
        campaign_type="persona",
        status="completed",
        status_class="success",
        overall_score=0.0,
        completed_turns=1,
        total_turns=1,
        duration="00:01:00",
        created_at="2025-10-21 00:00:00",
        region="us-east-1",
        metrics=[],
        turns=[
            TurnDetail(
                number=1,
                status="completed",
                status_class="success",
                score=0.0,
                user_message="Test",
                system_response="Response",
                metrics=[],
                evaluation=evaluation_data,
            )
        ],
        metric_labels=[],
        metric_scores=[],
        turn_labels=["Turn 1"],
        turn_scores=[0.0],
    )

    # Should not raise an error
    output_path = html_renderer.render_campaign_detail(context)

    with open(output_path) as f:
        html_content = f.read()

    # When metric_results is empty dict, section should NOT render
    # Template condition: {% if turn.evaluation and turn.evaluation.get('metric_results') %}
    # In Jinja2, empty dict {} is falsy, so the condition fails
    assert '<div class="judge-reasoning-section">' not in html_content
    assert '<div class="reasoning-card">' not in html_content


def test_campaign_template_handles_missing_optional_fields(html_renderer):
    """Test template handles metrics with missing confidence or evidence."""
    evaluation_data = {
        "eval_id": "test-eval",
        "metric_results": {
            "basic_metric": {
                "score": 0.8,
                "passed": True,
                "reasoning": "This is the reasoning text",
                # No confidence or evidence fields
            }
        },
    }

    context = CampaignContext(
        campaign_id="test-campaign-abc",
        campaign_type="persona",
        status="completed",
        status_class="success",
        overall_score=0.8,
        completed_turns=1,
        total_turns=1,
        duration="00:01:00",
        created_at="2025-10-21 00:00:00",
        region="us-east-1",
        metrics=[],
        turns=[
            TurnDetail(
                number=1,
                status="completed",
                status_class="success",
                score=0.8,
                user_message="Test",
                system_response="Response",
                metrics=[],
                evaluation=evaluation_data,
            )
        ],
        metric_labels=[],
        metric_scores=[],
        turn_labels=["Turn 1"],
        turn_scores=[0.8],
    )

    output_path = html_renderer.render_campaign_detail(context)

    with open(output_path) as f:
        html_content = f.read()

    # Should render reasoning but not confidence or evidence sections
    assert "This is the reasoning text" in html_content
    assert "<strong>Confidence:</strong>" not in html_content
    assert "<strong>Evidence:</strong>" not in html_content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
