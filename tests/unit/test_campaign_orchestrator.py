"""
Unit tests for CampaignOrchestrator

Tests orchestrator lifecycle, client management, and HTTP target communication.
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from agenteval.orchestration.campaign import (
    CampaignOrchestrator,
    CampaignType,
)


class TestCampaignOrchestratorLifecycle:
    """Test CampaignOrchestrator lifecycle management"""

    def test_orchestrator_initializes_with_clients(self):
        """Test that orchestrator initializes all AWS clients"""
        orchestrator = CampaignOrchestrator()

        assert orchestrator.dynamodb is not None
        assert orchestrator.s3 is not None
        assert orchestrator.xray is not None
        assert orchestrator.eventbridge is not None
        assert orchestrator._clients_connected is False
        assert orchestrator._http_client is None

    @pytest.mark.asyncio
    async def test_connect_initializes_all_clients(self):
        """Test that connect() initializes all clients"""
        orchestrator = CampaignOrchestrator()

        # Mock all AWS client connect methods
        orchestrator.dynamodb.connect = AsyncMock()
        orchestrator.s3.connect = AsyncMock()
        orchestrator.xray.connect = AsyncMock()
        orchestrator.eventbridge.connect = AsyncMock()

        await orchestrator.connect()

        # Verify all clients were connected
        orchestrator.dynamodb.connect.assert_called_once()
        orchestrator.s3.connect.assert_called_once()
        orchestrator.xray.connect.assert_called_once()
        orchestrator.eventbridge.connect.assert_called_once()

        # Verify HTTP client was created
        assert orchestrator._http_client is not None
        assert isinstance(orchestrator._http_client, httpx.AsyncClient)
        assert orchestrator._clients_connected is True

    @pytest.mark.asyncio
    async def test_close_disconnects_all_clients(self):
        """Test that close() disconnects all clients"""
        orchestrator = CampaignOrchestrator()

        # Mock connect and close methods
        orchestrator.dynamodb.connect = AsyncMock()
        orchestrator.dynamodb.close = AsyncMock()
        orchestrator.s3.connect = AsyncMock()
        orchestrator.s3.close = AsyncMock()
        orchestrator.xray.connect = AsyncMock()
        orchestrator.xray.close = AsyncMock()
        orchestrator.eventbridge.connect = AsyncMock()
        orchestrator.eventbridge.close = AsyncMock()

        await orchestrator.connect()
        await orchestrator.close()

        # Verify all clients were disconnected
        orchestrator.dynamodb.close.assert_called_once()
        orchestrator.s3.close.assert_called_once()
        orchestrator.xray.close.assert_called_once()
        orchestrator.eventbridge.close.assert_called_once()

        assert orchestrator._clients_connected is False
        assert orchestrator._http_client is None

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        """Test context manager properly manages lifecycle"""
        orchestrator = CampaignOrchestrator()

        # Mock client methods
        orchestrator.dynamodb.connect = AsyncMock()
        orchestrator.dynamodb.close = AsyncMock()
        orchestrator.s3.connect = AsyncMock()
        orchestrator.s3.close = AsyncMock()
        orchestrator.xray.connect = AsyncMock()
        orchestrator.xray.close = AsyncMock()
        orchestrator.eventbridge.connect = AsyncMock()
        orchestrator.eventbridge.close = AsyncMock()

        async with orchestrator:
            assert orchestrator._clients_connected is True

        assert orchestrator._clients_connected is False


class TestHTTPTargetClient:
    """Test real HTTP target client implementation"""

    @pytest.mark.asyncio
    async def test_send_to_target_requires_connection(self):
        """Test that _send_to_target validates HTTP client connection"""
        orchestrator = CampaignOrchestrator()

        with pytest.raises(RuntimeError, match="HTTP client not connected"):
            await orchestrator._send_to_target("http://example.com", "test message")

    @pytest.mark.asyncio
    async def test_send_to_target_makes_http_request(self):
        """Test that _send_to_target makes actual HTTP POST request"""
        orchestrator = CampaignOrchestrator()

        # Mock HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success response"
        mock_response.json.return_value = {"response": "Test response"}
        mock_response.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        orchestrator._http_client = mock_http_client

        result = await orchestrator._send_to_target("http://example.com/api", "Test message")

        # Verify HTTP POST was called
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args

        assert call_args[0][0] == "http://example.com/api"
        assert "json" in call_args[1]
        assert call_args[1]["json"]["message"] == "Test message"

        # Verify headers include trace propagation
        headers = call_args[1]["headers"]
        assert "Content-Type" in headers
        assert "User-Agent" in headers
        assert headers["User-Agent"] == "AgentEval/1.0"

        assert result == "Test response"

    @pytest.mark.asyncio
    async def test_send_to_target_handles_timeout(self):
        """Test that _send_to_target handles timeouts"""
        orchestrator = CampaignOrchestrator()

        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = httpx.TimeoutException("Timeout")
        orchestrator._http_client = mock_http_client

        with pytest.raises(RuntimeError, match="timeout"):
            await orchestrator._send_to_target("http://example.com", "message")

    @pytest.mark.asyncio
    async def test_send_to_target_handles_http_errors(self):
        """Test that _send_to_target handles HTTP errors"""
        orchestrator = CampaignOrchestrator()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response
        orchestrator._http_client = mock_http_client

        with pytest.raises(RuntimeError, match="returned error: 500"):
            await orchestrator._send_to_target("http://example.com", "message")

    @pytest.mark.asyncio
    async def test_send_to_target_handles_connection_errors(self):
        """Test that _send_to_target handles connection errors"""
        orchestrator = CampaignOrchestrator()

        mock_http_client = AsyncMock()
        mock_http_client.post.side_effect = httpx.RequestError("Connection failed")
        orchestrator._http_client = mock_http_client

        with pytest.raises(RuntimeError, match="Failed to connect"):
            await orchestrator._send_to_target("http://example.com", "message")

    @pytest.mark.asyncio
    async def test_http_client_has_timeout_configuration(self):
        """Test that HTTP client is configured with timeouts"""
        orchestrator = CampaignOrchestrator()

        # Mock AWS client connections
        orchestrator.dynamodb.connect = AsyncMock()
        orchestrator.s3.connect = AsyncMock()
        orchestrator.xray.connect = AsyncMock()
        orchestrator.eventbridge.connect = AsyncMock()

        await orchestrator.connect()

        # Verify HTTP client has timeout
        assert orchestrator._http_client is not None
        assert orchestrator._http_client.timeout is not None


class TestCampaignOrchestratorValidation:
    """Test campaign configuration validation"""

    def test_validate_persona_campaign_config(self):
        """Test validation for PERSONA campaign"""
        orchestrator = CampaignOrchestrator()

        # Should raise if persona_type missing
        with pytest.raises(ValueError, match="persona_type required"):
            orchestrator._validate_campaign_config(CampaignType.PERSONA, {})

        # Should not raise if persona_type present
        orchestrator._validate_campaign_config(
            CampaignType.PERSONA, {"persona_type": "frustrated_customer"}
        )

    def test_validate_redteam_campaign_config(self):
        """Test validation for RED_TEAM campaign (should not raise)"""
        orchestrator = CampaignOrchestrator()

        # Should not raise even without attack_categories
        orchestrator._validate_campaign_config(CampaignType.RED_TEAM, {})
