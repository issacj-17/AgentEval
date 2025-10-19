"""
Pytest configuration and shared fixtures

Provides common fixtures for all test modules, including DI container fixtures.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add src to Python path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_data_dir():
    """Return path to test data directory"""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_campaign_config():
    """Sample campaign configuration for testing"""
    return {"persona_type": "frustrated_customer", "max_turns": 5, "timeout_seconds": 30}


@pytest.fixture
def sample_turn_data():
    """Sample turn data for testing"""
    return {
        "turn_number": 1,
        "user_message": "Test message",
        "system_response": "Test response",
        "status": "completed",
    }


@pytest.fixture
def mock_trace_data():
    """Mock X-Ray trace data for testing"""
    return {
        "Id": "test-trace-id-123",
        "Duration": 1.5,
        "Segments": [
            {
                "Id": "segment-1",
                "Name": "test-segment",
                "StartTime": 1234567890.0,
                "EndTime": 1234567891.5,
            }
        ],
    }


# ============================================================================
# DI Container Fixtures
# ============================================================================


@pytest.fixture
def fresh_container():
    """
    Provides a fresh Container instance for testing

    Automatically resets the container after test completes.
    """
    from agenteval.container import Container, reset_container

    reset_container()
    container = Container()
    yield container
    reset_container()


@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB client for testing"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    mock.get_campaign = AsyncMock(
        return_value={
            "campaign_id": "test-123",
            "campaign_type": "persona",
            "status": "created",
            "config": {},
            "created_at": "2024-01-01T00:00:00",
        }
    )
    mock.list_campaigns = AsyncMock(return_value=[])
    mock.save_turn = AsyncMock()
    mock.update_campaign_status = AsyncMock()
    return mock


@pytest.fixture
def mock_s3():
    """Mock S3 client for testing"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    mock.store_results = AsyncMock(return_value="s3://bucket/key")
    mock.store_report = AsyncMock(return_value=("s3://bucket/report", "https://presigned-url"))
    return mock


@pytest.fixture
def mock_xray():
    """Mock X-Ray client for testing"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    mock.get_trace = AsyncMock(return_value={"Id": "test-trace-123", "Segments": []})
    return mock


@pytest.fixture
def mock_eventbridge():
    """Mock EventBridge client for testing"""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.close = AsyncMock()
    mock.publish_campaign_event = AsyncMock()
    mock.publish_turn_event = AsyncMock()
    return mock


@pytest.fixture
def mock_all_clients(mock_dynamodb, mock_s3, mock_xray, mock_eventbridge):
    """Returns dictionary of all mocked AWS clients"""
    return {
        "dynamodb": mock_dynamodb,
        "s3": mock_s3,
        "xray": mock_xray,
        "eventbridge": mock_eventbridge,
    }


@pytest.fixture
def container_with_mocks(fresh_container, mock_dynamodb, mock_s3, mock_xray, mock_eventbridge):
    """
    Container pre-configured with mocked clients

    Useful for testing components that depend on the container
    without making real AWS calls.
    """
    fresh_container._dynamodb = mock_dynamodb
    fresh_container._s3 = mock_s3
    fresh_container._xray = mock_xray
    fresh_container._eventbridge = mock_eventbridge
    fresh_container._connected = True
    return fresh_container


# ============================================================================
# Agent Factory Fixtures
# ============================================================================


@pytest.fixture
def mock_persona_factory():
    """Mock PersonaAgentFactory for testing"""
    from agenteval.agents.persona_agent import PersonaAgent

    factory = AsyncMock()
    mock_agent = AsyncMock(spec=PersonaAgent)
    mock_agent.agent_id = "persona-test-123"
    mock_agent.initialize = AsyncMock()
    mock_agent.generate_message = AsyncMock(return_value="Test message")
    mock_agent.process_response = AsyncMock()
    mock_agent.memory = MagicMock()
    mock_agent.memory.to_dict = MagicMock(return_value={})

    factory.create = AsyncMock(return_value=mock_agent)
    return factory


@pytest.fixture
def mock_redteam_factory():
    """Mock RedTeamAgentFactory for testing"""
    from agenteval.agents.redteam_agent import RedTeamAgent

    factory = AsyncMock()
    mock_agent = AsyncMock(spec=RedTeamAgent)
    mock_agent.agent_id = "redteam-test-123"
    mock_agent.initialize = AsyncMock()
    mock_agent.select_attack = MagicMock()

    factory.create = AsyncMock(return_value=mock_agent)
    return factory


@pytest.fixture
def mock_judge_factory():
    """Mock JudgeAgentFactory for testing"""
    from agenteval.agents.judge_agent import JudgeAgent

    factory = AsyncMock()
    mock_agent = AsyncMock(spec=JudgeAgent)
    mock_agent.agent_id = "judge-test-123"
    mock_agent.initialize = AsyncMock()
    mock_agent.evaluate_response = AsyncMock(
        return_value={"aggregate_scores": {"overall": 0.8}, "pass_fail": {"all_passed": True}}
    )

    factory.create = AsyncMock(return_value=mock_agent)
    return factory


@pytest.fixture
def mock_all_factories(mock_persona_factory, mock_redteam_factory, mock_judge_factory):
    """Returns dictionary of all mocked agent factories"""
    return {
        "persona": mock_persona_factory,
        "redteam": mock_redteam_factory,
        "judge": mock_judge_factory,
    }


# ============================================================================
# Service Fixtures
# ============================================================================


@pytest.fixture
def mock_orchestrator():
    """Mock CampaignOrchestrator for testing"""
    mock = AsyncMock()
    mock.create_campaign = AsyncMock(
        return_value={"campaign_id": "test-123", "campaign_type": "persona", "status": "created"}
    )
    mock.run_campaign = AsyncMock(
        return_value={"campaign_id": "test-123", "status": "completed", "turns": []}
    )
    mock.dynamodb = AsyncMock()
    return mock


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line("markers", "asyncio: mark test as async test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "unit: mark test as unit test")
