"""
Integration tests for Dependency Injection Container

Tests the container's ability to manage dependencies,
lifecycle, and integration with FastAPI.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agenteval.container import (
    Container,
    get_campaign_orchestrator,
    get_container,
    get_dynamodb,
    get_eventbridge,
    get_s3,
    get_xray,
    reset_container,
)


class TestContainerBasics:
    """Test basic container functionality"""

    def test_container_initialization(self):
        """Test container initializes with no dependencies created"""
        container = Container()

        assert container._dynamodb is None
        assert container._s3 is None
        assert container._xray is None
        assert container._eventbridge is None
        assert container._campaign_orchestrator is None
        assert not container._connected

    def test_lazy_initialization(self):
        """Test dependencies are created lazily on first access"""
        container = Container()

        # Before access
        assert container._dynamodb is None

        # Access triggers creation
        dynamodb = container.dynamodb()

        # After access
        assert container._dynamodb is not None
        assert dynamodb is container._dynamodb

        # Subsequent access returns same instance
        dynamodb2 = container.dynamodb()
        assert dynamodb is dynamodb2

    def test_singleton_pattern(self):
        """Test each dependency type is a singleton per container"""
        container = Container()

        # Get each client multiple times
        db1 = container.dynamodb()
        db2 = container.dynamodb()
        s3_1 = container.s3()
        s3_2 = container.s3()
        xray1 = container.xray()
        xray2 = container.xray()

        # Verify same instances returned
        assert db1 is db2
        assert s3_1 is s3_2
        assert xray1 is xray2

    def test_reset_clears_dependencies(self):
        """Test reset clears all dependencies"""
        container = Container()

        # Create some dependencies
        container.dynamodb()
        container.s3()

        assert container._dynamodb is not None
        assert container._s3 is not None

        # Reset
        container.reset()

        # Verify cleared
        assert container._dynamodb is None
        assert container._s3 is None
        assert not container._connected


class TestContainerLifecycle:
    """Test container lifecycle management"""

    @pytest.mark.asyncio
    async def test_connect_idempotent(self):
        """Test connect can be called multiple times safely"""
        container = Container()

        # Create clients first (they need to exist to be connected)
        container.dynamodb()
        container.s3()

        # Connect multiple times
        await container.connect()
        await container.connect()

        assert container.is_connected()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Test close can be called multiple times safely"""
        container = Container()

        # Create and connect
        container.dynamodb()
        await container.connect()

        # Close multiple times
        await container.close()
        await container.close()

        assert not container.is_connected()

    @pytest.mark.asyncio
    async def test_managed_context_manager(self):
        """Test managed context manager connects and closes"""
        container = Container()

        assert not container.is_connected()

        async with container.managed():
            # Inside context, should be connected
            assert container.is_connected()

        # Outside context, should be closed
        assert not container.is_connected()

    @pytest.mark.asyncio
    async def test_orchestrator_lifecycle(self):
        """Test orchestrator connection lifecycle"""
        container = Container()

        # Create orchestrator (creates all dependencies)
        orchestrator = container.campaign_orchestrator()

        assert orchestrator is not None
        assert not orchestrator._clients_connected

        # Connect container
        await container.connect()

        # Orchestrator should now be connected
        assert orchestrator._clients_connected


class TestOrchestratorIntegration:
    """Test CampaignOrchestrator integration with container"""

    def test_orchestrator_receives_injected_clients(self):
        """Test orchestrator receives clients from container"""
        container = Container()

        # Get orchestrator from container
        orchestrator = container.campaign_orchestrator()

        # Orchestrator should have clients from container
        assert orchestrator.dynamodb is container.dynamodb()
        assert orchestrator.s3 is container.s3()
        assert orchestrator.xray is container.xray()
        assert orchestrator.eventbridge is container.eventbridge()

    def test_orchestrator_is_singleton(self):
        """Test orchestrator is a singleton per container"""
        container = Container()

        orch1 = container.campaign_orchestrator()
        orch2 = container.campaign_orchestrator()

        assert orch1 is orch2


class TestGlobalContainer:
    """Test global container functionality"""

    def test_get_container_returns_singleton(self):
        """Test get_container returns same instance"""
        reset_container()  # Start fresh

        container1 = get_container()
        container2 = get_container()

        assert container1 is container2

    def test_reset_container_creates_new_instance(self):
        """Test reset_container creates new instance on next get"""
        reset_container()

        container1 = get_container()

        # Create some state
        container1.dynamodb()

        reset_container()

        container2 = get_container()

        # Should be different instance
        # (reset_container creates fresh state)
        assert container2._dynamodb is None


class TestFastAPIDependencies:
    """Test FastAPI dependency functions"""

    @pytest.mark.asyncio
    async def test_get_dynamodb_dependency(self):
        """Test get_dynamodb returns client from global container"""
        reset_container()

        client = await get_dynamodb()

        assert client is get_container().dynamodb()

    @pytest.mark.asyncio
    async def test_get_s3_dependency(self):
        """Test get_s3 returns client from global container"""
        reset_container()

        client = await get_s3()

        assert client is get_container().s3()

    @pytest.mark.asyncio
    async def test_get_xray_dependency(self):
        """Test get_xray returns client from global container"""
        reset_container()

        client = await get_xray()

        assert client is get_container().xray()

    @pytest.mark.asyncio
    async def test_get_eventbridge_dependency(self):
        """Test get_eventbridge returns client from global container"""
        reset_container()

        client = await get_eventbridge()

        assert client is get_container().eventbridge()

    @pytest.mark.asyncio
    async def test_get_campaign_orchestrator_dependency(self):
        """Test get_campaign_orchestrator returns orchestrator from global container"""
        reset_container()

        orchestrator = await get_campaign_orchestrator()

        assert orchestrator is get_container().campaign_orchestrator()


class TestConfigInjection:
    """Test configuration injection into clients"""

    def test_dynamodb_receives_config(self):
        """Test DynamoDB client receives config from container"""
        container = Container()

        # Get client from container
        dynamodb = container.dynamodb()

        # Client should have config from settings
        assert dynamodb.region is not None
        assert dynamodb.campaigns_table is not None
        assert dynamodb.turns_table is not None

    def test_s3_receives_config(self):
        """Test S3 client receives config from container"""
        container = Container()

        # Get client from container
        s3 = container.s3()

        # Client should have config from settings
        assert s3.region is not None
        assert s3.results_bucket is not None
        assert s3.reports_bucket is not None

    def test_xray_receives_config(self):
        """Test X-Ray client receives config from container"""
        container = Container()

        # Get client from container
        xray = container.xray()

        # Client should have config from settings
        assert xray.region is not None

    def test_eventbridge_receives_config(self):
        """Test EventBridge client receives config from container"""
        container = Container()

        # Get client from container
        eventbridge = container.eventbridge()

        # Client should have config from settings
        assert eventbridge.region is not None
        assert eventbridge.bus_name is not None


class TestTestability:
    """Test container makes testing easier"""

    @pytest.mark.asyncio
    async def test_mock_injection(self):
        """Test can inject mocks for testing"""
        container = Container()

        # Create mock
        mock_dynamodb = AsyncMock()
        mock_dynamodb.get_campaign.return_value = {"campaign_id": "test-123", "status": "running"}

        # Inject mock
        container._dynamodb = mock_dynamodb
        container._connected = True

        # Use mock
        result = await container.dynamodb().get_campaign("test-123")

        assert result["campaign_id"] == "test-123"
        mock_dynamodb.get_campaign.assert_called_once_with("test-123")

    def test_orchestrator_with_mock_clients(self):
        """Test orchestrator can use mocked clients"""
        container = Container()

        # Create mocks
        container._dynamodb = Mock()
        container._s3 = Mock()
        container._xray = Mock()
        container._eventbridge = Mock()

        # Get orchestrator (will use mocked clients)
        orchestrator = container.campaign_orchestrator()

        # Verify orchestrator uses mocks
        assert orchestrator.dynamodb is container._dynamodb
        assert orchestrator.s3 is container._s3
        assert orchestrator.xray is container._xray
        assert orchestrator.eventbridge is container._eventbridge


@pytest.fixture(autouse=True)
def reset_global_container():
    """Reset global container before and after each test"""
    reset_container()
    yield
    reset_container()
