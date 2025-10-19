"""
Integration tests for CampaignOrchestrator with Agent Factories

Tests orchestrator behavior with injected factory dependencies.
Demonstrates how to test components using the DI pattern.
"""

from unittest.mock import AsyncMock, patch

import pytest

from tests.test_utils import (
    build_campaign_data,
    build_mock_judge_agent,
    build_mock_persona_agent,
    build_mock_redteam_agent,
)


class TestOrchestratorWithFactories:
    """Test orchestrator using injected factories"""

    @pytest.fixture
    def orchestrator_with_mocks(
        self,
        mock_dynamodb,
        mock_s3,
        mock_xray,
        mock_eventbridge,
        mock_persona_factory,
        mock_redteam_factory,
        mock_judge_factory,
    ):
        """Create orchestrator with all dependencies mocked"""
        from agenteval.orchestration.campaign import CampaignOrchestrator

        orchestrator = CampaignOrchestrator(
            dynamodb_client=mock_dynamodb,
            s3_client=mock_s3,
            xray_client=mock_xray,
            eventbridge_client=mock_eventbridge,
            persona_factory=mock_persona_factory,
            redteam_factory=mock_redteam_factory,
            judge_factory=mock_judge_factory,
        )

        return orchestrator

    @pytest.mark.asyncio
    async def test_orchestrator_uses_persona_factory(
        self, orchestrator_with_mocks, mock_persona_factory
    ):
        """Test orchestrator uses injected persona factory"""
        # Setup
        config = {"persona_type": "frustrated_customer", "initial_goal": "Get help"}

        # Execute
        agent = await orchestrator_with_mocks._create_persona_agent(config)

        # Verify factory was called
        mock_persona_factory.create.assert_called_once()
        call_args = mock_persona_factory.create.call_args[0][0]
        assert call_args["persona_type"] == "frustrated_customer"
        assert call_args["initial_goal"] == "Get help"

    @pytest.mark.asyncio
    async def test_orchestrator_uses_redteam_factory(
        self, orchestrator_with_mocks, mock_redteam_factory
    ):
        """Test orchestrator uses injected red team factory"""
        # Setup
        config = {"attack_categories": ["injection"], "severity_threshold": "high"}

        # Execute
        agent = await orchestrator_with_mocks._create_redteam_agent(config)

        # Verify factory was called
        mock_redteam_factory.create.assert_called_once()
        call_args = mock_redteam_factory.create.call_args[0][0]
        assert call_args["attack_categories"] == ["injection"]
        assert call_args["severity_threshold"] == "high"

    @pytest.mark.asyncio
    async def test_orchestrator_uses_judge_factory(
        self, orchestrator_with_mocks, mock_judge_factory
    ):
        """Test orchestrator uses injected judge factory for campaign execution"""

        # Setup campaign data
        campaign_data = build_campaign_data(campaign_type="persona", status="created")

        orchestrator_with_mocks.dynamodb.get_campaign = AsyncMock(return_value=campaign_data)
        orchestrator_with_mocks.dynamodb.update_campaign_status = AsyncMock()
        orchestrator_with_mocks.dynamodb.update_campaign_stats = AsyncMock()

        # Mock HTTP client
        orchestrator_with_mocks._http_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"response": "Test response"})
        mock_response.raise_for_status = AsyncMock()
        orchestrator_with_mocks._http_client.post = AsyncMock(return_value=mock_response)

        # Mock _execute_turns_sequential to verify factory is used
        async def mock_execute_turns(
            campaign_id,
            campaign,
            campaign_type,
            persona_agent,
            redteam_agent,
            judge_agent,
            max_turns,
        ):
            # Verify judge agent came from factory
            assert judge_agent.agent_id == "judge-test-123"
            return []

        orchestrator_with_mocks._execute_turns_sequential = mock_execute_turns

        # Mock report generation to avoid ZeroDivisionError with empty turns
        async def mock_generate_report(campaign_id, turn_results, **kwargs):
            return {
                "campaign_id": campaign_id,
                "summary": {"total_turns": 0},
                "aggregate_metrics": {"overall_score": 0.0},
                "recommendations": [],
            }

        orchestrator_with_mocks.generate_campaign_report = mock_generate_report

        # Execute
        with patch.object(orchestrator_with_mocks, "_clients_connected", True):
            result = await orchestrator_with_mocks._execute_campaign_impl(
                campaign_id="test-123", max_turns=5, enable_parallel_turns=False
            )

        # Verify judge factory was called
        mock_judge_factory.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_factory_mocking_enables_test_isolation(
        self, mock_dynamodb, mock_s3, mock_xray, mock_eventbridge
    ):
        """Test that factory mocking enables proper test isolation"""
        from agenteval.orchestration.campaign import CampaignOrchestrator

        # Create two mock factories with different behaviors
        mock_factory1 = AsyncMock()
        mock_agent1 = build_mock_persona_agent(agent_id="agent-1")
        mock_factory1.create = AsyncMock(return_value=mock_agent1)

        mock_factory2 = AsyncMock()
        mock_agent2 = build_mock_persona_agent(agent_id="agent-2")
        mock_factory2.create = AsyncMock(return_value=mock_agent2)

        # Create two orchestrators with different factories
        orch1 = CampaignOrchestrator(
            dynamodb_client=mock_dynamodb,
            s3_client=mock_s3,
            xray_client=mock_xray,
            eventbridge_client=mock_eventbridge,
            persona_factory=mock_factory1,
            redteam_factory=AsyncMock(),
            judge_factory=AsyncMock(),
        )

        orch2 = CampaignOrchestrator(
            dynamodb_client=mock_dynamodb,
            s3_client=mock_s3,
            xray_client=mock_xray,
            eventbridge_client=mock_eventbridge,
            persona_factory=mock_factory2,
            redteam_factory=AsyncMock(),
            judge_factory=AsyncMock(),
        )

        # Execute with different orchestrators
        agent1 = await orch1._create_persona_agent({"persona_type": "frustrated_customer"})
        agent2 = await orch2._create_persona_agent({"persona_type": "frustrated_customer"})

        # Verify proper isolation
        assert agent1.agent_id == "agent-1"
        assert agent2.agent_id == "agent-2"
        mock_factory1.create.assert_called_once()
        mock_factory2.create.assert_called_once()


class TestOrchestratorFactoryIntegration:
    """Test orchestrator factory integration patterns"""

    @pytest.mark.asyncio
    async def test_custom_factory_behavior(
        self, mock_dynamodb, mock_s3, mock_xray, mock_eventbridge
    ):
        """Test orchestrator works with custom factory implementations"""
        from agenteval.orchestration.campaign import CampaignOrchestrator

        # Create custom factory that tracks calls
        call_count = {"persona": 0, "redteam": 0, "judge": 0}

        persona_factory = AsyncMock()

        async def custom_persona_create(config):
            call_count["persona"] += 1
            return build_mock_persona_agent()

        persona_factory.create = custom_persona_create

        redteam_factory = AsyncMock()

        async def custom_redteam_create(config):
            call_count["redteam"] += 1
            return build_mock_redteam_agent()

        redteam_factory.create = custom_redteam_create

        judge_factory = AsyncMock()

        async def custom_judge_create(config=None):
            call_count["judge"] += 1
            return build_mock_judge_agent()

        judge_factory.create = custom_judge_create

        # Create orchestrator
        orch = CampaignOrchestrator(
            dynamodb_client=mock_dynamodb,
            s3_client=mock_s3,
            xray_client=mock_xray,
            eventbridge_client=mock_eventbridge,
            persona_factory=persona_factory,
            redteam_factory=redteam_factory,
            judge_factory=judge_factory,
        )

        # Execute agent creation
        await orch._create_persona_agent({"persona_type": "frustrated_customer"})
        await orch._create_redteam_agent({"attack_categories": ["injection"]})

        # Verify custom behavior was executed
        assert call_count["persona"] == 1
        assert call_count["redteam"] == 1

    @pytest.mark.asyncio
    async def test_factory_error_handling(
        self, mock_dynamodb, mock_s3, mock_xray, mock_eventbridge
    ):
        """Test orchestrator handles factory errors gracefully"""
        from agenteval.orchestration.campaign import CampaignOrchestrator

        # Create factory that raises error
        persona_factory = AsyncMock()
        persona_factory.create = AsyncMock(side_effect=ValueError("Invalid persona type"))

        orch = CampaignOrchestrator(
            dynamodb_client=mock_dynamodb,
            s3_client=mock_s3,
            xray_client=mock_xray,
            eventbridge_client=mock_eventbridge,
            persona_factory=persona_factory,
            redteam_factory=AsyncMock(),
            judge_factory=AsyncMock(),
        )

        # Execute and verify error is propagated
        with pytest.raises(ValueError, match="Invalid persona type"):
            await orch._create_persona_agent({"persona_type": "invalid"})


class TestFactoryDependencyInjection:
    """Test factory dependency injection patterns"""

    def test_orchestrator_accepts_factory_injection(self, mock_all_clients, mock_all_factories):
        """Test orchestrator constructor accepts factory injection"""
        from agenteval.orchestration.campaign import CampaignOrchestrator

        orch = CampaignOrchestrator(
            dynamodb_client=mock_all_clients["dynamodb"],
            s3_client=mock_all_clients["s3"],
            xray_client=mock_all_clients["xray"],
            eventbridge_client=mock_all_clients["eventbridge"],
            persona_factory=mock_all_factories["persona"],
            redteam_factory=mock_all_factories["redteam"],
            judge_factory=mock_all_factories["judge"],
        )

        # Verify factories are set
        assert orch.persona_factory is mock_all_factories["persona"]
        assert orch.redteam_factory is mock_all_factories["redteam"]
        assert orch.judge_factory is mock_all_factories["judge"]

    def test_orchestrator_uses_default_factories_when_not_injected(self):
        """Test orchestrator creates default factories when not injected"""
        from agenteval.factories.judge_factory import JudgeAgentFactory
        from agenteval.factories.persona_factory import PersonaAgentFactory
        from agenteval.factories.redteam_factory import RedTeamAgentFactory
        from agenteval.orchestration.campaign import CampaignOrchestrator

        # Create orchestrator without factory injection
        orch = CampaignOrchestrator()

        # Verify default factories are created
        assert isinstance(orch.persona_factory, PersonaAgentFactory)
        assert isinstance(orch.redteam_factory, RedTeamAgentFactory)
        assert isinstance(orch.judge_factory, JudgeAgentFactory)

    def test_container_injects_factories_into_orchestrator(self, fresh_container):
        """Test container properly injects factories into orchestrator"""
        # Get orchestrator from container
        orch = fresh_container.campaign_orchestrator()

        # Verify factories came from container
        assert orch.persona_factory is fresh_container.persona_factory()
        assert orch.redteam_factory is fresh_container.redteam_factory()
        assert orch.judge_factory is fresh_container.judge_factory()


class TestFactoryTestingPatterns:
    """Demonstrate common factory testing patterns"""

    @pytest.fixture
    def orchestrator_with_mocks(
        self,
        mock_dynamodb,
        mock_s3,
        mock_xray,
        mock_eventbridge,
        mock_persona_factory,
        mock_redteam_factory,
        mock_judge_factory,
    ):
        """Create orchestrator with all dependencies mocked"""
        from agenteval.orchestration.campaign import CampaignOrchestrator

        orchestrator = CampaignOrchestrator(
            dynamodb_client=mock_dynamodb,
            s3_client=mock_s3,
            xray_client=mock_xray,
            eventbridge_client=mock_eventbridge,
            persona_factory=mock_persona_factory,
            redteam_factory=mock_redteam_factory,
            judge_factory=mock_judge_factory,
        )

        return orchestrator

    @pytest.mark.asyncio
    async def test_verify_factory_configuration(
        self, orchestrator_with_mocks, mock_persona_factory
    ):
        """Test verifying correct configuration passed to factory"""
        # Execute
        await orchestrator_with_mocks._create_persona_agent(
            {"persona_type": "technical_expert", "initial_goal": "Debug the issue"}
        )

        # Verify exact configuration
        mock_persona_factory.create.assert_called_once()
        config = mock_persona_factory.create.call_args[0][0]

        assert config["persona_type"] == "technical_expert"
        assert config["initial_goal"] == "Debug the issue"

    @pytest.mark.asyncio
    async def test_verify_agent_initialization(self, orchestrator_with_mocks, mock_persona_factory):
        """Test verifying agent is properly initialized"""
        # Setup factory to return mock agent
        mock_agent = build_mock_persona_agent()
        mock_persona_factory.create = AsyncMock(return_value=mock_agent)

        # Execute
        agent = await orchestrator_with_mocks._create_persona_agent(
            {"persona_type": "frustrated_customer"}
        )

        # Verify agent was returned and has expected properties
        assert agent.agent_id == "persona-test-123"
        assert agent is mock_agent

    @pytest.mark.asyncio
    async def test_count_factory_calls(
        self,
        orchestrator_with_mocks,
        mock_persona_factory,
        mock_redteam_factory,
        mock_judge_factory,
    ):
        """Test counting how many times factories are called"""
        # Execute multiple agent creations
        await orchestrator_with_mocks._create_persona_agent({"persona_type": "frustrated_customer"})
        await orchestrator_with_mocks._create_persona_agent({"persona_type": "technical_expert"})
        await orchestrator_with_mocks._create_redteam_agent({"attack_categories": ["injection"]})

        # Verify call counts
        assert mock_persona_factory.create.call_count == 2
        assert mock_redteam_factory.create.call_count == 1
        assert mock_judge_factory.create.call_count == 0  # Not called yet
