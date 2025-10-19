"""
Integration tests for Agent Factories

Tests the factory pattern for agent creation with configuration validation.
"""

from unittest.mock import AsyncMock, patch

import pytest

from agenteval.agents.persona_agent import PersonaType
from agenteval.factories.judge_factory import JudgeAgentFactory
from agenteval.factories.persona_factory import PersonaAgentFactory
from agenteval.factories.redteam_factory import RedTeamAgentFactory
from agenteval.redteam.library import AttackCategory, AttackSeverity


class TestPersonaAgentFactory:
    """Test PersonaAgentFactory with configuration validation"""

    @pytest.fixture
    def factory(self):
        """Create factory instance"""
        return PersonaAgentFactory()

    @pytest.mark.asyncio
    async def test_create_frustrated_customer(self, factory):
        """Test creating frustrated customer persona"""
        with patch("agenteval.factories.persona_factory.PersonaAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent_class.return_value = mock_agent

            config = {
                "persona_type": "frustrated_customer",
                "initial_goal": "Get help with billing",
            }

            agent = await factory.create(config)

            mock_agent_class.assert_called_once_with(
                persona_type=PersonaType.FRUSTRATED_CUSTOMER, initial_goal="Get help with billing"
            )
            mock_agent.initialize.assert_called_once()
            assert agent == mock_agent

    @pytest.mark.asyncio
    async def test_create_technical_expert(self, factory):
        """Test creating technical expert persona"""
        with patch("agenteval.factories.persona_factory.PersonaAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent_class.return_value = mock_agent

            config = {"persona_type": "technical_expert", "initial_goal": "Debug the API issue"}

            agent = await factory.create(config)

            mock_agent_class.assert_called_once_with(
                persona_type=PersonaType.TECHNICAL_EXPERT, initial_goal="Debug the API issue"
            )
            assert agent == mock_agent

    @pytest.mark.asyncio
    async def test_create_with_default_goal(self, factory):
        """Test creating persona with default initial goal"""
        with patch("agenteval.factories.persona_factory.PersonaAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent_class.return_value = mock_agent

            config = {"persona_type": "frustrated_customer"}

            agent = await factory.create(config)

            mock_agent_class.assert_called_once_with(
                persona_type=PersonaType.FRUSTRATED_CUSTOMER, initial_goal="Get help with my issue"
            )

    @pytest.mark.asyncio
    async def test_create_missing_persona_type(self, factory):
        """Test validation error when persona_type is missing"""
        with pytest.raises(ValueError, match="Missing required configuration keys"):
            await factory.create({})

    @pytest.mark.asyncio
    async def test_create_invalid_persona_type(self, factory):
        """Test validation error with invalid persona type"""
        config = {"persona_type": "invalid_persona", "initial_goal": "Test"}

        with pytest.raises(ValueError, match="Invalid persona_type"):
            await factory.create(config)

    @pytest.mark.asyncio
    async def test_create_initialization_failure(self, factory):
        """Test handling of agent initialization failure"""
        with patch("agenteval.factories.persona_factory.PersonaAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock(side_effect=RuntimeError("Init failed"))
            mock_agent_class.return_value = mock_agent

            config = {"persona_type": "frustrated_customer", "initial_goal": "Test"}

            with pytest.raises(RuntimeError, match="Failed to create PersonaAgent"):
                await factory.create(config)

    def test_convenience_method_frustrated_customer(self, factory):
        """Test convenience method for frustrated customer"""
        with (
            patch("agenteval.factories.persona_factory.PersonaAgent") as mock_agent_class,
            patch("asyncio.run") as mock_run,
        ):
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_run.return_value = mock_agent

            result = factory.create_frustrated_customer("Fix my account")

            assert result == mock_agent
            mock_run.assert_called_once()

    def test_convenience_method_technical_expert(self, factory):
        """Test convenience method for technical expert"""
        with (
            patch("agenteval.factories.persona_factory.PersonaAgent") as mock_agent_class,
            patch("asyncio.run") as mock_run,
        ):
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_run.return_value = mock_agent

            result = factory.create_technical_expert("Debug API")

            assert result == mock_agent
            mock_run.assert_called_once()


class TestRedTeamAgentFactory:
    """Test RedTeamAgentFactory with attack configuration validation"""

    @pytest.fixture
    def factory(self):
        """Create factory instance"""
        return RedTeamAgentFactory()

    @pytest.mark.asyncio
    async def test_create_with_all_parameters(self, factory):
        """Test creating red team agent with all parameters"""
        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent.agent_id = "agent-123"
            mock_agent_class.return_value = mock_agent

            config = {
                "attack_categories": ["injection", "jailbreak"],
                "severity_threshold": "high",
                "use_mutations": True,
            }

            with pytest.warns(UserWarning):
                agent = await factory.create(config)

            mock_agent_class.assert_called_once_with(
                attack_categories=[AttackCategory.INJECTION, AttackCategory.JAILBREAK],
                severity_threshold=AttackSeverity.HIGH,
            )
            mock_agent.initialize.assert_called_once()
            assert agent == mock_agent

    @pytest.mark.asyncio
    async def test_create_with_minimal_config(self, factory):
        """Test creating red team agent with minimal config"""
        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent.agent_id = "agent-456"
            mock_agent_class.return_value = mock_agent

            config = {}

            agent = await factory.create(config)

            mock_agent_class.assert_called_once_with(
                attack_categories=None, severity_threshold=None
            )

    @pytest.mark.asyncio
    async def test_create_without_mutations(self, factory):
        """Test creating red team agent with mutations disabled"""
        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent_class.return_value = mock_agent

            config = {"use_mutations": False}

            with pytest.warns(UserWarning):
                agent = await factory.create(config)

            mock_agent_class.assert_called_once_with(
                attack_categories=None, severity_threshold=None
            )

    @pytest.mark.asyncio
    async def test_create_single_attack_category(self, factory):
        """Test creating red team agent with single attack category"""
        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent_class.return_value = mock_agent

            config = {"attack_categories": ["injection"]}

            agent = await factory.create(config)

            mock_agent_class.assert_called_once_with(
                attack_categories=[AttackCategory.INJECTION], severity_threshold=None
            )

    @pytest.mark.asyncio
    async def test_create_all_severity_levels(self, factory):
        """Test creating red team agent with each severity level"""
        severities = ["low", "medium", "high", "critical"]

        for severity in severities:
            with patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class:
                mock_agent = AsyncMock()
                mock_agent.initialize = AsyncMock()
                mock_agent_class.return_value = mock_agent

                config = {"severity_threshold": severity}

                agent = await factory.create(config)

                expected_severity = AttackSeverity(severity)
                mock_agent_class.assert_called_once_with(
                    attack_categories=None, severity_threshold=expected_severity
                )

    @pytest.mark.asyncio
    async def test_create_invalid_attack_category(self, factory):
        """Test validation error with invalid attack category"""
        config = {"attack_categories": ["invalid_category"]}

        with pytest.raises(ValueError, match="Invalid attack category"):
            await factory.create(config)

    @pytest.mark.asyncio
    async def test_create_invalid_severity_threshold(self, factory):
        """Test validation error with invalid severity threshold"""
        config = {"severity_threshold": "invalid_severity"}

        with pytest.raises(ValueError, match="Invalid severity_threshold"):
            await factory.create(config)

    @pytest.mark.asyncio
    async def test_create_mixed_valid_invalid_categories(self, factory):
        """Test validation error with mixed valid/invalid attack categories"""
        config = {"attack_categories": ["injection", "invalid_category"]}

        with pytest.raises(ValueError, match="Invalid attack category"):
            await factory.create(config)

    @pytest.mark.asyncio
    async def test_create_initialization_failure(self, factory):
        """Test handling of agent initialization failure"""
        with patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock(side_effect=RuntimeError("Init failed"))
            mock_agent_class.return_value = mock_agent

            config = {"attack_categories": ["injection"]}

            with pytest.raises(RuntimeError, match="Failed to create RedTeamAgent"):
                await factory.create(config)

    def test_convenience_method_injection_focused(self, factory):
        """Test convenience method for injection-focused agent"""
        with (
            patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class,
            patch("asyncio.run") as mock_run,
        ):
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_run.return_value = mock_agent

            result = factory.create_injection_focused(severity_threshold="high")

            assert result == mock_agent
            mock_run.assert_called_once()

    def test_convenience_method_full_spectrum(self, factory):
        """Test convenience method for full spectrum agent"""
        with (
            patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_agent_class,
            patch("asyncio.run") as mock_run,
        ):
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_run.return_value = mock_agent

            result = factory.create_full_spectrum(severity_threshold="medium")

            assert result == mock_agent
            mock_run.assert_called_once()


class TestJudgeAgentFactory:
    """Test JudgeAgentFactory with minimal configuration"""

    @pytest.fixture
    def factory(self):
        """Create factory instance"""
        return JudgeAgentFactory()

    @pytest.mark.asyncio
    async def test_create_with_empty_config(self, factory):
        """Test creating judge agent with empty config"""
        with patch("agenteval.factories.judge_factory.JudgeAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent.agent_id = "judge-123"
            mock_agent_class.return_value = mock_agent

            agent = await factory.create({})

            mock_agent_class.assert_called_once()
            mock_agent.initialize.assert_called_once()
            assert agent == mock_agent

    @pytest.mark.asyncio
    async def test_create_with_no_config(self, factory):
        """Test creating judge agent with None config"""
        with patch("agenteval.factories.judge_factory.JudgeAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_agent_class.return_value = mock_agent

            agent = await factory.create(None)

            mock_agent_class.assert_called_once()
            mock_agent.initialize.assert_called_once()
            assert agent == mock_agent

    @pytest.mark.asyncio
    async def test_create_initialization_failure(self, factory):
        """Test handling of agent initialization failure"""
        with patch("agenteval.factories.judge_factory.JudgeAgent") as mock_agent_class:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock(side_effect=RuntimeError("Init failed"))
            mock_agent_class.return_value = mock_agent

            with pytest.raises(RuntimeError, match="Failed to create JudgeAgent"):
                await factory.create()

    def test_convenience_method_create_sync(self, factory):
        """Test synchronous convenience method"""
        with (
            patch("agenteval.factories.judge_factory.JudgeAgent") as mock_agent_class,
            patch("asyncio.run") as mock_run,
        ):
            mock_agent = AsyncMock()
            mock_agent_class.return_value = mock_agent
            mock_run.return_value = mock_agent

            result = factory.create_sync()

            assert result == mock_agent
            mock_run.assert_called_once()


class TestAgentFactoryIntegration:
    """Integration tests for factories working together"""

    @pytest.mark.asyncio
    async def test_create_all_agent_types(self):
        """Test creating all three agent types in sequence"""
        persona_factory = PersonaAgentFactory()
        redteam_factory = RedTeamAgentFactory()
        judge_factory = JudgeAgentFactory()

        with (
            patch("agenteval.factories.persona_factory.PersonaAgent") as mock_persona,
            patch("agenteval.factories.redteam_factory.RedTeamAgent") as mock_redteam,
            patch("agenteval.factories.judge_factory.JudgeAgent") as mock_judge,
        ):
            # Setup mocks
            for mock_class in [mock_persona, mock_redteam, mock_judge]:
                mock_agent = AsyncMock()
                mock_agent.initialize = AsyncMock()
                mock_class.return_value = mock_agent

            # Create agents
            persona = await persona_factory.create(
                {"persona_type": "frustrated_customer", "initial_goal": "Get help"}
            )
            redteam = await redteam_factory.create(
                {"attack_categories": ["injection"], "severity_threshold": "medium"}
            )
            judge = await judge_factory.create()

            # Verify all created
            assert persona is not None
            assert redteam is not None
            assert judge is not None

    @pytest.mark.asyncio
    async def test_factory_error_isolation(self):
        """Test that errors in one factory don't affect others"""
        persona_factory = PersonaAgentFactory()
        judge_factory = JudgeAgentFactory()

        # First factory should fail
        with pytest.raises(ValueError, match="Invalid persona_type"):
            await persona_factory.create({"persona_type": "invalid"})

        # Second factory should still work
        with patch("agenteval.factories.judge_factory.JudgeAgent") as mock_judge:
            mock_agent = AsyncMock()
            mock_agent.initialize = AsyncMock()
            mock_judge.return_value = mock_agent

            judge = await judge_factory.create()
            assert judge is not None
