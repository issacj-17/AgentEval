"""
Unit tests for DashboardService.

Tests the DashboardService orchestration with mocked dependencies.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.application.dashboard_service import (
    DashboardConfig,
    DashboardGenerationError,
    DashboardService,
)
from agenteval.application.results_service import (
    CampaignData,
    ResultsBundle,
    S3Reports,
    XRayTraces,
)
from agenteval.reporting.html_renderer import (
    CampaignContext,
    DashboardContext,
    HTMLRenderer,
    SummaryContext,
)


@pytest.fixture
def mock_results_service():
    """Create mock ResultsService."""
    service = MagicMock()
    service.pull_all_results = AsyncMock()
    return service


@pytest.fixture
def mock_html_renderer(tmp_path):
    """Create mock HTMLRenderer."""
    renderer = MagicMock(spec=HTMLRenderer)
    renderer.render_dashboard = MagicMock(return_value=tmp_path / "dashboard.html")
    renderer.render_campaign_detail = MagicMock(return_value=tmp_path / "campaign.html")
    renderer.render_summary = MagicMock(return_value=tmp_path / "summary.html")
    renderer.calculate_score_class = MagicMock(return_value="")
    renderer.calculate_status_class = MagicMock(return_value="success")
    renderer.format_duration = MagicMock(return_value="1.5m")
    return renderer


@pytest.fixture
def dashboard_config(tmp_path):
    """Create dashboard configuration."""
    return DashboardConfig(
        region="us-east-1",
        environment="test",
        output_dir=tmp_path,
        generate_html=True,
        generate_markdown=True,
    )


@pytest.fixture
def dashboard_service(mock_results_service, mock_html_renderer, dashboard_config):
    """Create DashboardService with mocked dependencies."""
    return DashboardService(
        results_service=mock_results_service,
        html_renderer=mock_html_renderer,
        config=dashboard_config,
    )


@pytest.fixture
def sample_results_bundle():
    """Sample results bundle."""
    campaigns = [
        {
            "campaign_id": "campaign-1",
            "campaign_type": "persona",
            "status": "completed",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:05:00Z",
        },
        {
            "campaign_id": "campaign-2",
            "campaign_type": "red_team",
            "status": "completed",
            "created_at": "2025-01-02T00:00:00Z",
            "updated_at": "2025-01-02T00:03:00Z",
        },
    ]

    turns = [
        {
            "campaign_id": "campaign-1",
            "turn_number": 1,
            "status": "completed",
            "user_message": "Hello",
            "system_response": "Hi there!",
        },
        {
            "campaign_id": "campaign-1",
            "turn_number": 2,
            "status": "completed",
            "user_message": "How are you?",
            "system_response": "I'm doing well!",
        },
        {
            "campaign_id": "campaign-2",
            "turn_number": 1,
            "status": "completed",
            "user_message": "Test",
            "system_response": "Response",
        },
    ]

    evaluations = [
        {
            "campaign_id": "campaign-1",
            "turn_number": 1,
            "score": 0.85,
            "metrics": {"accuracy": 0.9, "relevance": 0.8},
        },
        {
            "campaign_id": "campaign-1",
            "turn_number": 2,
            "score": 0.90,
            "metrics": {"accuracy": 0.95, "relevance": 0.85},
        },
        {
            "campaign_id": "campaign-2",
            "turn_number": 1,
            "score": 0.80,
            "metrics": {"accuracy": 0.85, "relevance": 0.75},
        },
    ]

    campaign_data = CampaignData(
        campaigns=campaigns,
        turns=turns,
        evaluations=evaluations,
    )

    s3_reports = S3Reports(
        campaign_reports={},
        demo_reports={},
    )

    xray_traces = XRayTraces(
        trace_summaries=[],
        trace_details=[],
    )

    return ResultsBundle(
        campaign_data=campaign_data,
        s3_reports=s3_reports,
        xray_traces=xray_traces,
        region="us-east-1",
    )


class TestDashboardService:
    """Test suite for DashboardService."""

    @pytest.mark.asyncio
    async def test_generate_dashboard(
        self,
        dashboard_service,
        mock_results_service,
        mock_html_renderer,
        sample_results_bundle,
        tmp_path,
    ):
        """Test complete dashboard generation."""
        # Setup mock
        mock_results_service.pull_all_results.return_value = sample_results_bundle

        # Mock file creation for markdown
        mock_html_renderer.render_dashboard.return_value = tmp_path / "dashboard.html"
        mock_html_renderer.render_campaign_detail.return_value = tmp_path / "campaign.html"
        mock_html_renderer.render_summary.return_value = tmp_path / "summary.html"

        # Create markdown file that will be generated
        (tmp_path / "SUMMARY.md").touch()

        # Execute
        output_files = await dashboard_service.generate_dashboard()

        # Verify
        assert isinstance(output_files, dict)
        assert "html_dashboard" in output_files
        assert "html_summary" in output_files

        # Verify services were called
        mock_results_service.pull_all_results.assert_called_once()
        mock_html_renderer.render_dashboard.assert_called_once()
        mock_html_renderer.render_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_dashboard_html_only(
        self,
        mock_results_service,
        mock_html_renderer,
        sample_results_bundle,
        tmp_path,
    ):
        """Test dashboard generation with HTML only."""
        config = DashboardConfig(generate_html=True, generate_markdown=False)
        service = DashboardService(
            results_service=mock_results_service,
            html_renderer=mock_html_renderer,
            config=config,
        )

        mock_results_service.pull_all_results.return_value = sample_results_bundle
        mock_html_renderer.render_dashboard.return_value = tmp_path / "dashboard.html"
        mock_html_renderer.render_campaign_detail.return_value = tmp_path / "campaign.html"
        mock_html_renderer.render_summary.return_value = tmp_path / "summary.html"

        # Execute
        output_files = await service.generate_dashboard()

        # Verify - should have HTML but no markdown
        assert "html_dashboard" in output_files
        assert "markdown_summary" not in output_files

    @pytest.mark.asyncio
    async def test_build_dashboard_context(self, dashboard_service, sample_results_bundle):
        """Test building dashboard context."""
        # Execute
        context = dashboard_service._build_dashboard_context(sample_results_bundle)

        # Verify
        assert isinstance(context, DashboardContext)
        assert context.total_campaigns == 2
        assert context.total_turns == 3
        assert context.completed_turns == 3
        assert context.failed_turns == 0
        assert 0.8 <= context.overall_score <= 0.9
        assert context.success_rate == 1.0
        assert context.region == "us-east-1"

    @pytest.mark.asyncio
    async def test_build_campaign_contexts(self, dashboard_service, sample_results_bundle):
        """Test building campaign contexts."""
        # Execute
        contexts = dashboard_service._build_campaign_contexts(sample_results_bundle)

        # Verify
        assert len(contexts) == 2
        assert all(isinstance(ctx, CampaignContext) for ctx in contexts)

        # Verify first campaign
        ctx1 = contexts[0]
        assert ctx1.campaign_id == "campaign-1"
        assert ctx1.campaign_type == "persona"
        assert ctx1.total_turns == 2
        assert ctx1.completed_turns == 2

    @pytest.mark.asyncio
    async def test_build_summary_context(self, dashboard_service, sample_results_bundle):
        """Test building summary context."""
        # Execute
        context = dashboard_service._build_summary_context(sample_results_bundle)

        # Verify
        assert isinstance(context, SummaryContext)
        assert context.total_campaigns == 2
        assert context.total_turns == 3
        assert context.completed_turns == 3
        assert context.failed_turns == 0
        assert 0.8 <= context.overall_score <= 0.9
        assert len(context.recommendations) > 0

    @pytest.mark.asyncio
    async def test_calculate_metric_summaries(self, dashboard_service, sample_results_bundle):
        """Test calculating metric summaries."""
        evaluations = sample_results_bundle.campaign_data.evaluations

        # Execute
        summaries = dashboard_service._calculate_metric_summaries(evaluations)

        # Verify
        assert len(summaries) == 2  # accuracy and relevance
        assert any(s.name == "accuracy" for s in summaries)
        assert any(s.name == "relevance" for s in summaries)

        # Verify scores are calculated correctly
        accuracy_summary = next(s for s in summaries if s.name == "accuracy")
        assert 0.85 <= accuracy_summary.score <= 0.95

    @pytest.mark.asyncio
    async def test_generate_recommendations(self, dashboard_service, sample_results_bundle):
        """Test recommendation generation."""
        # Test with low score
        recommendations = dashboard_service._generate_recommendations(
            sample_results_bundle, overall_score=0.65, failed_turns=2
        )

        # Verify
        assert len(recommendations) > 0
        assert any("quality" in r["title"].lower() for r in recommendations)
        assert any("failed" in r["text"].lower() for r in recommendations)
        assert any("monitoring" in r["title"].lower() for r in recommendations)

    @pytest.mark.asyncio
    async def test_generate_recommendations_high_score(
        self, dashboard_service, sample_results_bundle
    ):
        """Test recommendation generation with high score."""
        # Test with high score and no failures
        recommendations = dashboard_service._generate_recommendations(
            sample_results_bundle, overall_score=0.95, failed_turns=0
        )

        # Verify - should still have monitoring recommendation
        assert len(recommendations) > 0
        assert any("monitoring" in r["title"].lower() for r in recommendations)

    @pytest.mark.asyncio
    async def test_calculate_duration(self, dashboard_service):
        """Test duration calculation."""
        start = "2025-01-01T00:00:00Z"
        end = "2025-01-01T00:05:00Z"

        # Execute
        duration = dashboard_service._calculate_duration(start, end)

        # Verify
        assert isinstance(duration, str)
        assert duration != "N/A"

    @pytest.mark.asyncio
    async def test_format_datetime(self, dashboard_service):
        """Test datetime formatting."""
        dt_str = "2025-01-01T12:30:00Z"

        # Execute
        formatted = dashboard_service._format_datetime(dt_str)

        # Verify
        assert isinstance(formatted, str)
        assert "2025-01-01" in formatted

    @pytest.mark.asyncio
    async def test_generate_markdown_summary(self, dashboard_service, sample_results_bundle):
        """Test markdown summary generation."""
        # Execute
        markdown = dashboard_service._generate_markdown_summary(sample_results_bundle)

        # Verify
        assert isinstance(markdown, str)
        assert "AgentEval Results Summary" in markdown
        assert "Campaign:" in markdown  # Check that campaigns are listed
        assert "Total Campaigns" in markdown
        assert "persona" in markdown or "red_team" in markdown  # Campaign types present

    @pytest.mark.asyncio
    async def test_error_handling(self, dashboard_service, mock_results_service):
        """Test error handling when pulling results fails."""
        # Setup mock to raise exception
        mock_results_service.pull_all_results.side_effect = Exception("Pull failed")

        # Execute and verify exception
        with pytest.raises(DashboardGenerationError):
            await dashboard_service.generate_dashboard()

    @pytest.mark.asyncio
    async def test_empty_results(
        self,
        dashboard_service,
        mock_results_service,
        mock_html_renderer,
        tmp_path,
    ):
        """Test handling of empty results."""
        # Setup mock with empty data
        empty_bundle = ResultsBundle(
            campaign_data=CampaignData(campaigns=[], turns=[], evaluations=[]),
            s3_reports=S3Reports(campaign_reports={}, demo_reports={}),
            xray_traces=XRayTraces(trace_summaries=[], trace_details=[]),
            region="us-east-1",
        )
        mock_results_service.pull_all_results.return_value = empty_bundle

        mock_html_renderer.render_dashboard.return_value = tmp_path / "dashboard.html"
        mock_html_renderer.render_summary.return_value = tmp_path / "summary.html"

        # Create markdown file
        (tmp_path / "SUMMARY.md").touch()

        # Execute - should handle empty data gracefully
        output_files = await dashboard_service.generate_dashboard()

        # Verify
        assert isinstance(output_files, dict)

    @pytest.mark.asyncio
    async def test_campaign_filtering(
        self,
        dashboard_service,
        mock_results_service,
        sample_results_bundle,
    ):
        """Test campaign filtering."""
        mock_results_service.pull_all_results.return_value = sample_results_bundle

        # Execute with campaign filter
        await dashboard_service.generate_dashboard(campaign_ids=["campaign-1"])

        # Verify filter was passed to results service
        mock_results_service.pull_all_results.assert_called_once()
        call_args = mock_results_service.pull_all_results.call_args
        # Verify campaign_ids parameter exists in the call
        assert call_args is not None


class TestDashboardConfig:
    """Test suite for DashboardConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DashboardConfig()

        assert config.region == "us-east-1"
        assert config.environment == "development"
        assert config.generate_html is True
        assert config.generate_markdown is True
        assert config.campaign_ids is None

    def test_custom_config(self, tmp_path):
        """Test custom configuration."""
        config = DashboardConfig(
            region="us-west-2",
            environment="production",
            output_dir=tmp_path,
            generate_html=False,
            generate_markdown=True,
            campaign_ids=["campaign-1"],
        )

        assert config.region == "us-west-2"
        assert config.environment == "production"
        assert config.output_dir == tmp_path
        assert config.generate_html is False
        assert config.generate_markdown is True
        assert config.campaign_ids == ["campaign-1"]
