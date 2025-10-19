"""
Unit tests for Agent Factories.

Tests all factory classes that create agent instances.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.factories.base import AgentFactory
from agenteval.factories.judge_factory import JudgeAgentFactory
from agenteval.factories.persona_factory import PersonaAgentFactory
from agenteval.factories.redteam_factory import RedTeamAgentFactory
from agenteval.factories.reporter_factory import ReporterAgentFactory


# Concrete test implementation of abstract AgentFactory
class TestAgentFactory(AgentFactory[str]):
    """Concrete factory for testing"""

    async def create(self, config: dict[str, Any]) -> str:
        """Test implementation"""
        self._validate_config(config, ["test_key"])
        self._log_creation("test", config)
        return f"agent-{config['test_key']}"


class TestBaseAgentFactory:
    """Test suite for base AgentFactory"""

    def test_init(self):
        """Test factory initialization"""
        factory = TestAgentFactory()

        assert factory.logger is not None
        assert factory.logger.name == "TestAgentFactory"

    def test_validate_config_valid(self):
        """Test config validation with valid config"""
        factory = TestAgentFactory()
        config = {"test_key": "value", "other": "data"}

        # Should not raise
        factory._validate_config(config, ["test_key"])

    def test_validate_config_missing_keys(self):
        """Test config validation with missing keys"""
        factory = TestAgentFactory()
        config = {"other": "data"}

        with pytest.raises(ValueError, match="Missing required configuration keys"):
            factory._validate_config(config, ["test_key", "another_key"])

    def test_log_creation(self):
        """Test logging agent creation"""
        factory = TestAgentFactory()

        with patch.object(factory.logger, "info") as mock_info:
            factory._log_creation("test_agent", {"key": "value"})

            mock_info.assert_called_once()
            call_args = mock_info.call_args
            assert "Creating test_agent agent" in str(call_args)

    @pytest.mark.asyncio
    async def test_create_implementation(self):
        """Test concrete create implementation"""
        factory = TestAgentFactory()
        config = {"test_key": "123"}

        result = await factory.create(config)

        assert result == "agent-123"


class TestPersonaAgentFactory:
    """Test suite for PersonaAgentFactory"""

    def test_init(self):
        """Test persona factory initialization"""
        factory = PersonaAgentFactory()

        assert factory.logger is not None

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful persona agent creation"""
        factory = PersonaAgentFactory()
        config = {"persona_type": "frustrated_customer", "initial_goal": "Test goal"}

        with patch("agenteval.factories.persona_factory.PersonaAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.agent_id = "test-123"
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            result = await factory.create(config)

            assert result == mock_agent
            MockAgent.assert_called_once()
            mock_agent.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_missing_config(self):
        """Test creation with missing required config"""
        factory = PersonaAgentFactory()
        config = {"initial_goal": "Test"}  # Missing persona_type

        with pytest.raises(ValueError, match="Missing required configuration keys"):
            await factory.create(config)

    @pytest.mark.asyncio
    async def test_create_invalid_persona_type(self):
        """Test creation with invalid persona type"""
        factory = PersonaAgentFactory()
        config = {"persona_type": "invalid_type"}

        with pytest.raises(ValueError, match="Invalid persona_type"):
            await factory.create(config)

    @pytest.mark.asyncio
    async def test_create_with_default_goal(self):
        """Test creation uses default goal when not provided"""
        factory = PersonaAgentFactory()
        config = {"persona_type": "frustrated_customer"}

        with patch("agenteval.factories.persona_factory.PersonaAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.agent_id = "test-123"
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            await factory.create(config)

            # Verify default goal was used
            call_kwargs = MockAgent.call_args.kwargs
            assert call_kwargs["initial_goal"] == "Get help with my issue"

    @pytest.mark.asyncio
    async def test_create_initialization_failure(self):
        """Test handling of agent initialization failure"""
        factory = PersonaAgentFactory()
        config = {"persona_type": "frustrated_customer"}

        with patch("agenteval.factories.persona_factory.PersonaAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock(side_effect=Exception("Init failed"))
            MockAgent.return_value = mock_agent

            with pytest.raises(RuntimeError, match="Failed to create PersonaAgent"):
                await factory.create(config)


class TestJudgeAgentFactory:
    """Test suite for JudgeAgentFactory"""

    def test_init(self):
        """Test judge factory initialization"""
        factory = JudgeAgentFactory()

        assert factory.logger is not None

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful judge agent creation"""
        factory = JudgeAgentFactory()
        config = {"evaluation_criteria": ["accuracy", "relevance"]}

        with patch("agenteval.factories.judge_factory.JudgeAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.agent_id = "judge-123"
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            result = await factory.create(config)

            assert result == mock_agent
            MockAgent.assert_called_once()
            mock_agent.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_defaults(self):
        """Test creation with default configuration"""
        factory = JudgeAgentFactory()
        config = {}  # Empty config should use defaults

        with patch("agenteval.factories.judge_factory.JudgeAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            result = await factory.create(config)

            assert result == mock_agent

    @pytest.mark.asyncio
    async def test_create_initialization_failure(self):
        """Test handling of initialization failure"""
        factory = JudgeAgentFactory()
        config = {}

        with patch("agenteval.factories.judge_factory.JudgeAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock(side_effect=Exception("Init failed"))
            MockAgent.return_value = mock_agent

            with pytest.raises(RuntimeError, match="Failed to create JudgeAgent"):
                await factory.create(config)


class TestRedTeamAgentFactory:
    """Test suite for RedTeamAgentFactory"""

    def test_init(self):
        """Test redteam factory initialization"""
        factory = RedTeamAgentFactory()

        assert factory.logger is not None

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful redteam agent creation"""
        factory = RedTeamAgentFactory()
        config = {"attack_categories": ["injection", "jailbreak"], "severity_threshold": "medium"}

        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.agent_id = "redteam-123"
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            result = await factory.create(config)

            assert result == mock_agent
            MockAgent.assert_called_once()
            mock_agent.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_empty_config(self):
        """Test creation with empty config (all parameters optional)"""
        factory = RedTeamAgentFactory()
        config = {}  # Empty config is valid for RedTeam

        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            result = await factory.create(config)

            assert result == mock_agent

    @pytest.mark.asyncio
    async def test_create_with_defaults(self):
        """Test creation uses default values"""
        factory = RedTeamAgentFactory()
        config = {"attack_categories": ["injection"]}

        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            await factory.create(config)

            MockAgent.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_initialization_failure(self):
        """Test handling of initialization failure"""
        factory = RedTeamAgentFactory()
        config = {"attack_categories": ["injection"]}

        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock(side_effect=Exception("Init failed"))
            MockAgent.return_value = mock_agent

            with pytest.raises(RuntimeError, match="Failed to create RedTeamAgent"):
                await factory.create(config)


class TestReporterAgentFactory:
    """Test suite for ReporterAgentFactory"""

    def test_init(self):
        """Test reporter factory initialization"""
        factory = ReporterAgentFactory()

        assert factory.logger is not None

    @pytest.mark.asyncio
    async def test_create_success(self):
        """Test successful reporter agent creation"""
        factory = ReporterAgentFactory()
        config = {"report_type": "comprehensive"}

        with patch("agenteval.factories.reporter_factory.ReporterAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.agent_id = "reporter-123"
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            result = await factory.create(config)

            assert result == mock_agent
            MockAgent.assert_called_once()
            mock_agent.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_with_custom_model(self):
        """Test creation with custom model ID"""
        factory = ReporterAgentFactory()
        config = {"model_id": "custom-model-id"}

        with patch("agenteval.factories.reporter_factory.ReporterAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            await factory.create(config)

            call_kwargs = MockAgent.call_args.kwargs
            assert call_kwargs.get("model_id") == "custom-model-id"

    @pytest.mark.asyncio
    async def test_create_with_defaults(self):
        """Test creation with default configuration"""
        factory = ReporterAgentFactory()
        config = {}

        with patch("agenteval.factories.reporter_factory.ReporterAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock()
            MockAgent.return_value = mock_agent

            result = await factory.create(config)

            assert result == mock_agent

    @pytest.mark.asyncio
    async def test_create_initialization_failure(self):
        """Test handling of initialization failure"""
        factory = ReporterAgentFactory()
        config = {}

        with patch("agenteval.factories.reporter_factory.ReporterAgent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.initialize = AsyncMock(side_effect=Exception("Init failed"))
            MockAgent.return_value = mock_agent

            with pytest.raises(RuntimeError, match="Reporter agent creation failed"):
                await factory.create(config)
