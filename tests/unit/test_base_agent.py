"""
Unit tests for BaseAgent.

Tests the abstract base class for all agent types.
"""

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest

from agenteval.agents.base import BaseAgent


# Concrete implementation for testing
class TestableAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execute_called = False

    async def execute(self, *args, **kwargs):
        """Concrete implementation of abstract method"""
        self.execute_called = True
        return {"status": "success", "args": args, "kwargs": kwargs}

    def _get_default_model(self) -> str:
        """Concrete implementation of abstract method"""
        return "anthropic.claude-haiku-4-5-20251001-v1:0"


class TestBaseAgentInitialization:
    """Test suite for BaseAgent initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        agent = TestableAgent()

        # Verify agent_id is UUID
        assert agent.agent_id is not None
        assert len(agent.agent_id) > 0
        try:
            UUID(agent.agent_id)
        except ValueError:
            pytest.fail("agent_id is not a valid UUID")

        # Verify agent_type defaults to class name
        assert agent.agent_type == "TestableAgent"

        # Verify bedrock is initially None
        assert agent.bedrock is None

        # Verify tracer is initialized
        assert agent.tracer is not None

    def test_init_custom_agent_id(self):
        """Test initialization with custom agent_id"""
        custom_id = "custom-agent-123"
        agent = TestableAgent(agent_id=custom_id)

        assert agent.agent_id == custom_id

    def test_init_custom_agent_type(self):
        """Test initialization with custom agent_type"""
        agent = TestableAgent(agent_type="CustomType")

        assert agent.agent_type == "CustomType"

    def test_abstract_execute_enforcement(self):
        """Test that execute() must be implemented"""
        # Attempt to instantiate without implementing execute()
        with pytest.raises(TypeError):

            class IncompleteAgent(BaseAgent):
                def _get_default_model(self):
                    return "model"

            IncompleteAgent()

    def test_abstract_get_default_model_enforcement(self):
        """Test that _get_default_model() must be implemented"""
        with pytest.raises(TypeError):

            class IncompleteAgent(BaseAgent):
                async def execute(self):
                    pass

            IncompleteAgent()


class TestBaseAgentLifecycle:
    """Test suite for BaseAgent lifecycle methods"""

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test agent initialization"""
        agent = TestableAgent()

        with patch("agenteval.agents.base.BedrockClient") as MockBedrock:
            mock_bedrock = AsyncMock()
            mock_bedrock.__aenter__ = AsyncMock(return_value=mock_bedrock)
            MockBedrock.return_value = mock_bedrock

            await agent.initialize()

            # Verify Bedrock client was created
            MockBedrock.assert_called_once()
            mock_bedrock.__aenter__.assert_called_once()
            assert agent.bedrock == mock_bedrock

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test agent cleanup"""
        agent = TestableAgent()

        # Setup mock bedrock client
        mock_bedrock = AsyncMock()
        mock_bedrock.__aexit__ = AsyncMock()
        agent.bedrock = mock_bedrock

        await agent.cleanup()

        # Verify Bedrock client was cleaned up
        mock_bedrock.__aexit__.assert_called_once_with(None, None, None)

    @pytest.mark.asyncio
    async def test_cleanup_no_bedrock(self):
        """Test cleanup when bedrock is None"""
        agent = TestableAgent()
        agent.bedrock = None

        # Should not raise error
        await agent.cleanup()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager"""
        agent = TestableAgent()

        with patch("agenteval.agents.base.BedrockClient") as MockBedrock:
            mock_bedrock = AsyncMock()
            mock_bedrock.__aenter__ = AsyncMock(return_value=mock_bedrock)
            mock_bedrock.__aexit__ = AsyncMock()
            MockBedrock.return_value = mock_bedrock

            async with agent as ctx_agent:
                # Verify agent is returned
                assert ctx_agent == agent
                assert agent.bedrock == mock_bedrock

            # Verify cleanup was called
            mock_bedrock.__aexit__.assert_called_once()


class TestBaseAgentLLMInvocation:
    """Test suite for LLM invocation"""

    @pytest.mark.asyncio
    async def test_invoke_llm_success(self):
        """Test successful LLM invocation"""
        agent = TestableAgent()

        # Setup mock bedrock client
        mock_bedrock = AsyncMock()
        mock_response = {
            "content": "Test response",
            "usage": {"input_tokens": 10, "output_tokens": 20},
            "stop_reason": "end_turn",
        }
        mock_bedrock.invoke_model = AsyncMock(return_value=mock_response)
        agent.bedrock = mock_bedrock

        # Invoke LLM
        result = await agent.invoke_llm(
            prompt="Test prompt", model_id="test-model", max_tokens=500, temperature=0.5
        )

        # Verify
        assert result["content"] == "Test response"
        assert result["usage"]["output_tokens"] == 20
        assert result["stop_reason"] == "end_turn"

        # Verify bedrock was called correctly
        mock_bedrock.invoke_model.assert_called_once_with(
            prompt="Test prompt",
            model_id="test-model",
            max_tokens=500,
            temperature=0.5,
            system_prompt=None,
        )

    @pytest.mark.asyncio
    async def test_invoke_llm_with_system_prompt(self):
        """Test LLM invocation with system prompt"""
        agent = TestableAgent()

        mock_bedrock = AsyncMock()
        mock_bedrock.invoke_model = AsyncMock(return_value={"content": "Response", "usage": {}})
        agent.bedrock = mock_bedrock

        await agent.invoke_llm(prompt="User prompt", system_prompt="System instructions")

        # Verify system prompt was passed
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        assert call_kwargs["system_prompt"] == "System instructions"

    @pytest.mark.asyncio
    async def test_invoke_llm_uses_default_model(self):
        """Test that invoke_llm uses default model when not specified"""
        agent = TestableAgent()

        mock_bedrock = AsyncMock()
        mock_bedrock.invoke_model = AsyncMock(return_value={"content": "Response", "usage": {}})
        agent.bedrock = mock_bedrock

        await agent.invoke_llm(prompt="Test")

        # Verify default model was used
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        assert call_kwargs["model_id"] == "anthropic.claude-haiku-4-5-20251001-v1:0"

    @pytest.mark.asyncio
    async def test_invoke_llm_no_bedrock_client(self):
        """Test invoke_llm fails when bedrock not initialized"""
        agent = TestableAgent()
        agent.bedrock = None

        with pytest.raises(RuntimeError, match="Bedrock client not initialized"):
            await agent.invoke_llm(prompt="Test")

    @pytest.mark.asyncio
    async def test_invoke_llm_error_handling(self):
        """Test LLM invocation error handling"""
        agent = TestableAgent()

        mock_bedrock = AsyncMock()
        mock_bedrock.invoke_model = AsyncMock(side_effect=Exception("Bedrock error"))
        agent.bedrock = mock_bedrock

        with pytest.raises(Exception, match="Bedrock error"):
            await agent.invoke_llm(prompt="Test")


class TestBaseAgentUtilities:
    """Test suite for utility methods"""

    def test_get_agent_info(self):
        """Test get_agent_info returns correct information"""
        agent = TestableAgent(agent_id="test-123", agent_type="TestType")

        info = agent.get_agent_info()

        assert info["agent_id"] == "test-123"
        assert info["agent_type"] == "TestType"

    def test_normalize_usage_dict(self):
        """Test _normalize_usage with dictionary input"""
        usage = {"input_tokens": 10, "output_tokens": 20}

        normalized = BaseAgent._normalize_usage(usage)

        assert normalized == {"input_tokens": 10, "output_tokens": 20}
        assert normalized is not usage  # Should be a copy

    def test_normalize_usage_none(self):
        """Test _normalize_usage with None input"""
        normalized = BaseAgent._normalize_usage(None)

        assert normalized == {}

    def test_normalize_usage_number(self):
        """Test _normalize_usage with number input"""
        normalized = BaseAgent._normalize_usage(100)

        assert normalized == {"total_tokens": 100}

    def test_normalize_usage_list_with_dict(self):
        """Test _normalize_usage with list containing dict"""
        usage_list = [{"tokens": 50}]

        normalized = BaseAgent._normalize_usage(usage_list)

        assert normalized == {"tokens": 50}

    def test_normalize_usage_list_with_number(self):
        """Test _normalize_usage with list containing number"""
        normalized = BaseAgent._normalize_usage([75])

        assert normalized == {"total_tokens": 75}

    def test_normalize_usage_unknown_type(self):
        """Test _normalize_usage with unknown type"""
        normalized = BaseAgent._normalize_usage("unknown")

        assert normalized == {"value": "unknown"}


class TestTokenExtraction:
    """Test suite for token extraction methods"""

    def test_extract_output_tokens_output_tokens_key(self):
        """Test extracting from output_tokens key"""
        usage = {"output_tokens": 42}

        tokens = BaseAgent._extract_output_tokens(usage)

        assert tokens == 42

    def test_extract_output_tokens_completion_tokens(self):
        """Test extracting from completion_tokens key"""
        usage = {"completion_tokens": 35}

        tokens = BaseAgent._extract_output_tokens(usage)

        assert tokens == 35

    def test_extract_output_tokens_nested_token_count(self):
        """Test extracting from nested tokenCount"""
        usage = {"tokenCount": {"outputTokenCount": 50}}

        tokens = BaseAgent._extract_output_tokens(usage)

        assert tokens == 50

    def test_extract_output_tokens_total_tokens_fallback(self):
        """Test falling back to total_tokens"""
        usage = {"total_tokens": 100}

        tokens = BaseAgent._extract_output_tokens(usage)

        assert tokens == 100

    def test_extract_output_tokens_non_dict(self):
        """Test extracting from non-dict value"""
        tokens = BaseAgent._extract_output_tokens(25)

        assert tokens == 25

    def test_extract_output_tokens_no_match(self):
        """Test when no token keys found"""
        usage = {"unknown_key": 100}

        tokens = BaseAgent._extract_output_tokens(usage)

        assert tokens == 0

    def test_coerce_token_value_int(self):
        """Test coercing integer value"""
        value = BaseAgent._coerce_token_value(42)

        assert value == 42

    def test_coerce_token_value_float(self):
        """Test coercing float value"""
        value = BaseAgent._coerce_token_value(42.7)

        assert value == 42

    def test_coerce_token_value_list_with_int(self):
        """Test coercing list with integer"""
        value = BaseAgent._coerce_token_value([30])

        assert value == 30

    def test_coerce_token_value_dict_with_value(self):
        """Test coercing dict with 'value' key"""
        value = BaseAgent._coerce_token_value({"value": 25})

        assert value == 25

    def test_coerce_token_value_none(self):
        """Test coercing None returns None"""
        value = BaseAgent._coerce_token_value(None)

        assert value is None

    def test_coerce_token_value_empty_list(self):
        """Test coercing empty list returns None"""
        value = BaseAgent._coerce_token_value([])

        assert value is None


class TestStopReasonExtraction:
    """Test suite for stop reason extraction"""

    def test_derive_stop_reason_stop_reason_key(self):
        """Test extracting from stop_reason key"""
        response = {"stop_reason": "end_turn"}

        reason = BaseAgent._derive_stop_reason(response)

        assert reason == "end_turn"

    def test_derive_stop_reason_stopReason_key(self):
        """Test extracting from stopReason key (camelCase)"""
        response = {"stopReason": "max_tokens"}

        reason = BaseAgent._derive_stop_reason(response)

        assert reason == "max_tokens"

    def test_derive_stop_reason_completion_reason(self):
        """Test extracting from completion_reason key"""
        response = {"completion_reason": "stop"}

        reason = BaseAgent._derive_stop_reason(response)

        assert reason == "stop"

    def test_derive_stop_reason_metadata_finish_reason(self):
        """Test extracting from metadata.finish_reason"""
        response = {"metadata": {"finish_reason": "length"}}

        reason = BaseAgent._derive_stop_reason(response)

        assert reason == "length"

    def test_derive_stop_reason_not_found(self):
        """Test when no stop reason found"""
        response = {"content": "test"}

        reason = BaseAgent._derive_stop_reason(response)

        assert reason == "unknown"

    def test_derive_stop_reason_empty_string(self):
        """Test when stop reason is empty string"""
        response = {"stop_reason": ""}

        reason = BaseAgent._derive_stop_reason(response)

        assert reason == "unknown"


class TestExecuteImplementation:
    """Test suite for execute method"""

    @pytest.mark.asyncio
    async def test_execute_called(self):
        """Test that execute method can be called"""
        agent = TestableAgent()

        result = await agent.execute(arg1="value1", arg2="value2")

        assert agent.execute_called is True
        assert result["status"] == "success"
        assert result["kwargs"]["arg1"] == "value1"
        assert result["kwargs"]["arg2"] == "value2"
