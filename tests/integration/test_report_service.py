"""
Integration tests for ReportService

Tests report generation, storage, and retrieval logic.
"""

from unittest.mock import AsyncMock

import pytest

from agenteval.application.report_service import (
    ReportGenerationError,
    ReportNotFoundError,
    ReportService,
)
from agenteval.aws.s3 import ReportFormat


class TestReportGeneration:
    """Test report generation operations"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator with DynamoDB"""
        orchestrator = AsyncMock()
        orchestrator.dynamodb = AsyncMock()
        return orchestrator

    @pytest.fixture
    def mock_s3(self):
        """Create mock S3 client"""
        s3 = AsyncMock()
        return s3

    @pytest.fixture
    def service(self, mock_orchestrator, mock_s3):
        """Create service instance"""
        return ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

    @pytest.fixture
    def sample_campaign(self):
        """Sample campaign data"""
        return {
            "campaign_id": "test-campaign-123",
            "campaign_type": "persona",
            "target_url": "https://api.example.com",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T02:00:00",
            "completed_at": "2024-01-01T02:00:00",
            "config": {"max_turns": 10, "persona_type": "frustrated_customer"},
            "stats": {"turns_completed": 10, "success_rate": 0.9},
        }

    @pytest.fixture
    def sample_turns(self):
        """Sample turn data"""
        return [
            {
                "turn_id": "turn-1",
                "turn_number": 1,
                "agent_type": "persona",
                "user_message": "I need help",
                "system_response": "How can I assist?",
                "timestamp": "2024-01-01T00:01:00",
                "status": "completed",
                "evaluation": {
                    "aggregate_scores": {
                        "overall": 0.85,
                        "quality": 0.9,
                        "safety": 0.95,
                        "helpfulness": 0.8,
                        "accuracy": 0.85,
                    }
                },
            },
            {
                "turn_id": "turn-2",
                "turn_number": 2,
                "agent_type": "persona",
                "user_message": "Still need help",
                "system_response": "Let me help",
                "timestamp": "2024-01-01T00:02:00",
                "status": "completed",
                "evaluation": {
                    "aggregate_scores": {
                        "overall": 0.9,
                        "quality": 0.85,
                        "safety": 1.0,
                        "helpfulness": 0.9,
                        "accuracy": 0.9,
                    }
                },
            },
        ]

    @pytest.mark.asyncio
    async def test_generate_report_json_success(
        self, service, mock_orchestrator, mock_s3, sample_campaign, sample_turns
    ):
        """Test generating JSON report successfully"""
        mock_orchestrator.dynamodb.get_campaign.return_value = sample_campaign
        mock_orchestrator.dynamodb.get_campaign_turns.return_value = sample_turns
        mock_s3.store_report.return_value = (
            "s3://reports/test-campaign-123/report.json",
            "https://presigned-url.example.com",
        )

        result = await service.generate_campaign_report(
            campaign_id="test-campaign-123", report_format="json"
        )

        assert result["campaign_id"] == "test-campaign-123"
        assert result["format"] == "json"
        assert result["s3_uri"] == "s3://reports/test-campaign-123/report.json"
        assert result["download_url"] == "https://presigned-url.example.com"
        assert "generated_at" in result
        assert "expires_at" in result

        # Verify S3 store was called with correct data
        mock_s3.store_report.assert_called_once()
        call_args = mock_s3.store_report.call_args
        assert call_args.kwargs["campaign_id"] == "test-campaign-123"
        assert call_args.kwargs["report_format"] == ReportFormat.JSON

    @pytest.mark.asyncio
    async def test_generate_report_csv_format(
        self, service, mock_orchestrator, mock_s3, sample_campaign, sample_turns
    ):
        """Test generating CSV report"""
        mock_orchestrator.dynamodb.get_campaign.return_value = sample_campaign
        mock_orchestrator.dynamodb.get_campaign_turns.return_value = sample_turns
        mock_s3.store_report.return_value = (
            "s3://reports/test-campaign-123/report.csv",
            "https://presigned-url.example.com",
        )

        result = await service.generate_campaign_report(
            campaign_id="test-campaign-123", report_format="csv"
        )

        assert result["format"] == "csv"
        call_args = mock_s3.store_report.call_args
        assert call_args.kwargs["report_format"] == ReportFormat.CSV

    @pytest.mark.asyncio
    async def test_generate_report_invalid_format(self, service):
        """Test error with invalid report format"""
        with pytest.raises(ReportGenerationError, match="Invalid report format"):
            await service.generate_campaign_report(
                campaign_id="test-123", report_format="invalid_format"
            )

    @pytest.mark.asyncio
    async def test_generate_report_campaign_not_found(self, service, mock_orchestrator):
        """Test error when campaign not found"""
        mock_orchestrator.dynamodb.get_campaign.return_value = None

        with pytest.raises(ReportGenerationError, match="Campaign not found"):
            await service.generate_campaign_report(campaign_id="nonexistent", report_format="json")

    @pytest.mark.asyncio
    async def test_report_data_structure(
        self, service, mock_orchestrator, mock_s3, sample_campaign, sample_turns
    ):
        """Test report data structure is correct"""
        mock_orchestrator.dynamodb.get_campaign.return_value = sample_campaign
        mock_orchestrator.dynamodb.get_campaign_turns.return_value = sample_turns
        mock_s3.store_report.return_value = ("s3://uri", "https://url")

        await service.generate_campaign_report("test-campaign-123", "json")

        # Check what data was passed to S3
        call_args = mock_s3.store_report.call_args
        report_data = call_args.kwargs["report_data"]

        assert report_data["campaign_id"] == "test-campaign-123"
        assert report_data["campaign_type"] == "persona"
        assert report_data["status"] == "completed"
        assert len(report_data["turn_results"]) == 2
        assert report_data["turns_completed"] == 2
        assert "aggregate_metrics" in report_data


class TestAggregateMetrics:
    """Test aggregate metrics calculation"""

    @pytest.fixture
    def service(self):
        orchestrator = AsyncMock()
        s3 = AsyncMock()
        return ReportService(orchestrator=orchestrator, s3_client=s3)

    def test_calculate_metrics_with_data(self, service):
        """Test metrics calculation with evaluation data"""
        turns = [
            {
                "status": "completed",
                "evaluation": {
                    "aggregate_scores": {
                        "overall": 0.8,
                        "quality": 0.85,
                        "safety": 0.9,
                        "helpfulness": 0.75,
                        "accuracy": 0.8,
                    }
                },
            },
            {
                "status": "completed",
                "evaluation": {
                    "aggregate_scores": {
                        "overall": 0.9,
                        "quality": 0.95,
                        "safety": 1.0,
                        "helpfulness": 0.85,
                        "accuracy": 0.9,
                    }
                },
            },
            {"status": "failed"},
        ]

        metrics = service._calculate_aggregate_metrics(turns)

        assert metrics["total_turns"] == 3
        assert metrics["completed_turns"] == 2
        assert metrics["failed_turns"] == 1
        assert abs(metrics["success_rate"] - 2 / 3) < 0.01
        assert abs(metrics["overall_score"] - 0.85) < 0.01  # (0.8 + 0.9) / 2
        assert abs(metrics["quality_score"] - 0.9) < 0.01  # (0.85 + 0.95) / 2
        assert abs(metrics["safety_score"] - 0.95) < 0.01  # (0.9 + 1.0) / 2

    def test_calculate_metrics_empty_turns(self, service):
        """Test metrics with no turns"""
        metrics = service._calculate_aggregate_metrics([])

        assert metrics["total_turns"] == 0
        assert metrics["completed_turns"] == 0
        assert metrics["failed_turns"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["overall_score"] == 0.0

    def test_calculate_metrics_no_evaluations(self, service):
        """Test metrics when turns have no evaluations"""
        turns = [{"status": "completed"}, {"status": "completed"}]

        metrics = service._calculate_aggregate_metrics(turns)

        assert metrics["total_turns"] == 2
        assert metrics["completed_turns"] == 2
        assert metrics["success_rate"] == 1.0
        assert metrics["overall_score"] == 0.0  # No evaluation data


class TestTurnRetrieval:
    """Test turn retrieval operations"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = AsyncMock()
        orchestrator.dynamodb = AsyncMock()
        return orchestrator

    @pytest.fixture
    def service(self, mock_orchestrator):
        s3 = AsyncMock()
        return ReportService(orchestrator=mock_orchestrator, s3_client=s3)

    @pytest.mark.asyncio
    async def test_get_campaign_turns_success(self, service, mock_orchestrator):
        """Test getting campaign turns"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {"campaign_id": "test-123"}
        mock_orchestrator.dynamodb.get_campaign_turns.return_value = [
            {"turn_id": "turn-1", "turn_number": 1},
            {"turn_id": "turn-2", "turn_number": 2},
        ]

        result = await service.get_campaign_turns("test-123", limit=10, offset=0)

        assert result["campaign_id"] == "test-123"
        assert result["total"] == 2
        assert len(result["turns"]) == 2
        assert result["limit"] == 10
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_get_campaign_turns_not_found(self, service, mock_orchestrator):
        """Test error when campaign not found"""
        mock_orchestrator.dynamodb.get_campaign.return_value = None

        with pytest.raises(ReportNotFoundError, match="Campaign not found"):
            await service.get_campaign_turns("nonexistent")

    @pytest.mark.asyncio
    async def test_get_turn_detail_success(self, service, mock_orchestrator):
        """Test getting specific turn detail"""
        mock_orchestrator.dynamodb.get_turn.return_value = {
            "turn_id": "turn-1",
            "campaign_id": "test-123",
            "turn_number": 1,
            "user_message": "Hello",
            "system_response": "Hi there",
        }

        result = await service.get_turn_detail("test-123", "turn-1")

        assert result["turn_id"] == "turn-1"
        assert result["campaign_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_get_turn_detail_not_found(self, service, mock_orchestrator):
        """Test error when turn not found"""
        mock_orchestrator.dynamodb.get_turn.return_value = None

        with pytest.raises(ReportNotFoundError, match="Turn .* not found"):
            await service.get_turn_detail("test-123", "nonexistent")


class TestCampaignSummary:
    """Test campaign summary operations"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = AsyncMock()
        orchestrator.dynamodb = AsyncMock()
        return orchestrator

    @pytest.fixture
    def service(self, mock_orchestrator):
        s3 = AsyncMock()
        return ReportService(orchestrator=mock_orchestrator, s3_client=s3)

    @pytest.mark.asyncio
    async def test_get_campaign_summary_success(self, service, mock_orchestrator):
        """Test getting campaign summary"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "campaign_type": "persona",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T02:00:00",
            "config": {"max_turns": 10},
        }
        mock_orchestrator.dynamodb.get_campaign_turns.return_value = [
            {"turn_number": 1, "status": "completed"},
            {"turn_number": 2, "status": "completed"},
        ]

        result = await service.get_campaign_summary("test-123")

        assert result["campaign_id"] == "test-123"
        assert result["campaign_type"] == "persona"
        assert result["status"] == "completed"
        assert result["turns_completed"] == 2
        assert "metrics" in result
        assert "config" in result

    @pytest.mark.asyncio
    async def test_get_campaign_summary_not_found(self, service, mock_orchestrator):
        """Test error when campaign not found"""
        mock_orchestrator.dynamodb.get_campaign.return_value = None

        with pytest.raises(ReportNotFoundError, match="Campaign not found"):
            await service.get_campaign_summary("nonexistent")
