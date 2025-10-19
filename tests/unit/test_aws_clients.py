"""
Unit tests for AWS Client Lifecycle Management

Tests the connect()/close() lifecycle and connection validation
for DynamoDB, S3, XRay, and EventBridge clients.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.aws.dynamodb import DynamoDBClient
from agenteval.aws.eventbridge import EventBridgeClient
from agenteval.aws.s3 import S3Client
from agenteval.aws.xray import XRayClient


class TestDynamoDBClientLifecycle:
    """Test DynamoDB client lifecycle management"""

    @pytest.mark.asyncio
    async def test_client_starts_disconnected(self):
        """Test that client starts in disconnected state"""
        client = DynamoDBClient()
        assert client._connected is False
        assert client._resource is None

    @pytest.mark.asyncio
    async def test_connect_establishes_connection(self):
        """Test that connect() establishes connection"""
        client = DynamoDBClient()

        with patch.object(client.session, "resource") as mock_resource:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = MagicMock()
            mock_resource.return_value = mock_context

            await client.connect()

            assert client._connected is True
            assert client._resource is not None
            mock_resource.assert_called_once_with("dynamodb")

    @pytest.mark.asyncio
    async def test_close_disconnects(self):
        """Test that close() disconnects client"""
        client = DynamoDBClient()

        with patch.object(client.session, "resource") as mock_resource:
            mock_context = AsyncMock()
            mock_resource_obj = MagicMock()
            mock_context.__aenter__.return_value = mock_resource_obj
            mock_context.__aexit__.return_value = None
            mock_resource.return_value = mock_context

            await client.connect()
            assert client._connected is True

            await client.close()
            assert client._connected is False

    @pytest.mark.asyncio
    async def test_context_manager_connects_and_disconnects(self):
        """Test that context manager properly connects and disconnects"""
        client = DynamoDBClient()

        with patch.object(client.session, "resource") as mock_resource:
            mock_context = AsyncMock()
            mock_resource_obj = MagicMock()
            mock_context.__aenter__.return_value = mock_resource_obj
            mock_context.__aexit__.return_value = None
            mock_resource.return_value = mock_context

            async with client:
                assert client._connected is True

            assert client._connected is False

    @pytest.mark.asyncio
    async def test_operations_require_connection(self):
        """Test that operations fail if not connected"""
        client = DynamoDBClient()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.get_campaign("test-id")

    @pytest.mark.asyncio
    async def test_ensure_connected_validation(self):
        """Test _ensure_connected() validation"""
        client = DynamoDBClient()

        # Should raise when not connected
        with pytest.raises(RuntimeError):
            client._ensure_connected()

        # Should not raise when connected
        with patch.object(client.session, "resource") as mock_resource:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = MagicMock()
            mock_resource.return_value = mock_context

            await client.connect()
            client._ensure_connected()  # Should not raise


class TestS3ClientLifecycle:
    """Test S3 client lifecycle management"""

    @pytest.mark.asyncio
    async def test_client_starts_disconnected(self):
        """Test that client starts in disconnected state"""
        client = S3Client()
        assert client._connected is False
        assert client._client is None

    @pytest.mark.asyncio
    async def test_connect_establishes_connection(self):
        """Test that connect() establishes connection"""
        client = S3Client()

        with patch.object(client.session, "client") as mock_client:
            mock_context = AsyncMock()
            mock_context.__aenter__.return_value = MagicMock()
            mock_client.return_value = mock_context

            await client.connect()

            assert client._connected is True
            assert client._client is not None
            mock_client.assert_called_once_with("s3")

    @pytest.mark.asyncio
    async def test_operations_require_connection(self):
        """Test that operations fail if not connected"""
        client = S3Client()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.upload_json("bucket", "key", {"test": "data"})

    @pytest.mark.asyncio
    async def test_store_results_method_exists(self):
        """Test that store_results method exists and validates connection"""
        client = S3Client()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.store_results("campaign-123", {"result": "data"}, "key")


class TestXRayClientLifecycle:
    """Test XRay client lifecycle management"""

    @pytest.mark.asyncio
    async def test_client_starts_disconnected(self):
        """Test that client starts in disconnected state"""
        client = XRayClient()
        assert client._connected is False
        assert client._client is None

    @pytest.mark.asyncio
    async def test_operations_require_connection(self):
        """Test that operations fail if not connected"""
        client = XRayClient()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.get_trace("test-trace-id")


class TestEventBridgeClientLifecycle:
    """Test EventBridge client lifecycle management"""

    @pytest.mark.asyncio
    async def test_client_starts_disconnected(self):
        """Test that client starts in disconnected state"""
        client = EventBridgeClient()
        assert client._connected is False
        assert client._client is None

    @pytest.mark.asyncio
    async def test_operations_require_connection(self):
        """Test that operations fail if not connected"""
        client = EventBridgeClient()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.publish_event("TestEvent", {"test": "data"})


class TestDynamoDBHelperMethods:
    """Test the newly implemented DynamoDB helper methods"""

    @pytest.mark.asyncio
    async def test_update_turn_status_exists(self):
        """Test that update_turn_status method exists"""
        client = DynamoDBClient()
        assert hasattr(client, "update_turn_status")

    @pytest.mark.asyncio
    async def test_list_campaigns_exists(self):
        """Test that list_campaigns method exists"""
        client = DynamoDBClient()
        assert hasattr(client, "list_campaigns")

    @pytest.mark.asyncio
    async def test_get_turn_exists(self):
        """Test that get_turn method exists"""
        client = DynamoDBClient()
        assert hasattr(client, "get_turn")

    @pytest.mark.asyncio
    async def test_get_campaign_turns_exists(self):
        """Test that get_campaign_turns method exists"""
        client = DynamoDBClient()
        assert hasattr(client, "get_campaign_turns")

    @pytest.mark.asyncio
    async def test_update_campaign_stats_exists(self):
        """Test that update_campaign_stats method exists"""
        client = DynamoDBClient()
        assert hasattr(client, "update_campaign_stats")

    @pytest.mark.asyncio
    async def test_helper_methods_require_connection(self):
        """Test that helper methods validate connection"""
        client = DynamoDBClient()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.update_turn_status("campaign-id", "turn-id", "completed")

        with pytest.raises(RuntimeError, match="not connected"):
            await client.list_campaigns()

        with pytest.raises(RuntimeError, match="not connected"):
            await client.get_turn("campaign-id", "turn-id")

        with pytest.raises(RuntimeError, match="not connected"):
            await client.update_campaign_stats("campaign-id", {})
