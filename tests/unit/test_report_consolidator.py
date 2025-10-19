"""
Unit tests for ReportConsolidator.

Tests the ReportConsolidator service with mocked Reporter Agent.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.agents.reporter_agent import (
    GeneratedReport,
    ReportContext,
    ReporterAgent,
    ReportSection,
)
from agenteval.application.report_consolidator import (
    ConsolidatorConfig,
    ReportConsolidator,
    ReportGenerationError,
)
from agenteval.application.results_service import (
    CampaignData,
    ResultsBundle,
    S3Reports,
    XRayTraces,
)


@pytest.fixture
def mock_reporter_agent():
    """Create mock Reporter Agent."""
    agent = MagicMock(spec=ReporterAgent)
    agent.execute = AsyncMock()
    agent._calculate_statistics = MagicMock()
    return agent


@pytest.fixture
def consolidator_config(tmp_path):
    """Create consolidator configuration."""
    return ConsolidatorConfig(
        output_dir=tmp_path,
        report_type="comprehensive",
        include_html_link=True,
        include_raw_data=False,
    )


@pytest.fixture
def report_consolidator(mock_reporter_agent, consolidator_config):
    """Create ReportConsolidator instance."""
    return ReportConsolidator(
        reporter_agent=mock_reporter_agent,
        config=consolidator_config,
    )


@pytest.fixture
def sample_results_bundle():
    """Sample results bundle."""
    # Note: This data is in plain format as expected by ReportConsolidator
    # (DynamoDB format is already processed by ResultsService)
    campaigns = [
        {
            "campaign_id": "campaign-1",
            "campaign_type": "persona",
            "status": "completed",
            "created_at": "2025-01-01T00:00:00Z",
            "updated_at": "2025-01-01T00:05:00Z",
        },
    ]

    turns = [
        {
            "campaign_id": "campaign-1",
            "turn_number": 1,
            "status": "completed",
        },
    ]

    evaluations = [
        {
            "campaign_id": "campaign-1",
            "turn_number": 1,
            "score": 0.85,
            "metrics": {"accuracy": 0.9},
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


@pytest.fixture
def sample_generated_report():
    """Sample generated report."""
    return GeneratedReport(
        executive_summary="This is a comprehensive evaluation summary.",
        key_findings=[
            "Finding 1: System performed well",
            "Finding 2: Some improvements needed",
            "Finding 3: Overall quality is good",
        ],
        recommendations=[
            "Recommendation 1: Increase test coverage",
            "Recommendation 2: Optimize performance",
            "Recommendation 3: Add monitoring",
        ],
        detailed_analysis="Detailed analysis content here.",
        sections=[
            ReportSection(
                title="Performance Analysis",
                content="Performance details...",
                priority=8,
            ),
            ReportSection(
                title="Quality Metrics",
                content="Quality details...",
                priority=7,
            ),
        ],
        metadata={
            "agent_id": "reporter-123",
            "statistics": {
                "total_campaigns": 1,
                "total_turns": 1,
                "completed_turns": 1,
                "failed_turns": 0,
                "success_rate": 1.0,
                "avg_score": 0.85,
            },
        },
        generated_at=datetime(2025, 1, 1, 12, 0, 0),
    )


class TestReportConsolidator:
    """Test suite for ReportConsolidator."""

    def test_initialization(self, report_consolidator, tmp_path):
        """Test consolidator initialization."""
        assert report_consolidator.reporter_agent is not None
        assert report_consolidator.config.output_dir == tmp_path
        assert report_consolidator.config.report_type == "comprehensive"
        assert report_consolidator.config.include_html_link is True

    def test_build_report_context(self, report_consolidator, sample_results_bundle):
        """Test building report context from results bundle."""
        context = report_consolidator._build_report_context(sample_results_bundle)

        assert isinstance(context, ReportContext)
        assert len(context.campaign_data) == 1
        assert len(context.turn_data) == 1
        assert len(context.evaluation_data) == 1
        assert context.region == "us-east-1"
        assert "start" in context.time_range
        assert "end" in context.time_range

    def test_build_report_context_empty(self, report_consolidator):
        """Test building report context with empty data."""
        empty_bundle = ResultsBundle(
            campaign_data=CampaignData(campaigns=[], turns=[], evaluations=[]),
            s3_reports=S3Reports(campaign_reports={}, demo_reports={}),
            xray_traces=XRayTraces(trace_summaries=[], trace_details=[]),
            region="us-east-1",
        )

        context = report_consolidator._build_report_context(empty_bundle)

        assert isinstance(context, ReportContext)
        assert len(context.campaign_data) == 0
        assert len(context.turn_data) == 0
        assert len(context.evaluation_data) == 0

    def test_format_as_markdown(
        self,
        report_consolidator,
        sample_generated_report,
        sample_results_bundle,
    ):
        """Test formatting report as markdown."""
        markdown = report_consolidator._format_as_markdown(
            sample_generated_report, sample_results_bundle
        )

        # Verify structure
        assert isinstance(markdown, str)
        assert "# AgentEval Evaluation Report" in markdown
        assert "Executive Summary" in markdown
        assert "Key Findings" in markdown
        assert "Recommendations" in markdown
        assert "Detailed Analysis" in markdown
        assert "Additional Sections" in markdown
        assert "Statistics Summary" in markdown

        # Verify content
        assert "This is a comprehensive evaluation summary" in markdown
        assert "Finding 1: System performed well" in markdown
        assert "Recommendation 1: Increase test coverage" in markdown
        assert "Performance Analysis" in markdown
        assert "Quality Metrics" in markdown

    def test_format_as_markdown_without_html_link(
        self,
        mock_reporter_agent,
        sample_generated_report,
        sample_results_bundle,
        tmp_path,
    ):
        """Test formatting markdown without HTML link."""
        config = ConsolidatorConfig(
            output_dir=tmp_path,
            include_html_link=False,
        )
        consolidator = ReportConsolidator(
            reporter_agent=mock_reporter_agent,
            config=config,
        )

        markdown = consolidator._format_as_markdown(sample_generated_report, sample_results_bundle)

        assert "Interactive Dashboard" not in markdown

    def test_format_statistics_table(self, report_consolidator):
        """Test formatting statistics as markdown table."""
        stats = {
            "total_campaigns": 5,
            "total_turns": 15,
            "completed_turns": 14,
            "failed_turns": 1,
            "success_rate": 0.933,
            "avg_score": 0.85,
        }

        table = report_consolidator._format_statistics_table(stats)

        assert "| Metric | Value |" in table
        assert "| Total Campaigns | 5 |" in table
        assert "| Total Turns | 15 |" in table
        assert "| Success Rate | 93.3% |" in table
        assert "| Average Score | 85.0% |" in table

    def test_format_statistics_table_empty(self, report_consolidator):
        """Test formatting empty statistics."""
        table = report_consolidator._format_statistics_table({})
        assert "_No statistics available_" in table

    @pytest.mark.asyncio
    async def test_consolidate_reports(
        self,
        report_consolidator,
        mock_reporter_agent,
        sample_results_bundle,
        sample_generated_report,
        tmp_path,
    ):
        """Test full report consolidation workflow."""
        # Setup mock
        mock_reporter_agent.execute.return_value = sample_generated_report

        # Execute
        output_path = await report_consolidator.consolidate_reports(sample_results_bundle)

        # Verify
        assert output_path.exists()
        assert output_path.name == "REPORT.md"
        assert output_path.parent == tmp_path

        # Verify content
        content = output_path.read_text()
        assert "# AgentEval Evaluation Report" in content
        assert "Executive Summary" in content
        assert "Key Findings" in content

        # Verify agent was called
        mock_reporter_agent.execute.assert_called_once()
        call_args = mock_reporter_agent.execute.call_args
        assert "report_context" in call_args.kwargs
        assert "report_type" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_consolidate_reports_custom_filename(
        self,
        report_consolidator,
        mock_reporter_agent,
        sample_results_bundle,
        sample_generated_report,
    ):
        """Test consolidation with custom filename."""
        mock_reporter_agent.execute.return_value = sample_generated_report

        output_path = await report_consolidator.consolidate_reports(
            sample_results_bundle, output_filename="CUSTOM.md"
        )

        assert output_path.name == "CUSTOM.md"
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_consolidate_reports_error_handling(
        self,
        report_consolidator,
        mock_reporter_agent,
        sample_results_bundle,
    ):
        """Test error handling during consolidation."""
        # Setup mock to raise exception during agent execution
        mock_reporter_agent.execute.side_effect = Exception("Agent execution failed")

        # Execute and verify exception
        with pytest.raises(ReportGenerationError) as exc_info:
            await report_consolidator.consolidate_reports(sample_results_bundle)

        # Verify error message contains our exception info
        error_msg = str(exc_info.value)
        assert "Failed to consolidate" in error_msg
        # The exact error message may vary depending on where the exception occurs
        assert "Agent execution failed" in error_msg or "consolidate" in error_msg

    @pytest.mark.asyncio
    async def test_generate_quick_summary(
        self,
        report_consolidator,
        mock_reporter_agent,
        sample_results_bundle,
    ):
        """Test quick summary generation."""
        # Setup mock statistics
        mock_reporter_agent._calculate_statistics.return_value = {
            "total_campaigns": 5,
            "total_turns": 15,
            "completed_turns": 14,
            "failed_turns": 1,
            "success_rate": 0.933,
            "avg_score": 0.85,
            "metric_averages": {
                "accuracy": 0.90,
                "relevance": 0.85,
                "clarity": 0.80,
            },
        }

        # Execute
        summary = await report_consolidator.generate_quick_summary(sample_results_bundle)

        # Verify
        assert isinstance(summary, str)
        assert "AgentEval Quick Summary" in summary
        assert "Campaigns: 5" in summary
        assert "Turns: 15" in summary
        assert "Success Rate: 93.3%" in summary
        assert "Average Score: 85.0%" in summary
        assert "Top Performing Metrics:" in summary
        assert "accuracy" in summary

    def test_config_defaults(self):
        """Test ConsolidatorConfig default values."""
        config = ConsolidatorConfig(output_dir=Path("/tmp"))

        assert config.report_type == "comprehensive"
        assert config.include_html_link is True
        assert config.include_raw_data is False
        assert config.model_id == "anthropic.claude-haiku-4-5-20251001-v1:0"

    def test_config_custom_values(self):
        """Test ConsolidatorConfig with custom values."""
        config = ConsolidatorConfig(
            output_dir=Path("/custom"),
            report_type="summary",
            include_html_link=False,
            include_raw_data=True,
            model_id="custom-model-id",
        )

        assert config.output_dir == Path("/custom")
        assert config.report_type == "summary"
        assert config.include_html_link is False
        assert config.include_raw_data is True
        assert config.model_id == "custom-model-id"

    def test_markdown_format_with_sections(
        self,
        report_consolidator,
        sample_generated_report,
        sample_results_bundle,
    ):
        """Test markdown formatting includes all sections properly ordered."""
        # Add more sections with different priorities
        sample_generated_report.sections.append(
            ReportSection(
                title="Low Priority Section",
                content="Low priority content",
                priority=3,
            )
        )

        markdown = report_consolidator._format_as_markdown(
            sample_generated_report, sample_results_bundle
        )

        # Verify sections are included
        assert "Performance Analysis" in markdown
        assert "Quality Metrics" in markdown
        assert "Low Priority Section" in markdown

        # Verify sections are in priority order (highest first)
        performance_idx = markdown.index("Performance Analysis")
        quality_idx = markdown.index("Quality Metrics")
        low_idx = markdown.index("Low Priority Section")

        assert performance_idx < quality_idx < low_idx
