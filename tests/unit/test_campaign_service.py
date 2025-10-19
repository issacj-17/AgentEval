"""
Unit tests for CampaignService

Tests campaign service business logic, validation, and exception handling.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.application.campaign_service import (
    CampaignNotFoundError,
    CampaignService,
    CampaignStateError,
    CampaignValidationError,
)
from agenteval.orchestration.campaign import CampaignType


class TestCampaignServiceInitialization:
    """Test CampaignService initialization"""

    def test_init_with_orchestrator(self):
        """Test service initializes with orchestrator"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        assert service.orchestrator == mock_orchestrator


class TestCreateCampaignValidation:
    """Test create_campaign validation logic"""

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_type(self):
        """Test that invalid campaign type raises error"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="Invalid campaign_type"):
            await service.create_campaign(
                campaign_type="invalid_type", target_url="http://example.com"
            )

    @pytest.mark.asyncio
    async def test_create_persona_campaign_without_persona_type(self):
        """Test that persona campaign requires persona_type"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="persona_type required"):
            await service.create_campaign(campaign_type="persona", target_url="http://example.com")

    @pytest.mark.asyncio
    async def test_create_persona_campaign_invalid_persona_type(self):
        """Test that invalid persona_type raises error"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="Invalid persona_type"):
            await service.create_campaign(
                campaign_type="persona",
                target_url="http://example.com",
                persona_type="nonexistent_persona",
            )

    @pytest.mark.asyncio
    async def test_create_redteam_campaign_invalid_attack_category(self):
        """Test that invalid attack categories raise error"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="Invalid attack_categories"):
            await service.create_campaign(
                campaign_type="red_team",
                target_url="http://example.com",
                attack_categories=["invalid_category"],
            )

    @pytest.mark.asyncio
    async def test_create_redteam_campaign_invalid_severity(self):
        """Test that invalid severity threshold raises error"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="Invalid severity_threshold"):
            await service.create_campaign(
                campaign_type="red_team",
                target_url="http://example.com",
                severity_threshold="invalid_severity",
            )

    @pytest.mark.asyncio
    async def test_create_combined_campaign_invalid_strategy(self):
        """Test that invalid combined strategy raises error"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="Invalid combined_strategy"):
            await service.create_campaign(
                campaign_type="combined",
                target_url="http://example.com",
                persona_type="frustrated_customer",
                combined_strategy="invalid_strategy",
            )

    @pytest.mark.asyncio
    async def test_create_combined_campaign_invalid_persona_weight(self):
        """Test that invalid persona_weight raises error"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="persona_weight must be between"):
            await service.create_campaign(
                campaign_type="combined",
                target_url="http://example.com",
                persona_type="frustrated_customer",
                combined_strategy="weighted",
                persona_weight=1.5,
            )


class TestCreateCampaignSuccess:
    """Test successful campaign creation"""

    @pytest.mark.asyncio
    async def test_create_redteam_campaign_success(self):
        """Test creating red team campaign successfully"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.create_campaign = AsyncMock(
            return_value={
                "campaign_id": "campaign-123",
                "campaign_type": "red_team",
                "target_url": "http://example.com",
                "status": "created",
                "created_at": datetime.utcnow().isoformat(),
            }
        )

        service = CampaignService(orchestrator=mock_orchestrator)

        result = await service.create_campaign(
            campaign_type="red_team",
            target_url="http://example.com",
            max_turns=5,
            use_mutations=True,
        )

        assert result["campaign_id"] == "campaign-123"
        assert result["campaign_type"] == "red_team"

        # Verify orchestrator was called with correct params
        mock_orchestrator.create_campaign.assert_called_once()
        call_kwargs = mock_orchestrator.create_campaign.call_args[1]
        assert call_kwargs["campaign_type"] == CampaignType.RED_TEAM
        assert call_kwargs["target_url"] == "http://example.com"
        assert call_kwargs["campaign_config"]["max_turns"] == 5
        assert call_kwargs["campaign_config"]["use_mutations"] is True


class TestGetCampaign:
    """Test get_campaign method"""

    @pytest.mark.asyncio
    async def test_get_campaign_found(self):
        """Test getting existing campaign"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "created"}
        )

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.get_campaign("campaign-123")

        assert result["campaign_id"] == "campaign-123"
        mock_orchestrator.dynamodb.get_campaign.assert_called_once_with("campaign-123")

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self):
        """Test getting non-existent campaign raises error"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(return_value=None)

        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignNotFoundError, match="Campaign not found"):
            await service.get_campaign("nonexistent")


class TestListCampaigns:
    """Test list_campaigns method"""

    @pytest.mark.asyncio
    async def test_list_campaigns_no_filter(self):
        """Test listing all campaigns"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.list_campaigns = AsyncMock(
            return_value=[
                {"campaign_id": "camp-1", "status": "created"},
                {"campaign_id": "camp-2", "status": "running"},
            ]
        )

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.list_campaigns()

        assert result["total"] == 2
        assert len(result["campaigns"]) == 2
        assert result["limit"] == 20
        assert result["offset"] == 0

    @pytest.mark.asyncio
    async def test_list_campaigns_with_status_filter(self):
        """Test listing campaigns with status filter"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.list_campaigns = AsyncMock(
            return_value=[{"campaign_id": "camp-1", "status": "completed"}]
        )

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.list_campaigns(status_filter="completed")

        assert result["total"] == 1
        mock_orchestrator.dynamodb.list_campaigns.assert_called_once_with(
            status_filter="completed", limit=20, offset=0
        )

    @pytest.mark.asyncio
    async def test_list_campaigns_invalid_status_filter(self):
        """Test that invalid status filter raises error"""
        mock_orchestrator = MagicMock()
        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignValidationError, match="Invalid status filter"):
            await service.list_campaigns(status_filter="invalid_status")


class TestStartCampaign:
    """Test start_campaign method"""

    @pytest.mark.asyncio
    async def test_start_campaign_success(self):
        """Test starting campaign successfully"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={
                "campaign_id": "campaign-123",
                "status": "created",
                "config": {"max_turns": 10},
            }
        )
        mock_orchestrator.run_campaign = AsyncMock()
        mock_orchestrator._track_task = MagicMock()

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.start_campaign("campaign-123")

        assert result["campaign_id"] == "campaign-123"
        assert result["status"] == "running"
        assert result["max_turns"] == 10

    @pytest.mark.asyncio
    async def test_start_campaign_already_running(self):
        """Test that starting running campaign raises error"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "running", "config": {}}
        )

        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignStateError, match="already running"):
            await service.start_campaign("campaign-123")

    @pytest.mark.asyncio
    async def test_start_campaign_not_found(self):
        """Test that starting non-existent campaign raises error"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(return_value=None)

        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignNotFoundError):
            await service.start_campaign("nonexistent")


class TestPauseCampaign:
    """Test pause_campaign method"""

    @pytest.mark.asyncio
    async def test_pause_campaign_success(self):
        """Test pausing running campaign"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "running"}
        )
        mock_orchestrator.dynamodb.update_campaign_status = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "paused"}
        )

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.pause_campaign("campaign-123")

        assert result["status"] == "paused"
        mock_orchestrator.dynamodb.update_campaign_status.assert_called_once_with(
            campaign_id="campaign-123", status="paused"
        )

    @pytest.mark.asyncio
    async def test_pause_campaign_not_running(self):
        """Test that pausing non-running campaign raises error"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "created"}
        )

        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignStateError, match="not running"):
            await service.pause_campaign("campaign-123")


class TestGetCampaignStatus:
    """Test get_campaign_status method"""

    @pytest.mark.asyncio
    async def test_get_campaign_status(self):
        """Test getting campaign status"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={
                "campaign_id": "campaign-123",
                "status": "running",
                "stats": {"turns_completed": 5},
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T01:00:00",
                "config": {"max_turns": 10},
            }
        )

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.get_campaign_status("campaign-123")

        assert result["campaign_id"] == "campaign-123"
        assert result["status"] == "running"
        assert result["stats"]["turns_completed"] == 5
        assert "created_at" in result
        assert "config" in result


class TestDeleteCampaign:
    """Test delete_campaign method"""

    @pytest.mark.asyncio
    async def test_delete_campaign_success_with_orchestrator_method(self):
        """Test deleting campaign using orchestrator delete method"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "completed"}
        )
        mock_orchestrator.delete_campaign = AsyncMock()

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.delete_campaign("campaign-123")

        assert result["campaign_id"] == "campaign-123"
        assert result["status"] == "deleted"
        mock_orchestrator.delete_campaign.assert_called_once_with("campaign-123")

    @pytest.mark.asyncio
    async def test_delete_campaign_success_without_orchestrator_method(self):
        """Test deleting campaign when orchestrator lacks delete method"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "completed"}
        )
        # Remove delete_campaign attribute to simulate missing method
        del mock_orchestrator.delete_campaign
        mock_orchestrator.dynamodb.update_campaign_status = AsyncMock()

        service = CampaignService(orchestrator=mock_orchestrator)
        result = await service.delete_campaign("campaign-123")

        assert result["status"] == "deleted"
        mock_orchestrator.dynamodb.update_campaign_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_running_campaign_raises_error(self):
        """Test that deleting running campaign raises error"""
        mock_orchestrator = MagicMock()
        mock_orchestrator.dynamodb = MagicMock()
        mock_orchestrator.dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "campaign-123", "status": "running"}
        )

        service = CampaignService(orchestrator=mock_orchestrator)

        with pytest.raises(CampaignStateError, match="Cannot delete running campaign"):
            await service.delete_campaign("campaign-123")


class TestCampaignServiceExceptions:
    """Test custom exception classes"""

    def test_campaign_validation_error(self):
        """Test CampaignValidationError exception"""
        error = CampaignValidationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, Exception)

    def test_campaign_not_found_error(self):
        """Test CampaignNotFoundError exception"""
        error = CampaignNotFoundError("Campaign not found")
        assert str(error) == "Campaign not found"
        assert isinstance(error, Exception)

    def test_campaign_state_error(self):
        """Test CampaignStateError exception"""
        error = CampaignStateError("Invalid state")
        assert str(error) == "Invalid state"
        assert isinstance(error, Exception)
