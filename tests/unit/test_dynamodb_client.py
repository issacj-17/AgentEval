"""
Unit tests for DynamoDB Client (Core Methods).

Tests core CRUD operations and lifecycle management.
Focuses on high-value methods to maximize coverage efficiency.
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.aws.dynamodb import (
    DynamoDBClient,
    _make_placeholder_name,
    dynamodb_to_python,
    python_to_dynamodb,
)


class TestHelperFunctions:
    """Test suite for DynamoDB helper functions"""

    def test_python_to_dynamodb_float(self):
        """Test converting float to Decimal"""
        result = python_to_dynamodb(3.14)

        assert isinstance(result, Decimal)
        assert float(result) == 3.14

    def test_python_to_dynamodb_dict(self):
        """Test converting dict with nested floats"""
        data = {"score": 0.95, "count": 10}

        result = python_to_dynamodb(data)

        assert isinstance(result["score"], Decimal)
        assert result["count"] == 10

    def test_python_to_dynamodb_list(self):
        """Test converting list with floats"""
        data = [1.5, 2.5, 3.5]

        result = python_to_dynamodb(data)

        assert all(isinstance(x, Decimal) for x in result)

    def test_python_to_dynamodb_passthrough(self):
        """Test non-float types pass through"""
        assert python_to_dynamodb("test") == "test"
        assert python_to_dynamodb(42) == 42
        assert python_to_dynamodb(None) is None

    def test_dynamodb_to_python_decimal(self):
        """Test converting Decimal to float"""
        result = dynamodb_to_python(Decimal("3.14"))

        assert isinstance(result, float)
        assert result == 3.14

    def test_dynamodb_to_python_dict(self):
        """Test converting dict with Decimals"""
        data = {"score": Decimal("0.95"), "count": 10}

        result = dynamodb_to_python(data)

        assert isinstance(result["score"], float)
        assert result["count"] == 10

    def test_dynamodb_to_python_list(self):
        """Test converting list with Decimals"""
        data = [Decimal("1.5"), Decimal("2.5")]

        result = dynamodb_to_python(data)

        assert all(isinstance(x, float) for x in result)

    def test_dynamodb_to_python_passthrough(self):
        """Test non-Decimal types pass through"""
        assert dynamodb_to_python("test") == "test"
        assert dynamodb_to_python(42) == 42

    def test_make_placeholder_name_basic(self):
        """Test generating placeholder name"""
        result = _make_placeholder_name("test", {}, "#")

        assert result == "#test"

    def test_make_placeholder_name_sanitization(self):
        """Test sanitizing invalid characters"""
        result = _make_placeholder_name("test-key", {}, "#")

        assert result == "#test_key"

    def test_make_placeholder_name_collision(self):
        """Test avoiding name collisions"""
        existing = {"#test": True}

        result = _make_placeholder_name("test", existing, "#")

        assert result == "#test_2"

    def test_make_placeholder_name_starts_with_digit(self):
        """Test handling names starting with digit"""
        result = _make_placeholder_name("123test", {}, "#")

        assert result == "#attr_123test"


class TestDynamoDBClientInitialization:
    """Test suite for DynamoDB client initialization"""

    def test_init_with_defaults(self):
        """Test initialization uses settings defaults"""
        client = DynamoDBClient()

        assert client.session is not None
        assert client._resource is None
        assert client._connected is False

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration"""
        with patch("agenteval.aws.dynamodb.aioboto3.Session"):
            client = DynamoDBClient(
                region="us-west-2", profile="custom", campaigns_table="custom-campaigns"
            )

            assert client.region == "us-west-2"
            assert client.profile == "custom"
            assert client.campaigns_table == "custom-campaigns"


class TestLifecycleManagement:
    """Test suite for connection lifecycle"""

    @pytest.mark.asyncio
    async def test_connect(self):
        """Test connecting to DynamoDB"""
        client = DynamoDBClient()

        # Mock the session resource
        mock_resource = AsyncMock()
        mock_resource.__aenter__ = AsyncMock(return_value=mock_resource)

        with patch.object(client.session, "resource") as mock_res:
            mock_res.return_value = mock_resource

            await client.connect()

            assert client._connected is True
            assert client._resource == mock_resource
            mock_resource.__aenter__.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_idempotent(self):
        """Test connect is idempotent"""
        client = DynamoDBClient()
        client._connected = True
        client._resource = MagicMock()

        # Should not reconnect
        await client.connect()

        assert client._connected is True

    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing DynamoDB connection"""
        client = DynamoDBClient()
        client._connected = True

        mock_resource = AsyncMock()
        mock_resource.__aexit__ = AsyncMock()
        client._resource = mock_resource

        await client.close()

        assert client._connected is False
        mock_resource.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test close does nothing when not connected"""
        client = DynamoDBClient()
        client._connected = False

        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        client = DynamoDBClient()

        mock_resource = AsyncMock()
        mock_resource.__aenter__ = AsyncMock(return_value=mock_resource)
        mock_resource.__aexit__ = AsyncMock()

        with patch.object(client.session, "resource") as mock_res:
            mock_res.return_value = mock_resource

            async with client as ctx:
                assert ctx == client
                assert client._connected is True

            # Should close on exit
            mock_resource.__aexit__.assert_called_once()

    def test_ensure_connected_raises_when_not_connected(self):
        """Test _ensure_connected raises when not connected"""
        client = DynamoDBClient()
        client._connected = False

        with pytest.raises(RuntimeError, match="not connected"):
            client._ensure_connected()


class TestCampaignOperations:
    """Test suite for campaign CRUD operations"""

    @pytest.mark.asyncio
    async def test_create_campaign(self):
        """Test creating a campaign"""
        client = DynamoDBClient()
        client._connected = True

        # Mock table
        mock_table = AsyncMock()
        mock_table.put_item = AsyncMock()

        mock_resource = MagicMock()
        mock_resource.Table = AsyncMock(return_value=mock_table)
        client._resource = mock_resource

        campaign_config = {
            "campaign_type": "persona",
            "target_url": "https://example.com",
            "config": {"turns": 10},
        }

        result = await client.create_campaign("test-campaign-1", campaign_config)

        # Verify campaign was created
