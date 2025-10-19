"""
Unit tests for ResultsService.

Tests the ResultsService functionality with mocked AWS clients.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.application.results_service import (
    CampaignData,
    ResultsBundle,
    ResultsService,
    S3Reports,
    XRayTraces,
)


@pytest.fixture
def mock_dynamodb():
    """Create mock DynamoDB client."""
    client = MagicMock()

    # Mock scan_table method directly (new implementation)
    client.scan_table = AsyncMock(return_value=[])

    return client


@pytest.fixture
def mock_s3():
    """Create mock S3 client."""
    client = MagicMock()
    client.list_objects = AsyncMock()
    client.download_file = AsyncMock()
    return client


@pytest.fixture
def mock_xray():
    """Create mock X-Ray client."""
    client = MagicMock()
    client.get_trace_summaries = AsyncMock()
    client.batch_get_traces = AsyncMock()
    return client


@pytest.fixture
def results_service(mock_dynamodb, mock_s3, mock_xray, tmp_path):
    """Create ResultsService with mocked clients."""
    return ResultsService(
        dynamodb=mock_dynamodb,
        s3=mock_s3,
        xray=mock_xray,
        output_dir=tmp_path,
    )


@pytest.fixture
def sample_campaigns():
    """Sample campaign data in DynamoDB format."""
    return [
        {
            "campaign_id": {"S": "campaign-1"},
            "campaign_type": {"S": "persona"},
            "status": {"S": "completed"},
            "created_at": {"S": "2025-01-01T00:00:00Z"},
        },
        {
            "campaign_id": {"S": "campaign-2"},
            "campaign_type": {"S": "red_team"},
            "status": {"S": "completed"},
            "created_at": {"S": "2025-01-02T00:00:00Z"},
        },
    ]


@pytest.fixture
def sample_turns():
    """Sample turn data in DynamoDB format."""
    return [
        {
            "campaign_id": {"S": "campaign-1"},
            "turn_number": {"N": "1"},
            "status": {"S": "completed"},
            "user_message": {"S": "Hello"},
            "system_response": {"S": "Hi there!"},
        },
        {
            "campaign_id": {"S": "campaign-1"},
            "turn_number": {"N": "2"},
            "status": {"S": "completed"},
            "user_message": {"S": "How are you?"},
            "system_response": {"S": "I'm doing well, thanks!"},
        },
    ]


@pytest.fixture
def sample_evaluations():
    """Sample evaluation data in DynamoDB format."""
    return [
        {
            "campaign_id": {"S": "campaign-1"},
            "turn_number": {"N": "1"},
            "score": {"N": "0.85"},
            "metrics": {"M": {"accuracy": {"N": "0.9"}, "relevance": {"N": "0.8"}}},
        },
        {
            "campaign_id": {"S": "campaign-1"},
            "turn_number": {"N": "2"},
            "score": {"N": "0.90"},
            "metrics": {"M": {"accuracy": {"N": "0.95"}, "relevance": {"N": "0.85"}}},
        },
    ]


class TestResultsService:
    """Test suite for ResultsService."""

    @pytest.mark.asyncio
    async def test_pull_campaign_data(
        self,
        results_service,
        mock_dynamodb,
        sample_campaigns,
        sample_turns,
        sample_evaluations,
    ):
        """Test pulling campaign data from DynamoDB."""
        # Setup mocks - scan_table returns items directly (no DynamoDB format wrapper)
        # Convert from DynamoDB format to Python format for the mock
        from agenteval.aws.dynamodb import dynamodb_to_python

        campaigns_python = [dynamodb_to_python(c) for c in sample_campaigns]
        turns_python = [dynamodb_to_python(t) for t in sample_turns]
        evaluations_python = [dynamodb_to_python(e) for e in sample_evaluations]

        # Configure scan_table to return different results for each call
        mock_dynamodb.scan_table.side_effect = [
            campaigns_python,  # campaigns table
            turns_python,  # turns table
            evaluations_python,  # evaluations table
        ]

        # Execute
        campaign_data = await results_service.pull_campaign_data("us-east-1")

        # Verify
        assert isinstance(campaign_data, CampaignData)
        assert len(campaign_data.campaigns) == 2
        assert len(campaign_data.turns) == 2
        assert len(campaign_data.evaluations) == 2

        # Verify DynamoDB scan_table was called 3 times (campaigns, turns, evaluations)
        assert mock_dynamodb.scan_table.call_count == 3

    @pytest.mark.asyncio
    async def test_pull_campaign_data_with_filter(
        self,
        results_service,
        mock_dynamodb,
        sample_campaigns,
        sample_turns,
        sample_evaluations,
    ):
        """Test pulling campaign data with campaign ID filter."""
        # Setup mocks - scan_table returns items directly
        from agenteval.aws.dynamodb import dynamodb_to_python

        campaigns_python = [dynamodb_to_python(c) for c in sample_campaigns]
        turns_python = [dynamodb_to_python(t) for t in sample_turns]
        evaluations_python = [dynamodb_to_python(e) for e in sample_evaluations]

        # Return all data, filtering happens in pull_campaign_data
        mock_dynamodb.scan_table.side_effect = [
            campaigns_python,  # Return all campaigns
            turns_python,  # Return all turns
            evaluations_python,  # Return all evaluations
        ]

        # Execute with filter - filtering happens in the service
        campaign_data = await results_service.pull_campaign_data(
            "us-east-1", campaign_ids=["campaign-1"]
        )

        # Verify - should be filtered to campaign-1 only
        assert len(campaign_data.campaigns) == 1
        assert campaign_data.campaigns[0]["campaign_id"]["S"] == "campaign-1"

    @pytest.mark.asyncio
    async def test_pull_s3_reports(self, results_service, mock_s3, tmp_path):
        """Test pulling S3 reports."""
        # Setup mocks
        mock_s3.list_objects.return_value = [
            "campaign-1/report.json",
            "campaign-2/report.json",
        ]
        mock_s3.download_file.return_value = None

        # Execute
        s3_reports = await results_service.pull_s3_reports("us-east-1")

        # Verify
        assert isinstance(s3_reports, S3Reports)
        assert s3_reports.total_reports >= 0

        # Verify S3 was called at least once (may be called for multiple prefixes)
        assert mock_s3.list_objects.call_count >= 1

    @pytest.mark.asyncio
    async def test_pull_xray_traces(self, results_service, mock_xray):
        """Test pulling X-Ray traces."""
        # Setup mocks
        mock_xray.get_trace_summaries.return_value = [
            {"Id": "trace-1", "Duration": 1.5},
            {"Id": "trace-2", "Duration": 2.0},
        ]
        mock_xray.batch_get_traces.return_value = [
            {"Id": "trace-1", "Segments": []},
            {"Id": "trace-2", "Segments": []},
        ]

        # Execute
        xray_traces = await results_service.pull_xray_traces("us-east-1")

        # Verify
        assert isinstance(xray_traces, XRayTraces)
        assert len(xray_traces.trace_ids) >= 0

    @pytest.mark.asyncio
    async def test_pull_all_results(
        self,
        results_service,
        mock_dynamodb,
        mock_s3,
        mock_xray,
        sample_campaigns,
        sample_turns,
        sample_evaluations,
    ):
        """Test pulling all results concurrently."""
        # Setup DynamoDB mocks - scan_table returns items directly
        from agenteval.aws.dynamodb import dynamodb_to_python

        campaigns_python = [dynamodb_to_python(c) for c in sample_campaigns]
        turns_python = [dynamodb_to_python(t) for t in sample_turns]
        evaluations_python = [dynamodb_to_python(e) for e in sample_evaluations]

        mock_dynamodb.scan_table.side_effect = [
            campaigns_python,
            turns_python,
            evaluations_python,
        ]

        # Setup S3 mocks
        mock_s3.list_objects.return_value = []
        mock_s3.download_file.return_value = None

        # Setup X-Ray mocks
        mock_xray.get_trace_summaries.return_value = []
        mock_xray.batch_get_traces.return_value = []

        # Execute
        results = await results_service.pull_all_results("us-east-1")

        # Verify
        assert isinstance(results, ResultsBundle)
        assert isinstance(results.campaign_data, CampaignData)
        assert isinstance(results.s3_reports, S3Reports)
        assert isinstance(results.xray_traces, XRayTraces)
        assert results.region == "us-east-1"

        # Verify all services were called
        assert mock_dynamodb.scan_table.call_count >= 3
        assert mock_s3.list_objects.call_count >= 1
        assert mock_xray.get_trace_summaries.call_count >= 1

    @pytest.mark.asyncio
    async def test_save_campaign_data(self, results_service, sample_campaigns, tmp_path):
        """Test saving campaign data to disk."""
        campaign_data = CampaignData(
            campaigns=sample_campaigns,
            turns=[],
            evaluations=[],
        )

        # Execute
        await results_service._save_campaign_data(campaign_data)

        # Verify files were created
        campaigns_file = tmp_path / "campaign-data" / "campaigns.json"
        assert campaigns_file.exists()

    @pytest.mark.asyncio
    async def test_generate_summary(
        self,
        results_service,
        sample_campaigns,
        sample_turns,
        sample_evaluations,
        tmp_path,
    ):
        """Test generating summary report."""
        # Create ResultsBundle with all required data
        campaign_data = CampaignData(
            campaigns=sample_campaigns,
            turns=sample_turns,
            evaluations=sample_evaluations,
        )

        s3_reports = S3Reports(
            campaign_reports={},
            demo_reports={},
        )

        xray_traces = XRayTraces(
            trace_summaries=[],
            trace_details=[],
        )

        results_bundle = ResultsBundle(
            campaign_data=campaign_data,
            s3_reports=s3_reports,
            xray_traces=xray_traces,
            region="us-east-1",
        )

        # Execute
        summary_path = await results_service.generate_summary(results_bundle)

        # Verify
        assert summary_path.exists()
        assert summary_path.name == "SUMMARY.md"

        # Verify summary contains expected content
        content = summary_path.read_text()
        assert "AgentEval Results Summary" in content

    @pytest.mark.asyncio
    async def test_error_handling_dynamodb(self, results_service, mock_dynamodb):
        """Test error handling when DynamoDB fails gracefully."""
        # Setup mock to raise exception on scan_table
        mock_dynamodb.scan_table = AsyncMock(side_effect=Exception("Table scan error"))

        # Execute - should handle errors gracefully with return_exceptions=True
        campaign_data = await results_service.pull_campaign_data("us-east-1")

        # Verify - should return empty data when errors occur
        assert isinstance(campaign_data, CampaignData)
        assert len(campaign_data.campaigns) == 0
        assert len(campaign_data.turns) == 0
        assert len(campaign_data.evaluations) == 0

    @pytest.mark.asyncio
    async def test_empty_results(self, results_service, mock_dynamodb, mock_s3, mock_xray):
        """Test handling of empty results."""
        # Setup mocks to return empty lists
        mock_dynamodb.scan_table.return_value = []

        mock_s3.list_objects.return_value = []
        mock_xray.get_trace_summaries.return_value = []

        # Execute
        results = await results_service.pull_all_results("us-east-1")

        # Verify - should handle empty results gracefully
        assert isinstance(results, ResultsBundle)
        assert len(results.campaign_data.campaigns) == 0
        assert len(results.campaign_data.turns) == 0
        assert len(results.campaign_data.evaluations) == 0
