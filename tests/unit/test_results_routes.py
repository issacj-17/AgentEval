"""
Unit tests for Results API routes.
"""

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, status

from agenteval.api.routes.results import (
    get_campaign_correlations,
    get_campaign_recommendations,
    get_campaign_report,
    get_campaign_summary,
    get_campaign_turns,
    get_turn_detail,
)
from agenteval.application.report_service import ReportGenerationError, ReportNotFoundError


class TestGetCampaignTurns:
    """Test suite for get_campaign_turns endpoint"""

    @pytest.mark.asyncio
    async def test_get_campaign_turns_success(self):
        """Test successful retrieval of campaign turns"""
        mock_service = AsyncMock()
        mock_service.get_campaign_turns = AsyncMock(
            return_value={
                "turns": [{"turn_id": "turn-1"}, {"turn_id": "turn-2"}],
                "total": 2,
                "limit": 50,
                "offset": 0,
            }
        )

        result = await get_campaign_turns(
            campaign_id="camp-123", limit=50, offset=0, report_service=mock_service
        )

        assert "turns" in result
        assert len(result["turns"]) == 2
        mock_service.get_campaign_turns.assert_called_once_with(
            campaign_id="camp-123", limit=50, offset=0
        )

    @pytest.mark.asyncio
    async def test_get_campaign_turns_not_found(self):
        """Test campaign not found error"""
        mock_service = AsyncMock()
        mock_service.get_campaign_turns = AsyncMock(
            side_effect=ReportNotFoundError("Campaign not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_campaign_turns(
                campaign_id="nonexistent", limit=50, offset=0, report_service=mock_service
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_campaign_turns_server_error(self):
        """Test internal server error handling"""
        mock_service = AsyncMock()
        mock_service.get_campaign_turns = AsyncMock(side_effect=Exception("Database error"))

        with pytest.raises(HTTPException) as exc_info:
            await get_campaign_turns(
                campaign_id="camp-123", limit=50, offset=0, report_service=mock_service
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


class TestGetTurnDetail:
    """Test suite for get_turn_detail endpoint"""

    @pytest.mark.asyncio
    async def test_get_turn_detail_success(self):
        """Test successful retrieval of turn detail"""
        mock_service = AsyncMock()
        mock_service.get_turn_detail = AsyncMock(
            return_value={
                "turn_id": "turn-1",
                "user_message": "Hello",
                "system_response": "Hi there",
                "evaluation": {"score": 0.9},
            }
        )

        result = await get_turn_detail(
            campaign_id="camp-123", turn_id="turn-1", report_service=mock_service
        )

        assert result["campaign_id"] == "camp-123"
        assert "turn" in result
        assert result["turn"]["turn_id"] == "turn-1"

    @pytest.mark.asyncio
    async def test_get_turn_detail_not_found(self):
        """Test turn not found error"""
        mock_service = AsyncMock()
        mock_service.get_turn_detail = AsyncMock(side_effect=ReportNotFoundError("Turn not found"))

        with pytest.raises(HTTPException) as exc_info:
            await get_turn_detail(
                campaign_id="camp-123", turn_id="nonexistent", report_service=mock_service
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND


class TestGetCampaignReport:
    """Test suite for get_campaign_report endpoint"""

    @pytest.mark.asyncio
    async def test_get_campaign_report_json(self):
        """Test JSON report generation"""
        mock_service = AsyncMock()
        mock_service.generate_campaign_report = AsyncMock(
            return_value={
                "report_url": "s3://bucket/report.json",
                "format": "json",
                "generated_at": "2024-01-01T00:00:00Z",
            }
        )

        result = await get_campaign_report(
            campaign_id="camp-123", format="json", report_service=mock_service
        )

        assert "report_url" in result
        assert result["format"] == "json"

    @pytest.mark.asyncio
    async def test_get_campaign_report_generation_error(self):
        """Test report generation error"""
        mock_service = AsyncMock()
        mock_service.generate_campaign_report = AsyncMock(
            side_effect=ReportGenerationError("Invalid format")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_campaign_report(
                campaign_id="camp-123", format="invalid", report_service=mock_service
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


class TestGetCampaignSummary:
    """Test suite for get_campaign_summary endpoint"""

    @pytest.mark.asyncio
    async def test_get_campaign_summary_success(self):
        """Test successful summary retrieval"""
        mock_service = AsyncMock()
        mock_service.get_campaign_summary = AsyncMock(
            return_value={
                "campaign_id": "camp-123",
                "total_turns": 10,
                "avg_score": 0.85,
                "status": "completed",
            }
        )

        result = await get_campaign_summary(campaign_id="camp-123", report_service=mock_service)

        assert result["campaign_id"] == "camp-123"
        assert result["total_turns"] == 10


class TestGetCampaignCorrelations:
    """Test suite for get_campaign_correlations endpoint"""

    @pytest.mark.asyncio
    async def test_get_campaign_correlations_success(self):
        """Test successful correlations retrieval"""
        mock_service = AsyncMock()
        mock_service.get_campaign_correlations = AsyncMock(
            return_value={
                "correlations": [
                    {"type": "latency", "strength": 0.9},
                    {"type": "error_rate", "strength": 0.7},
                ]
            }
        )

        result = await get_campaign_correlations(
            campaign_id="camp-123", report_service=mock_service
        )

        assert "correlations" in result
        assert len(result["correlations"]) == 2


class TestGetCampaignRecommendations:
    """Test suite for get_campaign_recommendations endpoint"""

    @pytest.mark.asyncio
    async def test_get_campaign_recommendations_success(self):
        """Test successful recommendations retrieval"""
        mock_service = AsyncMock()
        mock_service.get_campaign_recommendations = AsyncMock(
            return_value={
                "recommendations": [
                    {"priority": "high", "action": "Reduce latency"},
                    {"priority": "medium", "action": "Improve error handling"},
                ]
            }
        )

        result = await get_campaign_recommendations(
            campaign_id="camp-123", limit=20, report_service=mock_service
        )

        assert "recommendations" in result
        assert len(result["recommendations"]) == 2

    @pytest.mark.asyncio
    async def test_get_campaign_recommendations_with_limit(self):
        """Test recommendations with custom limit"""
        mock_service = AsyncMock()
        mock_service.get_campaign_recommendations = AsyncMock(return_value={"recommendations": []})

        result = await get_campaign_recommendations(
            campaign_id="camp-123", limit=5, report_service=mock_service
        )

        mock_service.get_campaign_recommendations.assert_called_once_with(
            campaign_id="camp-123", limit=5
        )
