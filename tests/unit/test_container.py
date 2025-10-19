"""
Unit tests for Dependency Injection Container.

Tests singleton management, lazy initialization, and lifecycle control.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.container import Container, get_container, reset_container


class TestContainerInitialization:
    """Test suite for Container initialization"""

    def test_init_creates_empty_container(self):
        """Test container initializes with all dependencies as None"""
        container = Container()

        # Verify all dependencies start as None
        assert container._dynamodb is None
        assert container._s3 is None
        assert container._xray is None
        assert container._eventbridge is None
        assert container._trace_analyzer is None
        assert container._correlation_engine is None
        assert container._campaign_orchestrator is None
        assert container._campaign_service is None
        assert container._report_service is None
        assert container._persona_factory is None
        assert container._redteam_factory is None
        assert container._judge_factory is None

    def test_init_sets_connected_false(self):
        """Test container starts in disconnected state"""
        container = Container()

        assert container._connected is False
        assert container.is_connected() is False

    def test_repr(self):
        """Test string representation"""
        container = Container()

        repr_str = repr(container)

        assert "Container" in repr_str
        assert "connected=False" in repr_str
        assert "clients_created=0" in repr_str


class TestInfrastructureFactories:
    """Test suite for infrastructure layer factories"""

    def test_dynamodb_lazy_initialization(self):
        """Test DynamoDB client is created on first access"""
        container = Container()

        # Initially None
        assert container._dynamodb is None

        # Create on first access
        with patch("agenteval.container.DynamoDBClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            result = container.dynamodb()

            assert result == mock_client
            MockClient.assert_called_once()

    def test_dynamodb_singleton(self):
        """Test DynamoDB client returns same instance"""
        container = Container()

        with patch("agenteval.container.DynamoDBClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            first = container.dynamodb()
            second = container.dynamodb()

            assert first is second
            # Should only be created once
            assert MockClient.call_count == 1

    def test_s3_lazy_initialization(self):
        """Test S3 client is created on first access"""
        container = Container()

        assert container._s3 is None

        with patch("agenteval.container.S3Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            result = container.s3()

            assert result == mock_client
            MockClient.assert_called_once()

    def test_s3_singleton(self):
        """Test S3 client returns same instance"""
        container = Container()

        with patch("agenteval.container.S3Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            first = container.s3()
            second = container.s3()

            assert first is second
            assert MockClient.call_count == 1

    def test_xray_lazy_initialization(self):
        """Test X-Ray client is created on first access"""
        container = Container()

        assert container._xray is None

        with patch("agenteval.container.XRayClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            result = container.xray()

            assert result == mock_client
            MockClient.assert_called_once()

    def test_eventbridge_lazy_initialization(self):
        """Test EventBridge client is created on first access"""
        container = Container()

        assert container._eventbridge is None

        with patch("agenteval.container.EventBridgeClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            result = container.eventbridge()

            assert result == mock_client
            MockClient.assert_called_once()


class TestAnalysisFactories:
    """Test suite for analysis layer factories"""

    def test_trace_analyzer_lazy_initialization(self):
        """Test TraceAnalyzer is created on first access"""
        container = Container()

        assert container._trace_analyzer is None

        with patch("agenteval.container.TraceAnalyzer") as MockAnalyzer:
            mock_analyzer = MagicMock()
            MockAnalyzer.return_value = mock_analyzer

            result = container.trace_analyzer()

            assert result == mock_analyzer
            MockAnalyzer.assert_called_once()

    def test_correlation_engine_singleton(self):
        """Test CorrelationEngine returns same instance"""
        container = Container()

        with patch("agenteval.container.CorrelationEngine") as MockEngine:
            mock_engine = MagicMock()
            MockEngine.return_value = mock_engine

            first = container.correlation_engine()
            second = container.correlation_engine()

            assert first is second
            assert MockEngine.call_count == 1


class TestAgentFactories:
    """Test suite for agent factory layer"""

    def test_persona_factory_lazy_initialization(self):
        """Test PersonaAgentFactory is created on first access"""
        container = Container()

        assert container._persona_factory is None

        with patch("agenteval.container.PersonaAgentFactory") as MockFactory:
            mock_factory = MagicMock()
            MockFactory.return_value = mock_factory

            result = container.persona_factory()

            assert result == mock_factory
            MockFactory.assert_called_once()

    def test_redteam_factory_singleton(self):
        """Test RedTeamAgentFactory returns same instance"""
        container = Container()

        with patch("agenteval.container.RedTeamAgentFactory") as MockFactory:
            mock_factory = MagicMock()
            MockFactory.return_value = mock_factory

            first = container.redteam_factory()
            second = container.redteam_factory()

            assert first is second
            assert MockFactory.call_count == 1

    def test_judge_factory_lazy_initialization(self):
        """Test JudgeAgentFactory is created on first access"""
        container = Container()

        assert container._judge_factory is None

        with patch("agenteval.container.JudgeAgentFactory") as MockFactory:
            mock_factory = MagicMock()
            MockFactory.return_value = mock_factory

            result = container.judge_factory()

            assert result == mock_factory
            MockFactory.assert_called_once()


class TestApplicationServices:
    """Test suite for application services layer"""

    def test_campaign_service_lazy_initialization(self):
        """Test CampaignService is created on first access"""
        container = Container()

        assert container._campaign_service is None

        # Mock all dependencies
        with (
            patch("agenteval.container.CampaignService") as MockService,
            patch("agenteval.container.CampaignOrchestrator"),
        ):
            mock_service = MagicMock()
            MockService.return_value = mock_service

            result = container.campaign_service()

            assert result == mock_service
            MockService.assert_called_once()

    def test_report_service_singleton(self):
        """Test ReportService returns same instance"""
        container = Container()

        with (
            patch("agenteval.container.ReportService") as MockService,
            patch("agenteval.container.CampaignOrchestrator"),
            patch("agenteval.container.S3Client"),
        ):
            mock_service = MagicMock()
            MockService.return_value = mock_service

            first = container.report_service()
            second = container.report_service()

            assert first is second
            assert MockService.call_count == 1


class TestLifecycleManagement:
    """Test suite for container lifecycle"""

    @pytest.mark.asyncio
    async def test_connect_when_no_clients_created(self):
        """Test connect when no clients have been created"""
        container = Container()

        await container.connect()

        assert container.is_connected() is True

    @pytest.mark.asyncio
    async def test_connect_calls_client_connect(self):
        """Test connect calls connect on created clients"""
        container = Container()

        # Create mock clients
        mock_dynamodb = AsyncMock()
        mock_dynamodb.connect = AsyncMock()
        container._dynamodb = mock_dynamodb

        mock_s3 = AsyncMock()
        mock_s3.connect = AsyncMock()
        container._s3 = mock_s3

        await container.connect()

        # Verify connect was called
        mock_dynamodb.connect.assert_called_once()
        mock_s3.connect.assert_called_once()
        assert container.is_connected() is True

    @pytest.mark.asyncio
    async def test_connect_is_idempotent(self):
        """Test connect can be called multiple times"""
        container = Container()

        mock_dynamodb = AsyncMock()
        mock_dynamodb.connect = AsyncMock()
        container._dynamodb = mock_dynamodb

        # Call connect twice
        await container.connect()
        await container.connect()

        # Should only connect once
        mock_dynamodb.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_calls_client_close(self):
        """Test close calls close on created clients"""
        container = Container()
        container._connected = True

        # Create mock clients
        mock_dynamodb = AsyncMock()
        mock_dynamodb.close = AsyncMock()
        container._dynamodb = mock_dynamodb

        mock_s3 = AsyncMock()
        mock_s3.close = AsyncMock()
        container._s3 = mock_s3

        await container.close()

        # Verify close was called
        mock_dynamodb.close.assert_called_once()
        mock_s3.close.assert_called_once()
        assert container.is_connected() is False

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self):
        """Test close does nothing when not connected"""
        container = Container()
        container._connected = False

        mock_dynamodb = AsyncMock()
        mock_dynamodb.close = AsyncMock()
        container._dynamodb = mock_dynamodb

        await container.close()

        # Should not call close
        mock_dynamodb.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_managed_context_manager(self):
        """Test managed context manager connects and closes"""
        container = Container()

        mock_dynamodb = AsyncMock()
        mock_dynamodb.connect = AsyncMock()
        mock_dynamodb.close = AsyncMock()
        container._dynamodb = mock_dynamodb

        async with container.managed() as ctx:
            # Verify we got the container
            assert ctx is container
            assert container.is_connected() is True
            mock_dynamodb.connect.assert_called_once()

        # Verify close was called on exit
        mock_dynamodb.close.assert_called_once()
        assert container.is_connected() is False

    @pytest.mark.asyncio
    async def test_managed_context_closes_on_exception(self):
        """Test managed context manager closes even on exception"""
        container = Container()

        mock_dynamodb = AsyncMock()
        mock_dynamodb.connect = AsyncMock()
        mock_dynamodb.close = AsyncMock()
        container._dynamodb = mock_dynamodb

        with pytest.raises(ValueError):
            async with container.managed():
                raise ValueError("Test error")

        # Verify close was still called
        mock_dynamodb.close.assert_called_once()


class TestContainerReset:
    """Test suite for container reset functionality"""

    def test_reset_clears_all_dependencies(self):
        """Test reset clears all singleton instances"""
        container = Container()

        # Set some mock dependencies
        container._dynamodb = MagicMock()
        container._s3 = MagicMock()
        container._persona_factory = MagicMock()
        container._connected = True

        container.reset()

        # Verify all cleared
        assert container._dynamodb is None
        assert container._s3 is None
        assert container._xray is None
        assert container._eventbridge is None
        assert container._trace_analyzer is None
        assert container._correlation_engine is None
        assert container._campaign_orchestrator is None
        assert container._campaign_service is None
        assert container._report_service is None
        assert container._persona_factory is None
        assert container._redteam_factory is None
        assert container._judge_factory is None
        assert container._connected is False

    def test_reset_allows_recreation(self):
        """Test dependencies can be recreated after reset"""
        container = Container()

        with patch("agenteval.container.DynamoDBClient") as MockClient:
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            MockClient.side_effect = [mock_client1, mock_client2]

            # Create first instance
            first = container.dynamodb()
            assert first is mock_client1

            # Reset
            container.reset()

            # Create new instance
            second = container.dynamodb()
            assert second is mock_client2
            assert second is not first


class TestGlobalContainer:
    """Test suite for global container functions"""

    def teardown_method(self):
        """Reset global container after each test"""
        reset_container()

    def test_get_container_creates_instance(self):
        """Test get_container creates container on first call"""
        reset_container()  # Ensure clean state

        container = get_container()

        assert container is not None
        assert isinstance(container, Container)

    def test_get_container_returns_singleton(self):
        """Test get_container returns same instance"""
        reset_container()

        first = get_container()
        second = get_container()

        assert first is second

    def test_reset_container_clears_global(self):
        """Test reset_container clears global instance"""
        container1 = get_container()

        reset_container()

        container2 = get_container()

        # Should be different instances
        assert container2 is not container1

    def test_reset_container_calls_reset(self):
        """Test reset_container calls reset on existing container"""
        container = get_container()
        container._dynamodb = MagicMock()

        reset_container()

        # New container should be fresh
        new_container = get_container()
        assert new_container._dynamodb is None


class TestFastAPIConvenienceFunctions:
    """Test suite for FastAPI dependency functions"""

    def teardown_method(self):
        """Reset global container after each test"""
        reset_container()

    @pytest.mark.asyncio
    async def test_get_dynamodb_returns_from_container(self):
        """Test get_dynamodb returns client from global container"""
        from agenteval.container import get_dynamodb

        with patch("agenteval.container.DynamoDBClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            result = await get_dynamodb()

            assert result == mock_client

    @pytest.mark.asyncio
    async def test_get_s3_returns_from_container(self):
        """Test get_s3 returns client from global container"""
        from agenteval.container import get_s3

        with patch("agenteval.container.S3Client") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            result = await get_s3()

            assert result == mock_client

    @pytest.mark.asyncio
    async def test_get_persona_factory_returns_from_container(self):
        """Test get_persona_factory returns factory from global container"""
        from agenteval.container import get_persona_factory

        with patch("agenteval.container.PersonaAgentFactory") as MockFactory:
            mock_factory = MagicMock()
            MockFactory.return_value = mock_factory

            result = await get_persona_factory()

            assert result == mock_factory
