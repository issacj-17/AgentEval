"""
Test Utilities

Common helper functions and utilities for testing AgentEval components.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

# ============================================================================
# Mock Data Builders
# ============================================================================


def build_campaign_data(
    campaign_id: str = "test-campaign-123",
    campaign_type: str = "persona",
    status: str = "created",
    **kwargs,
) -> dict[str, Any]:
    """
    Build campaign data dictionary for testing

    Args:
        campaign_id: Campaign identifier
        campaign_type: Type of campaign (persona, red_team, combined)
        status: Campaign status
        **kwargs: Additional fields to override

    Returns:
        Campaign data dictionary
    """
    data = {
        "campaign_id": campaign_id,
        "campaign_type": campaign_type,
        "status": status,
        "target_url": "https://api.example.com/chat",
        "config": {"max_turns": 10, "persona_type": "frustrated_customer"},
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
        "stats": {"total_turns": 0, "completed_turns": 0, "failed_turns": 0, "avg_score": 0.0},
    }
    data.update(kwargs)
    return data


def build_turn_data(
    turn_id: str = "test-turn-1",
    campaign_id: str = "test-campaign-123",
    turn_number: int = 1,
    **kwargs,
) -> dict[str, Any]:
    """
    Build turn data dictionary for testing

    Args:
        turn_id: Turn identifier
        campaign_id: Parent campaign identifier
        turn_number: Turn sequence number
        **kwargs: Additional fields to override

    Returns:
        Turn data dictionary
    """
    data = {
        "turn_id": turn_id,
        "campaign_id": campaign_id,
        "turn_number": turn_number,
        "agent_type": "persona",
        "user_message": "Test message",
        "system_response": "Test response",
        "evaluation": {
            "aggregate_scores": {"overall": 0.8, "quality": 0.85, "safety": 0.9},
            "pass_fail": {"all_passed": True},
        },
        "status": "completed",
        "trace_id": "test-trace-123",
        "completed_at": "2024-01-01T00:01:00Z",
    }
    data.update(kwargs)
    return data


def build_evaluation_result(
    overall_score: float = 0.8, all_passed: bool = True, **kwargs
) -> dict[str, Any]:
    """
    Build evaluation result dictionary for testing

    Args:
        overall_score: Overall evaluation score
        all_passed: Whether all evaluation checks passed
        **kwargs: Additional fields to override

    Returns:
        Evaluation result dictionary
    """
    data = {
        "aggregate_scores": {
            "overall": overall_score,
            "quality": 0.85,
            "safety": 0.9,
            "helpfulness": 0.8,
        },
        "pass_fail": {"all_passed": all_passed, "quality_passed": True, "safety_passed": True},
        "detailed_scores": {"relevance": 0.9, "coherence": 0.85, "completeness": 0.75},
    }
    data.update(kwargs)
    return data


def build_trace_data(trace_id: str = "test-trace-123", **kwargs) -> dict[str, Any]:
    """
    Build trace data dictionary for testing

    Args:
        trace_id: Trace identifier
        **kwargs: Additional fields to override

    Returns:
        Trace data dictionary
    """
    data = {
        "Id": trace_id,
        "Duration": 1.5,
        "Segments": [
            {
                "Id": "segment-1",
                "Name": "llm-call",
                "StartTime": 1234567890.0,
                "EndTime": 1234567891.5,
                "Subsegments": [],
            }
        ],
    }
    data.update(kwargs)
    return data


# ============================================================================
# Mock Agent Builders
# ============================================================================


def build_mock_persona_agent(agent_id: str = "persona-test-123", **kwargs) -> AsyncMock:
    """
    Build mock PersonaAgent for testing

    Args:
        agent_id: Agent identifier
        **kwargs: Additional mock configuration

    Returns:
        Mocked PersonaAgent instance
    """
    mock = AsyncMock()
    mock.agent_id = agent_id
    mock.initialize = AsyncMock()
    mock.generate_message = AsyncMock(return_value="Test message from persona")
    mock.process_response = AsyncMock()
    mock.memory = MagicMock()
    mock.memory.to_dict = MagicMock(return_value={"frustration_level": 0.5, "goal_progress": 0.3})
    mock.memory.state = MagicMock()
    mock.memory.state.frustration_level = 0.5
    mock.memory.state.goal_progress = 0.3

    # Apply custom configuration
    for key, value in kwargs.items():
        setattr(mock, key, value)

    return mock


def build_mock_redteam_agent(agent_id: str = "redteam-test-123", **kwargs) -> AsyncMock:
    """
    Build mock RedTeamAgent for testing

    Args:
        agent_id: Agent identifier
        **kwargs: Additional mock configuration

    Returns:
        Mocked RedTeamAgent instance
    """
    mock = AsyncMock()
    mock.agent_id = agent_id
    mock.initialize = AsyncMock()
    mock.select_attack = MagicMock()

    # Mock attack
    mock_attack = MagicMock()
    mock_attack.generate_payload = MagicMock(return_value="Test attack payload")
    mock.select_attack.return_value = mock_attack

    # Apply custom configuration
    for key, value in kwargs.items():
        setattr(mock, key, value)

    return mock


def build_mock_judge_agent(agent_id: str = "judge-test-123", **kwargs) -> AsyncMock:
    """
    Build mock JudgeAgent for testing

    Args:
        agent_id: Agent identifier
        **kwargs: Additional mock configuration

    Returns:
        Mocked JudgeAgent instance
    """
    mock = AsyncMock()
    mock.agent_id = agent_id
    mock.initialize = AsyncMock()
    mock.evaluate_response = AsyncMock(return_value=build_evaluation_result())

    # Apply custom configuration
    for key, value in kwargs.items():
        setattr(mock, key, value)

    return mock


# ============================================================================
# Assertion Helpers
# ============================================================================


def assert_campaign_valid(campaign: dict[str, Any]) -> None:
    """
    Assert campaign data has required fields

    Args:
        campaign: Campaign data to validate

    Raises:
        AssertionError: If campaign is invalid
    """
    assert "campaign_id" in campaign, "Campaign missing campaign_id"
    assert "campaign_type" in campaign, "Campaign missing campaign_type"
    assert "status" in campaign, "Campaign missing status"
    assert "config" in campaign, "Campaign missing config"
    assert "created_at" in campaign, "Campaign missing created_at"


def assert_turn_valid(turn: dict[str, Any]) -> None:
    """
    Assert turn data has required fields

    Args:
        turn: Turn data to validate

    Raises:
        AssertionError: If turn is invalid
    """
    assert "turn_id" in turn, "Turn missing turn_id"
    assert "campaign_id" in turn, "Turn missing campaign_id"
    assert "turn_number" in turn, "Turn missing turn_number"
    assert "user_message" in turn, "Turn missing user_message"
    assert "system_response" in turn, "Turn missing system_response"
    assert "evaluation" in turn, "Turn missing evaluation"
    assert "status" in turn, "Turn missing status"


def assert_evaluation_valid(evaluation: dict[str, Any]) -> None:
    """
    Assert evaluation result has required fields

    Args:
        evaluation: Evaluation result to validate

    Raises:
        AssertionError: If evaluation is invalid
    """
    assert "aggregate_scores" in evaluation, "Evaluation missing aggregate_scores"
    assert "pass_fail" in evaluation, "Evaluation missing pass_fail"
    assert "overall" in evaluation["aggregate_scores"], "Evaluation missing overall score"
    assert "all_passed" in evaluation["pass_fail"], "Evaluation missing all_passed"


# ============================================================================
# Async Test Helpers
# ============================================================================


async def run_with_mocked_time(coro, mock_time_value=None):
    """
    Run async coroutine with mocked time

    Useful for testing time-dependent functionality.

    Args:
        coro: Async coroutine to run
        mock_time_value: Optional datetime to mock

    Returns:
        Result of coroutine execution
    """
    return await coro


def create_async_context_manager(value=None):
    """
    Create async context manager for testing

    Args:
        value: Value to return from __aenter__

    Returns:
        Async context manager mock
    """
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=value)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


# ============================================================================
# Container Test Helpers
# ============================================================================


def inject_mock_clients(container, mock_clients: dict[str, Any]) -> None:
    """
    Inject mocked clients into container

    Args:
        container: Container instance
        mock_clients: Dictionary of client_name -> mock_client
    """
    for client_name, mock_client in mock_clients.items():
        setattr(container, f"_{client_name}", mock_client)
    container._connected = True


def inject_mock_factories(container, mock_factories: dict[str, Any]) -> None:
    """
    Inject mocked factories into container

    Args:
        container: Container instance
        mock_factories: Dictionary of factory_name -> mock_factory
    """
    for factory_name, mock_factory in mock_factories.items():
        setattr(container, f"_{factory_name}_factory", mock_factory)


# ============================================================================
# FastAPI Test Helpers
# ============================================================================


def create_test_request(
    method: str = "GET",
    url: str = "/",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create test request data for FastAPI testing

    Args:
        method: HTTP method
        url: Request URL
        headers: Request headers
        body: Request body

    Returns:
        Request data dictionary
    """
    return {"method": method, "url": url, "headers": headers or {}, "body": body or {}}


# ============================================================================
# Configuration Helpers
# ============================================================================


def create_test_settings(**overrides) -> dict[str, Any]:
    """
    Create test settings with overrides

    Args:
        **overrides: Settings to override

    Returns:
        Settings dictionary
    """
    defaults = {
        "aws": {
            "region": "us-east-1",
            "profile": None,
            "access_key_id": None,
            "secret_access_key": None,
            "dynamodb_campaigns_table": "test-campaigns",
            "dynamodb_turns_table": "test-turns",
            "s3_results_bucket": "test-results",
            "s3_reports_bucket": "test-reports",
        },
        "app": {
            "api_key_enabled": False,
            "max_concurrent_campaigns": 100,
            "max_concurrent_turns": 3,
        },
    }

    # Deep merge overrides
    for key, value in overrides.items():
        if isinstance(value, dict) and key in defaults:
            defaults[key].update(value)
        else:
            defaults[key] = value

    return defaults
