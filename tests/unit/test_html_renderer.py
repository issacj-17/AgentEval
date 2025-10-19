"""
Unit tests for HTMLRenderer.

Tests the HTMLRenderer functionality with mock data.
"""

from pathlib import Path

import pytest

from agenteval.reporting.html_renderer import (
    CampaignContext,
    CampaignSummary,
    DashboardContext,
    HTMLRenderer,
    MetricSummary,
    SummaryContext,
    TemplateNotFoundError,
    TurnDetail,
    create_html_renderer,
)


@pytest.fixture
def html_renderer(tmp_path):
    """Create HTMLRenderer with temporary directories."""
    # Use actual template directory from the package
    template_dir = Path(__file__).parents[2] / "src" / "agenteval" / "reporting" / "templates"
    return HTMLRenderer(
        template_dir=template_dir,
        output_dir=tmp_path / "reports",
    )


@pytest.fixture
def sample_dashboard_context():
    """Sample dashboard context."""
    return DashboardContext(
        title="Test Dashboard",
        subtitle="Test Subtitle",
        generated_at="2025-01-01 00:00:00 UTC",
        region="us-east-1",
        environment="test",
        total_campaigns=2,
        overall_score=0.85,
        total_turns=5,
        completed_turns=4,
        failed_turns=1,
        success_rate=0.8,
        total_evaluations=10,
        total_metrics=5,
        campaigns=[
            CampaignSummary(
                id="campaign-1",
                type="persona",
                status="completed",
                status_class="success",
                score=0.90,
                score_class="",
                completed_turns=3,
                total_turns=3,
                duration="2.5m",
                created_at="2025-01-01 00:00",
            )
        ],
        campaign_labels=["Camp1", "Camp2"],
        campaign_scores=[85.0, 90.0],
        campaign_type_labels=["persona", "red_team"],
        campaign_type_counts=[1, 1],
        metric_labels=["accuracy", "relevance"],
        metric_scores=[85.0, 80.0],
        turn_trend_labels=["Camp1", "Camp2"],
        turn_trend_completed=[3, 1],
        turn_trend_failed=[0, 1],
    )


@pytest.fixture
def sample_campaign_context():
    """Sample campaign context."""
    return CampaignContext(
        campaign_id="campaign-1",
        campaign_type="persona",
        status="completed",
        status_class="success",
        overall_score=0.90,
        completed_turns=2,
        total_turns=2,
        duration="1.5m",
        created_at="2025-01-01 00:00",
        region="us-east-1",
        metrics=[
            MetricSummary(name="accuracy", score=0.9, score_class=""),
            MetricSummary(name="relevance", score=0.85, score_class=""),
        ],
        turns=[
            TurnDetail(
                number=1,
                status="completed",
                status_class="success",
                score=0.88,
                user_message="Hello",
                system_response="Hi there!",
                metrics=[MetricSummary(name="accuracy", score=0.9, score_class="")],
                trace_id="trace-123",
            )
        ],
        metric_labels=["accuracy", "relevance"],
        metric_scores=[90.0, 85.0],
        turn_labels=["Turn 1"],
        turn_scores=[88.0],
    )


@pytest.fixture
def sample_summary_context():
    """Sample summary context."""
    return SummaryContext(
        generated_at="2025-01-01 00:00:00 UTC",
        evaluation_period="2025-01-01 to 2025-01-02",
        total_campaigns=2,
        region="us-east-1",
        overview_text="Test overview",
        overall_score=0.85,
        overall_status="Good",
        overall_status_class="info",
        performance_assessment="good performance",
        total_turns=5,
        completed_turns=4,
        failed_turns=1,
        success_rate=0.8,
        total_evaluations=10,
        total_metrics=5,
        recommendations=[
            {
                "title": "Improve Quality",
                "text": "Focus on improving response quality.",
            }
        ],
        conclusion_text="Test conclusion",
    )


class TestHTMLRenderer:
    """Test suite for HTMLRenderer."""

    def test_initialization(self, tmp_path):
        """Test HTMLRenderer initialization."""
        template_dir = Path(__file__).parents[2] / "src" / "agenteval" / "reporting" / "templates"
        renderer = HTMLRenderer(
            template_dir=template_dir,
            output_dir=tmp_path,
        )

        assert renderer.template_dir == template_dir
        assert renderer.output_dir == tmp_path
        assert renderer.env is not None

    def test_render_dashboard(self, html_renderer, sample_dashboard_context):
        """Test rendering dashboard HTML."""
        # Execute
        output_path = html_renderer.render_dashboard(sample_dashboard_context)

        # Verify
        assert output_path.exists()
        assert output_path.name == "dashboard.html"

        # Verify content
        content = output_path.read_text()
        assert "AgentEval Dashboard" in content
        assert "Test Dashboard" in content
        assert "85.0%" in content  # overall score

    def test_render_campaign_detail(self, html_renderer, sample_campaign_context):
        """Test rendering campaign detail HTML."""
        # Execute
        output_path = html_renderer.render_campaign_detail(sample_campaign_context)

        # Verify
        assert output_path.exists()
        assert output_path.name == "campaign_campaign-1.html"

        # Verify content
        content = output_path.read_text()
        assert "Campaign Details" in content
        assert "campaign-1" in content
        assert "persona" in content

    def test_render_summary(self, html_renderer, sample_summary_context):
        """Test rendering executive summary HTML."""
        # Execute
        output_path = html_renderer.render_summary(sample_summary_context)

        # Verify
        assert output_path.exists()
        assert output_path.name == "summary.html"

        # Verify content
        content = output_path.read_text()
        assert "Executive Summary" in content
        assert "85.0%" in content

    def test_save_html(self, html_renderer, tmp_path):
        """Test saving HTML content."""
        html_content = "<html><body>Test</body></html>"

        # Execute
        output_path = html_renderer.save_html(html_content, "test.html")

        # Verify
        assert output_path.exists()
        assert output_path.name == "test.html"
        assert output_path.read_text() == html_content

    def test_calculate_score_class(self, html_renderer):
        """Test score class calculation."""
        assert html_renderer.calculate_score_class(0.9) == ""
        assert html_renderer.calculate_score_class(0.7) == "medium"
        assert html_renderer.calculate_score_class(0.5) == "low"

    def test_calculate_status_class(self, html_renderer):
        """Test status class calculation."""
        assert html_renderer.calculate_status_class("completed") == "success"
        assert html_renderer.calculate_status_class("running") == "info"
        assert html_renderer.calculate_status_class("failed") == "danger"
        assert html_renderer.calculate_status_class("pending") == "warning"

    def test_format_duration(self, html_renderer):
        """Test duration formatting."""
        assert html_renderer.format_duration(30) == "30s"
        assert html_renderer.format_duration(90) == "1.5m"
        assert html_renderer.format_duration(3600) == "1.0h"

    def test_custom_filters(self, html_renderer):
        """Test custom Jinja2 filters."""
        # Test format_score filter
        template_str = "{{ value|format_score }}"
        template = html_renderer.env.from_string(template_str)
        assert template.render(value=0.85) == "85.0%"

        # Test score_class filter
        template_str = "{{ value|score_class }}"
        template = html_renderer.env.from_string(template_str)
        assert template.render(value=0.9) == ""
        assert template.render(value=0.7) == "medium"
        assert template.render(value=0.5) == "low"

    def test_dataclass_to_dict(self, html_renderer):
        """Test dataclass to dictionary conversion."""
        metric = MetricSummary(name="accuracy", score=0.9, score_class="")
        result = html_renderer._dataclass_to_dict(metric)

        assert isinstance(result, dict)
        assert result["name"] == "accuracy"
        assert result["score"] == 0.9

    def test_dataclass_to_dict_nested(self, html_renderer):
        """Test nested dataclass conversion."""
        campaign = CampaignSummary(
            id="test",
            type="persona",
            status="completed",
            status_class="success",
            score=0.9,
            score_class="",
            completed_turns=3,
            total_turns=3,
            duration="1m",
            created_at="2025-01-01",
        )

        result = html_renderer._dataclass_to_dict(campaign)
        assert isinstance(result, dict)
        assert result["id"] == "test"
        assert result["type"] == "persona"

    def test_template_not_found_error(self, html_renderer):
        """Test template not found error handling."""
        with pytest.raises(TemplateNotFoundError):
            html_renderer.render_template("nonexistent.html", {"key": "value"})

    def test_factory_function(self):
        """Test factory function for creating renderer."""
        renderer = create_html_renderer()
        assert isinstance(renderer, HTMLRenderer)
        assert renderer.env is not None


class TestChartDataBuilder:
    """Test suite for ChartDataBuilder."""

    def test_builder_pattern(self):
        """Test builder pattern for chart data."""
        from agenteval.reporting.html_renderer import (
            create_chart_builder,
        )

        # Using builder
        builder = create_chart_builder("bar")
        chart_data = (
            builder.with_labels(["A", "B", "C"])
            .add_dataset("Dataset 1", [1, 2, 3], backgroundColor="red")
            .with_options({"responsive": True})
            .build()
        )

        assert chart_data.chart_type == "bar"
        assert chart_data.labels == ["A", "B", "C"]
        assert len(chart_data.datasets) == 1
        assert chart_data.datasets[0]["label"] == "Dataset 1"
        assert chart_data.datasets[0]["data"] == [1, 2, 3]
        assert chart_data.datasets[0]["backgroundColor"] == "red"
        assert chart_data.options == {"responsive": True}

    def test_multiple_datasets(self):
        """Test builder with multiple datasets."""
        from agenteval.reporting.html_renderer import create_chart_builder

        builder = create_chart_builder("line")
        chart_data = (
            builder.with_labels(["Jan", "Feb", "Mar"])
            .add_dataset("Series 1", [10, 20, 30])
            .add_dataset("Series 2", [15, 25, 35])
            .build()
        )

        assert len(chart_data.datasets) == 2
        assert chart_data.datasets[0]["label"] == "Series 1"
        assert chart_data.datasets[1]["label"] == "Series 2"
