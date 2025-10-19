"""
Unit tests for Reporter Agent.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.agents.reporter_agent import (
    ReportContext,
    ReporterAgent,
)


@pytest.fixture
def mock_bedrock():
    """Create mock Bedrock client."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def reporter_agent():
    """Create Reporter Agent instance."""
    return ReporterAgent(
        model_id="anthropic.claude-haiku-4-5-20251001-v1:0",
        max_tokens=2000,
        temperature=0.3,
    )


@pytest.fixture
def sample_context():
    """Sample report context."""
    return ReportContext(
        campaign_data=[
            {
                "campaign_id": "camp-1",
                "campaign_type": "persona",
                "status": "completed",
                "created_at": "2025-01-01T00:00:00Z",
            }
        ],
        turn_data=[
            {
                "campaign_id": "camp-1",
                "turn_number": 1,
                "status": "completed",
            }
        ],
        evaluation_data=[
            {
                "campaign_id": "camp-1",
                "turn_number": 1,
                "score": 0.85,
                "metrics": {"accuracy": 0.9, "relevance": 0.8},
            }
        ],
        time_range={"start": "2025-01-01", "end": "2025-01-02"},
        region="us-east-1",
    )


class TestReporterAgent:
    """Test suite for Reporter Agent."""

    def test_initialization(self, reporter_agent):
        """Test agent initialization."""
        assert reporter_agent.agent_type == "reporter"
        assert reporter_agent.model_id == "anthropic.claude-haiku-4-5-20251001-v1:0"
        assert reporter_agent.max_tokens == 2000
        assert reporter_agent.temperature == 0.3

    def test_calculate_statistics(self, reporter_agent, sample_context):
        """Test statistics calculation."""
        stats = reporter_agent._calculate_statistics(sample_context)

        assert stats["total_campaigns"] == 1
        assert stats["total_turns"] == 1
        assert stats["total_evaluations"] == 1
        assert stats["completed_turns"] == 1
        assert stats["failed_turns"] == 0
        assert stats["success_rate"] == 1.0
        assert 0.8 <= stats["avg_score"] <= 0.9
        assert "accuracy" in stats["metric_averages"]
        assert "relevance" in stats["metric_averages"]

    def test_calculate_statistics_empty(self, reporter_agent):
        """Test statistics with empty data."""
        empty_context = ReportContext(
            campaign_data=[],
            turn_data=[],
            evaluation_data=[],
            time_range={},
            region="us-east-1",
        )

        stats = reporter_agent._calculate_statistics(empty_context)

        assert stats["total_campaigns"] == 0
        assert stats["total_turns"] == 0
        assert stats["avg_score"] == 0.0

    def test_build_executive_summary_prompt(self, reporter_agent, sample_context):
        """Test executive summary prompt building."""
        stats = reporter_agent._calculate_statistics(sample_context)
        prompt = reporter_agent._build_executive_summary_prompt(sample_context, stats)

        assert "executive summary" in prompt.lower()
        assert "us-east-1" in prompt
        assert "1" in prompt  # campaign count

    def test_build_key_findings_prompt(self, reporter_agent, sample_context):
        """Test key findings prompt building."""
        stats = reporter_agent._calculate_statistics(sample_context)
        prompt = reporter_agent._build_key_findings_prompt(sample_context, stats)

        assert "key findings" in prompt.lower()
        assert "accuracy" in prompt.lower()

    def test_build_recommendations_prompt(self, reporter_agent, sample_context):
        """Test recommendations prompt building."""
        stats = reporter_agent._calculate_statistics(sample_context)
        prompt = reporter_agent._build_recommendations_prompt(sample_context, stats)

        assert "recommendations" in prompt.lower()

    def test_build_report_sections(self, reporter_agent, sample_context):
        """Test report sections building."""
        stats = reporter_agent._calculate_statistics(sample_context)
        sections = reporter_agent._build_report_sections(sample_context, stats, "comprehensive")

        assert len(sections) > 0
        assert any(s.title == "Evaluation Overview" for s in sections)
        assert any(s.title == "Performance Metrics" for s in sections)

    def test_format_metrics(self, reporter_agent):
        """Test metrics formatting."""
        metrics = {"accuracy": 0.9, "relevance": 0.85, "clarity": 0.8}
        formatted = reporter_agent._format_metrics(metrics)

        assert "accuracy: 90.0%" in formatted
        assert "relevance: 85.0%" in formatted

    def test_format_campaign_types(self, reporter_agent):
        """Test campaign types formatting."""
        types = {"persona": 5, "red_team": 3}
        formatted = reporter_agent._format_campaign_types(types)

        assert "persona: 5 campaigns" in formatted
        assert "red_team: 3 campaigns" in formatted

    @pytest.mark.asyncio
    async def test_execute_requires_initialization(self, reporter_agent, sample_context):
        """Test that execute requires initialization."""
        # Without initialization, bedrock should be None
        assert reporter_agent.bedrock is None

    def test_statistics_with_failures(self, reporter_agent):
        """Test statistics calculation with failed turns."""
        context = ReportContext(
            campaign_data=[{"campaign_id": "c1", "campaign_type": "persona"}],
            turn_data=[
                {"campaign_id": "c1", "turn_number": 1, "status": "completed"},
                {"campaign_id": "c1", "turn_number": 2, "status": "failed"},
            ],
            evaluation_data=[
                {
                    "campaign_id": "c1",
                    "turn_number": 1,
                    "score": 0.8,
                    "metrics": {},
                }
            ],
            time_range={},
            region="us-east-1",
        )

        stats = reporter_agent._calculate_statistics(context)

        assert stats["completed_turns"] == 1
        assert stats["failed_turns"] == 1
        assert stats["success_rate"] == 0.5
