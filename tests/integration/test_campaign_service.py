"""
Integration tests for CampaignService

Tests the service layer business logic with mocked infrastructure dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.application.campaign_service import (
    CampaignNotFoundError,
    CampaignService,
    CampaignStateError,
    CampaignValidationError,
)


class TestCampaignServiceCreation:
    """Test campaign creation with validation"""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator"""
        orchestrator = AsyncMock()
        orchestrator.dynamodb = AsyncMock()
        orchestrator.create_campaign = AsyncMock(
            return_value={
                "campaign_id": "test-campaign-123",
                "campaign_type": "persona",
                "status": "created",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "config": {"max_turns": 10},
                "stats": {},
            }
        )
        return orchestrator

    @pytest.fixture
    def service(self, mock_orchestrator):
        """Create service instance"""
        return CampaignService(orchestrator=mock_orchestrator)

    @pytest.mark.asyncio
    async def test_create_persona_campaign_success(self, service, mock_orchestrator):
        """Test creating a valid persona campaign"""
        with patch("agenteval.application.campaign_service.get_persona_library") as mock_lib:
            mock_persona_lib = MagicMock()
            mock_persona_lib.get_persona.return_value = {"name": "Frustrated Customer"}
            mock_lib.return_value = mock_persona_lib

            result = await service.create_campaign(
                campaign_type="persona",
                target_url="https://api.example.com",
                max_turns=10,
                persona_type="frustrated_customer",
                initial_goal="Get help with billing",
            )

            assert result["campaign_id"] == "test-campaign-123"
            assert result["campaign_type"] == "persona"
            mock_orchestrator.create_campaign.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_persona_campaign_missing_type(self, service):
        """Test validation error when persona_type is missing"""
        with pytest.raises(CampaignValidationError, match="persona_type required"):
            await service.create_campaign(
                campaign_type="persona", target_url="https://api.example.com", max_turns=10
            )

    @pytest.mark.asyncio
    async def test_create_persona_campaign_invalid_type(self, service):
        """Test validation error with invalid persona type"""
        with patch("agenteval.application.campaign_service.get_persona_library") as mock_lib:
            mock_persona_lib = MagicMock()
            mock_persona_lib.get_persona.return_value = None
            mock_persona_lib.list_persona_ids.return_value = ["frustrated_customer", "curious_user"]
            mock_lib.return_value = mock_persona_lib

            with pytest.raises(CampaignValidationError, match="Invalid persona_type"):
                await service.create_campaign(
                    campaign_type="persona",
                    target_url="https://api.example.com",
                    max_turns=10,
                    persona_type="invalid_persona",
                )

    @pytest.mark.asyncio
    async def test_create_red_team_campaign_success(self, service, mock_orchestrator):
        """Test creating a valid red team campaign"""
        mock_orchestrator.create_campaign.return_value["campaign_type"] = "red_team"

        result = await service.create_campaign(
            campaign_type="red_team",
            target_url="https://api.example.com",
            max_turns=10,
            attack_categories=["injection", "jailbreak"],
            severity_threshold="high",
            use_mutations=True,
        )

        assert result["campaign_type"] == "red_team"
        mock_orchestrator.create_campaign.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_red_team_invalid_category(self, service):
        """Test validation error with invalid attack category"""
        with pytest.raises(CampaignValidationError, match="Invalid attack_categories"):
            await service.create_campaign(
                campaign_type="red_team",
                target_url="https://api.example.com",
                max_turns=10,
                attack_categories=["invalid_category"],
            )

    @pytest.mark.asyncio
    async def test_create_red_team_invalid_severity(self, service):
        """Test validation error with invalid severity"""
        with pytest.raises(CampaignValidationError, match="Invalid severity_threshold"):
            await service.create_campaign(
                campaign_type="red_team",
                target_url="https://api.example.com",
                max_turns=10,
                severity_threshold="invalid_severity",
            )

    @pytest.mark.asyncio
    async def test_create_combined_campaign_success(self, service, mock_orchestrator):
        """Test creating a valid combined campaign"""
        mock_orchestrator.create_campaign.return_value["campaign_type"] = "combined"

        with patch("agenteval.application.campaign_service.get_persona_library") as mock_lib:
            mock_persona_lib = MagicMock()
            mock_persona_lib.get_persona.return_value = {"name": "Test"}
            mock_lib.return_value = mock_persona_lib

            result = await service.create_campaign(
                campaign_type="combined",
                target_url="https://api.example.com",
                max_turns=20,
                persona_type="frustrated_customer",
                initial_goal="Get help",
                attack_categories=["injection"],
                combined_strategy="round_robin",
            )

            assert result["campaign_type"] == "combined"

    @pytest.mark.asyncio
    async def test_create_combined_missing_persona(self, service):
        """Test validation error when combined campaign missing persona"""
        with pytest.raises(CampaignValidationError, match="persona_type required"):
            await service.create_campaign(
                campaign_type="combined", target_url="https://api.example.com", max_turns=10
            )

    @pytest.mark.asyncio
    async def test_create_campaign_invalid_type(self, service):
        """Test validation error with invalid campaign type"""
        with pytest.raises(CampaignValidationError, match="Invalid campaign_type"):
            await service.create_campaign(
                campaign_type="invalid_type", target_url="https://api.example.com", max_turns=10
            )


class TestCampaignServiceRetrieval:
    """Test campaign retrieval operations"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = AsyncMock()
        orchestrator.dynamodb = AsyncMock()
        return orchestrator

    @pytest.fixture
    def service(self, mock_orchestrator):
        return CampaignService(orchestrator=mock_orchestrator)

    @pytest.mark.asyncio
    async def test_get_campaign_success(self, service, mock_orchestrator):
        """Test successful campaign retrieval"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "campaign_type": "persona",
            "status": "created",
        }

        result = await service.get_campaign("test-123")
        assert result["campaign_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_get_campaign_not_found(self, service, mock_orchestrator):
        """Test error when campaign not found"""
        mock_orchestrator.dynamodb.get_campaign.return_value = None

        with pytest.raises(CampaignNotFoundError, match="Campaign not found"):
            await service.get_campaign("nonexistent")

    @pytest.mark.asyncio
    async def test_list_campaigns_success(self, service, mock_orchestrator):
        """Test listing campaigns"""
        mock_orchestrator.dynamodb.list_campaigns.return_value = [
            {"campaign_id": "test-1", "status": "created"},
            {"campaign_id": "test-2", "status": "running"},
        ]

        result = await service.list_campaigns(limit=10, offset=0)
        assert result["total"] == 2
        assert len(result["campaigns"]) == 2

    @pytest.mark.asyncio
    async def test_list_campaigns_with_filter(self, service, mock_orchestrator):
        """Test listing campaigns with status filter"""
        mock_orchestrator.dynamodb.list_campaigns.return_value = [
            {"campaign_id": "test-1", "status": "running"}
        ]

        result = await service.list_campaigns(status_filter="running")
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_campaigns_invalid_status(self, service):
        """Test validation error with invalid status filter"""
        with pytest.raises(CampaignValidationError, match="Invalid status filter"):
            await service.list_campaigns(status_filter="invalid_status")


class TestCampaignServiceExecution:
    """Test campaign execution operations"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = AsyncMock()
        orchestrator.dynamodb = AsyncMock()
        orchestrator._track_task = MagicMock()
        return orchestrator

    @pytest.fixture
    def service(self, mock_orchestrator):
        return CampaignService(orchestrator=mock_orchestrator)

    @pytest.mark.asyncio
    async def test_start_campaign_success(self, service, mock_orchestrator):
        """Test starting a campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "status": "created",
            "config": {"max_turns": 10},
        }

        with patch("asyncio.create_task") as mock_task:
            result = await service.start_campaign("test-123")

            assert result["campaign_id"] == "test-123"
            assert result["status"] == "running"
            assert "started_at" in result
            mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_campaign_not_found(self, service, mock_orchestrator):
        """Test starting nonexistent campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = None

        with pytest.raises(CampaignNotFoundError):
            await service.start_campaign("nonexistent")

    @pytest.mark.asyncio
    async def test_start_campaign_already_running(self, service, mock_orchestrator):
        """Test starting already running campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "status": "running",
            "config": {"max_turns": 10},
        }

        with pytest.raises(CampaignStateError, match="already running"):
            await service.start_campaign("test-123")

    @pytest.mark.asyncio
    async def test_pause_campaign_success(self, service, mock_orchestrator):
        """Test pausing a running campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "status": "running",
        }
        mock_orchestrator.dynamodb.update_campaign_status.return_value = {
            "campaign_id": "test-123",
            "status": "paused",
        }

        result = await service.pause_campaign("test-123")
        assert result["status"] == "paused"

    @pytest.mark.asyncio
    async def test_pause_campaign_not_running(self, service, mock_orchestrator):
        """Test pausing non-running campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "status": "created",
        }

        with pytest.raises(CampaignStateError, match="not running"):
            await service.pause_campaign("test-123")

    @pytest.mark.asyncio
    async def test_get_campaign_status_success(self, service, mock_orchestrator):
        """Test getting campaign status"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "status": "running",
            "stats": {"turns_completed": 5},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T01:00:00",
            "config": {"max_turns": 10},
        }

        result = await service.get_campaign_status("test-123")
        assert result["campaign_id"] == "test-123"
        assert result["status"] == "running"
        assert "stats" in result


class TestCampaignServiceDeletion:
    """Test campaign deletion operations"""

    @pytest.fixture
    def mock_orchestrator(self):
        orchestrator = AsyncMock()
        orchestrator.dynamodb = AsyncMock()
        orchestrator.delete_campaign = AsyncMock()
        return orchestrator

    @pytest.fixture
    def service(self, mock_orchestrator):
        return CampaignService(orchestrator=mock_orchestrator)

    @pytest.mark.asyncio
    async def test_delete_campaign_success(self, service, mock_orchestrator):
        """Test deleting a campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "status": "completed",
        }

        result = await service.delete_campaign("test-123")
        assert result["campaign_id"] == "test-123"
        assert result["status"] == "deleted"
        assert "deleted_at" in result

    @pytest.mark.asyncio
    async def test_delete_campaign_running(self, service, mock_orchestrator):
        """Test cannot delete running campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = {
            "campaign_id": "test-123",
            "status": "running",
        }

        with pytest.raises(CampaignStateError, match="Cannot delete running campaign"):
            await service.delete_campaign("test-123")

    @pytest.mark.asyncio
    async def test_delete_campaign_not_found(self, service, mock_orchestrator):
        """Test deleting nonexistent campaign"""
        mock_orchestrator.dynamodb.get_campaign.return_value = None

        with pytest.raises(CampaignNotFoundError):
            await service.delete_campaign("nonexistent")
