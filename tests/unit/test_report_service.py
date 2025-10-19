"""
Unit tests for ReportService

Tests report service business logic, format handling, and aggregations.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.application.report_service import (
    ReportGenerationError,
    ReportNotFoundError,
    ReportService,
)


class TestReportServiceInitialization:
    """Test ReportService initialization"""

    def test_init_with_dependencies(self):
        """Test service initializes with orchestrator and s3 client"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()

        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        assert service.orchestrator == mock_orchestrator
        assert service.s3 == mock_s3


class TestGenerateCampaignReport:
    """Test generate_campaign_report method"""

    @pytest.mark.asyncio
    async def test_generate_report_invalid_format(self):
        """Test that invalid format raises error"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        with pytest.raises(ReportGenerationError, match="Invalid report format"):
            await service.generate_campaign_report(
                campaign_id="campaign-123", report_format="invalid_format"
            )

    @pytest.mark.asyncio
    async def test_generate_report_campaign_not_found(self):
        """Test that missing campaign raises error"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(return_value=None)

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        with pytest.raises(ReportGenerationError, match="Campaign not found"):
            await service.generate_campaign_report(campaign_id="nonexistent", report_format="json")

    @pytest.mark.asyncio
    async def test_generate_report_success(self):
        """Test successful report generation"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={
                "campaign_id": "campaign-123",
                "campaign_type": "persona",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T01:00:00",
                "config": {},
                "stats": {},
            }
        )
        mock_orchestrator.dynamodb.get_campaign_turns = AsyncMock(
            return_value=[
                {
                    "turn_number": 1,
                    "turn_id": "turn-1",
                    "agent_type": "persona",
                    "user_message": "Test message",
                    "system_response": "Test response",
                    "timestamp": "2024-01-01T00:00:00",
                    "status": "completed",
                }
            ]
        )

        mock_s3 = MagicMock()
        mock_s3.store_report = AsyncMock(
            return_value=("s3://bucket/report.json", "https://example.com/download")
        )

        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)
        result = await service.generate_campaign_report(
            campaign_id="campaign-123", report_format="json"
        )

        assert result["campaign_id"] == "campaign-123"
        assert result["format"] == "json"
        assert result["s3_uri"] == "s3://bucket/report.json"
        assert result["download_url"] == "https://example.com/download"
        assert "generated_at" in result
        assert "expires_at" in result

        # Verify store_report was called
        mock_s3.store_report.assert_called_once()


class TestBuildReportData:
    """Test _build_report_data method"""

    def test_build_report_data_basic(self):
        """Test building report data with basic turn"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        campaign = {
            "campaign_id": "campaign-123",
            "campaign_type": "persona",
            "target_url": "http://example.com",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
            "config": {"max_turns": 10},
            "stats": {"turns_completed": 1},
        }

        turns = [
            {
                "turn_number": 1,
                "turn_id": "turn-1",
                "agent_type": "persona",
                "user_message": "Test",
                "system_response": "Response",
                "timestamp": "2024-01-01T00:00:00",
                "status": "completed",
            }
        ]

        result = service._build_report_data(campaign, turns)

        assert result["campaign_id"] == "campaign-123"
        assert result["turns_completed"] == 1
        assert len(result["turn_results"]) == 1
        assert result["turn_results"][0]["turn_number"] == 1

    def test_build_report_data_with_evaluation(self):
        """Test building report data with evaluation"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        campaign = {
            "campaign_id": "campaign-123",
            "campaign_type": "persona",
            "target_url": "http://example.com",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
        }

        turns = [
            {
                "turn_number": 1,
                "turn_id": "turn-1",
                "agent_type": "persona",
                "user_message": "Test",
                "system_response": "Response",
                "timestamp": "2024-01-01T00:00:00",
                "status": "completed",
                "evaluation": {"aggregate_scores": {"overall": 0.8, "quality": 0.9}},
            }
        ]

        result = service._build_report_data(campaign, turns)

        assert "evaluation_result" in result["turn_results"][0]
        assert result["turn_results"][0]["evaluation_result"]["aggregate_scores"]["overall"] == 0.8

    def test_build_report_data_with_persona_memory(self):
        """Test building report data with persona memory"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        campaign = {
            "campaign_id": "campaign-123",
            "campaign_type": "persona",
            "target_url": "http://example.com",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
        }

        turns = [
            {
                "turn_number": 1,
                "turn_id": "turn-1",
                "agent_type": "persona",
                "user_message": "Test",
                "system_response": "Response",
                "timestamp": "2024-01-01T00:00:00",
                "status": "completed",
                "persona_memory": {
                    "state": {"frustration_level": 5, "goal_progress": 0.5, "patience_level": 3}
                },
            }
        ]

        result = service._build_report_data(campaign, turns)

        assert "persona_state" in result["turn_results"][0]
        assert result["turn_results"][0]["persona_state"]["frustration_level"] == 5


class TestCalculateAggregateMetrics:
    """Test _calculate_aggregate_metrics method"""

    def test_calculate_metrics_empty_turns(self):
        """Test metrics calculation with no turns"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = service._calculate_aggregate_metrics([])

        assert result["overall_score"] == 0.0
        assert result["total_turns"] == 0
        assert result["success_rate"] == 0.0

    def test_calculate_metrics_with_turns(self):
        """Test metrics calculation with turns"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        turns = [
            {
                "status": "completed",
                "evaluation": {
                    "aggregate_scores": {
                        "overall": 0.8,
                        "quality": 0.9,
                        "safety": 0.95,
                        "helpfulness": 0.85,
                        "accuracy": 0.88,
                    }
                },
            },
            {
                "status": "completed",
                "evaluation": {
                    "aggregate_scores": {
                        "overall": 0.7,
                        "quality": 0.8,
                        "safety": 0.9,
                        "helpfulness": 0.75,
                        "accuracy": 0.78,
                    }
                },
            },
            {"status": "failed"},
        ]

        result = service._calculate_aggregate_metrics(turns)

        assert result["total_turns"] == 3
        assert result["completed_turns"] == 2
        assert result["failed_turns"] == 1
        assert result["success_rate"] == pytest.approx(2.0 / 3.0)
        assert result["overall_score"] == pytest.approx(0.75)  # (0.8 + 0.7) / 2
        assert result["quality_score"] == pytest.approx(0.85)  # (0.9 + 0.8) / 2


class TestCalculateExpiry:
    """Test _calculate_expiry method"""

    def test_calculate_expiry_default(self):
        """Test expiry calculation with default hours"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = service._calculate_expiry()

        # Should return ISO format datetime string
        assert isinstance(result, str)
        assert "T" in result

    def test_calculate_expiry_custom_hours(self):
        """Test expiry calculation with custom hours"""
        mock_orchestrator = MagicMock()
        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = service._calculate_expiry(hours=48)

        assert isinstance(result, str)
        assert "T" in result


class TestGetCampaignTurns:
    """Test get_campaign_turns method"""

    @pytest.mark.asyncio
    async def test_get_campaign_turns_not_found(self):
        """Test getting turns for non-existent campaign"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(return_value=None)

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        with pytest.raises(ReportNotFoundError, match="Campaign not found"):
            await service.get_campaign_turns("nonexistent")

    @pytest.mark.asyncio
    async def test_get_campaign_turns_success(self):
        """Test getting turns successfully"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123"}
        )
        mock_orchestrator.dynamodb.get_campaign_turns = AsyncMock(
            return_value=[{"turn_id": "turn-1"}, {"turn_id": "turn-2"}]
        )

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = await service.get_campaign_turns("campaign-123", limit=10, offset=0)

        assert result["campaign_id"] == "campaign-123"
        assert result["total"] == 2
        assert result["limit"] == 10
        assert result["offset"] == 0
        assert len(result["turns"]) == 2


class TestGetTurnDetail:
    """Test get_turn_detail method"""

    @pytest.mark.asyncio
    async def test_get_turn_detail_not_found(self):
        """Test getting non-existent turn"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_turn = AsyncMock(return_value=None)

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        with pytest.raises(ReportNotFoundError, match="Turn .* not found"):
            await service.get_turn_detail("campaign-123", "turn-999")

    @pytest.mark.asyncio
    async def test_get_turn_detail_success(self):
        """Test getting turn detail successfully"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_turn = AsyncMock(
            return_value={"turn_id": "turn-1", "turn_number": 1, "user_message": "Test message"}
        )

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = await service.get_turn_detail("campaign-123", "turn-1")

        assert result["turn_id"] == "turn-1"
        assert result["turn_number"] == 1


class TestGetCampaignSummary:
    """Test get_campaign_summary method"""

    @pytest.mark.asyncio
    async def test_get_campaign_summary_not_found(self):
        """Test getting summary for non-existent campaign"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(return_value=None)

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        with pytest.raises(ReportNotFoundError, match="Campaign not found"):
            await service.get_campaign_summary("nonexistent")

    @pytest.mark.asyncio
    async def test_get_campaign_summary_success(self):
        """Test getting campaign summary successfully"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={
                "campaign_id": "campaign-123",
                "campaign_type": "persona",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T01:00:00",
                "config": {"max_turns": 10},
            }
        )
        mock_orchestrator.dynamodb.get_campaign_turns = AsyncMock(
            return_value=[{"status": "completed"}, {"status": "completed"}]
        )

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = await service.get_campaign_summary("campaign-123")

        assert result["campaign_id"] == "campaign-123"
        assert result["campaign_type"] == "persona"
        assert result["turns_completed"] == 2
        assert "metrics" in result


class TestGetCampaignCorrelations:
    """Test get_campaign_correlations method"""

    @pytest.mark.asyncio
    async def test_get_correlations_no_turns(self):
        """Test getting correlations when no turns exist"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign_turns = AsyncMock(return_value=[])

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        with pytest.raises(ReportNotFoundError, match="No turns found"):
            await service.get_campaign_correlations("campaign-123")

    @pytest.mark.asyncio
    async def test_get_correlations_success(self):
        """Test getting correlations successfully"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign_turns = AsyncMock(
            return_value=[
                {
                    "turn_id": "turn-1",
                    "correlation": {
                        "correlations": [{"id": "corr-1"}],
                        "root_causes": [
                            {
                                "issue": "slow_response",
                                "severity": 0.8,
                                "recommendations": ["Optimize database"],
                            }
                        ],
                    },
                },
                {
                    "turn_id": "turn-2",
                    "correlation": {
                        "correlations": [{"id": "corr-2"}],
                        "root_causes": [
                            {
                                "issue": "slow_response",
                                "severity": 0.9,
                                "recommendations": ["Add caching"],
                            }
                        ],
                    },
                },
            ]
        )

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = await service.get_campaign_correlations("campaign-123")

        assert result["campaign_id"] == "campaign-123"
        assert result["total_correlations"] == 2
        assert result["total_root_causes"] == 2
        assert "slow_response" in result["root_cause_summary"]
        assert result["root_cause_summary"]["slow_response"]["count"] == 2


class TestGetCampaignRecommendations:
    """Test get_campaign_recommendations method"""

    @pytest.mark.asyncio
    async def test_get_recommendations_no_turns(self):
        """Test getting recommendations when no turns exist"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign_turns = AsyncMock(return_value=[])

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        with pytest.raises(ReportNotFoundError, match="No turns found"):
            await service.get_campaign_recommendations("campaign-123")

    @pytest.mark.asyncio
    async def test_get_recommendations_success(self):
        """Test getting recommendations successfully"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign_turns = AsyncMock(
            return_value=[
                {
                    "turn_id": "turn-1",
                    "correlation": {
                        "recommendations": [
                            {"recommendation": "Add caching", "priority": 1, "severity": 0.9},
                            {"recommendation": "Optimize queries", "priority": 2, "severity": 0.8},
                        ]
                    },
                },
                {
                    "turn_id": "turn-2",
                    "correlation": {
                        "recommendations": [
                            {"recommendation": "Add caching", "priority": 1, "severity": 0.9},
                            {"recommendation": "Add monitoring", "priority": 3, "severity": 0.7},
                        ]
                    },
                },
            ]
        )

        mock_s3 = MagicMock()
        service = ReportService(orchestrator=mock_orchestrator, s3_client=mock_s3)

        result = await service.get_campaign_recommendations("campaign-123", limit=10)

        assert result["campaign_id"] == "campaign-123"
        assert result["total_recommendations"] == 3  # Deduplicated
        # Should be sorted by priority, then severity
        assert result["recommendations"][0]["recommendation"] == "Add caching"


class TestReportServiceExceptions:
    """Test custom exception classes"""

    def test_report_not_found_error(self):
        """Test ReportNotFoundError exception"""
        error = ReportNotFoundError("Report not found")
        assert str(error) == "Report not found"
        assert isinstance(error, Exception)

    def test_report_generation_error(self):
        """Test ReportGenerationError exception"""
        error = ReportGenerationError("Generation failed")
        assert str(error) == "Generation failed"
        assert isinstance(error, Exception)
