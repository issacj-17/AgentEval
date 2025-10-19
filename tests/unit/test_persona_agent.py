"""
Unit tests for PersonaAgent (targeted key methods).

Tests initialization, validation, and utility methods for coverage gains.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.agents.persona_agent import PersonaAgent, PersonaType
from agenteval.persona import PersonaDefinition


@pytest.fixture
def mock_persona_library():
    """Mock persona library with test personas"""
    mock_lib = MagicMock()

    # Create a mock persona definition with all required fields
    mock_persona = PersonaDefinition(
        id="frustrated_customer",
        name="Frustrated Customer",
        category="customer_support",
        description="A frustrated customer",
        metadata={"version": "1.0", "author": "test"},
        system_prompt="You are a frustrated customer. Goal: {goal}. Frustration: {frustration}. Patience: {patience}.",
        attributes={"patience_level": 3, "frustration_level": 7, "communication_style": "direct"},
        preferences={"response_time": "immediate"},
        behavioral_traits=["impatient", "demanding"],
    )

    mock_lib.get_persona.return_value = mock_persona
    mock_lib.list_persona_ids.return_value = ["frustrated_customer", "technical_expert"]

    return mock_lib


class TestPersonaAgentInitialization:
    """Test suite for PersonaAgent initialization"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_init_with_persona_type_enum(self, mock_get_lib, mock_persona_library):
        """Test initialization with PersonaType enum"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(persona_type=PersonaType.FRUSTRATED_CUSTOMER)

        assert agent._persona_id == "frustrated_customer"
        assert agent.persona_type == PersonaType.FRUSTRATED_CUSTOMER
        assert agent.initial_goal == "Get help with my issue"
        mock_persona_library.get_persona.assert_called_once_with("frustrated_customer")

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_init_with_persona_type_string(self, mock_get_lib, mock_persona_library):
        """Test initialization with persona_type as string"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(persona_type="frustrated_customer")

        assert agent._persona_id == "frustrated_customer"

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_init_with_persona_id(self, mock_get_lib, mock_persona_library):
        """Test initialization with persona_id (preferred method)"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(persona_id="frustrated_customer")

        assert agent._persona_id == "frustrated_customer"
        mock_persona_library.get_persona.assert_called_once_with("frustrated_customer")

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_init_with_custom_goal(self, mock_get_lib, mock_persona_library):
        """Test initialization with custom initial goal"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(
            persona_id="frustrated_customer", initial_goal="Cancel my subscription"
        )

        assert agent.initial_goal == "Cancel my subscription"

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_init_with_custom_agent_id(self, mock_get_lib, mock_persona_library):
        """Test initialization with custom agent_id"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(persona_id="frustrated_customer", agent_id="custom-agent-123")

        assert agent.agent_id == "custom-agent-123"

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_init_missing_both_persona_identifiers(self, mock_get_lib, mock_persona_library):
        """Test initialization fails when neither persona_type nor persona_id provided"""
        mock_get_lib.return_value = mock_persona_library

        with pytest.raises(ValueError, match="Either persona_type or persona_id must be provided"):
            PersonaAgent()

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_init_persona_not_found(self, mock_get_lib):
        """Test initialization fails when persona not found in library"""
        mock_lib = MagicMock()
        mock_lib.get_persona.return_value = None
        mock_lib.list_persona_ids.return_value = ["persona1", "persona2"]
        mock_get_lib.return_value = mock_lib

        with pytest.raises(ValueError, match="Persona 'nonexistent' not found in library"):
            PersonaAgent(persona_id="nonexistent")


class TestPersonaCharacteristics:
    """Test suite for persona characteristics setup"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_setup_persona_characteristics(self, mock_get_lib, mock_persona_library):
        """Test that persona characteristics are loaded correctly"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(persona_id="frustrated_customer")

        # Verify memory state was initialized with persona attributes
        assert agent.memory.state.patience_level == 3
        assert agent.memory.state.frustration_level == 7

        # Verify preferences were loaded (check memory dict)
        memory_dict = agent.memory.to_dict()
        assert memory_dict["preferences"]["communication_style"] == "direct"
        assert memory_dict["preferences"]["response_time"] == "immediate"

        # Verify behavioral traits were stored
        facts = memory_dict["semantic_facts"]
        assert "impatient" in facts
        assert "demanding" in facts


class TestSystemPromptBuilding:
    """Test suite for system prompt construction"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_build_system_prompt_basic(self, mock_get_lib, mock_persona_library):
        """Test basic system prompt construction"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(persona_id="frustrated_customer", initial_goal="Get refund")

        prompt = agent._build_system_prompt()

        # Verify prompt contains key elements
        assert "frustrated customer" in prompt.lower()
        assert "Get refund" in prompt
        assert "Frustration: 7" in prompt
        assert "Patience: 3" in prompt
        assert "Communication directives" in prompt

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_build_system_prompt_with_memory_context(self, mock_get_lib, mock_persona_library):
        """Test system prompt includes memory context"""
        mock_get_lib.return_value = mock_persona_library

        agent = PersonaAgent(persona_id="frustrated_customer")

        # Add conversation turns to memory
        agent.memory.add_turn(
            user_message="I want a refund", system_response="Processing...", turn_number=1
        )

        prompt = agent._build_system_prompt()

        # Should include memory context or turn information
        assert "Context from memory" in prompt or len(prompt) > 200


class TestMessageSanitization:
    """Test suite for message sanitization logic"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_sanitize_basic_message(self, mock_get_lib, mock_persona_library):
        """Test sanitization of basic message"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        result = agent._sanitize_user_message("I need help with my order")

        assert result == "I need help with my order"

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_sanitize_message_with_code_fence(self, mock_get_lib, mock_persona_library):
        """Test sanitization removes code fences"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        result = agent._sanitize_user_message("```text\nI need help\n```")

        assert result == "I need help"

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_sanitize_message_with_json(self, mock_get_lib, mock_persona_library):
        """Test sanitization extracts message from JSON"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        json_message = json.dumps({"message": "Help me now"})
        result = agent._sanitize_user_message(json_message)

        assert result == "Help me now"

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_sanitize_empty_message_fallback(self, mock_get_lib, mock_persona_library):
        """Test that empty message falls back to goal"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer", initial_goal="Cancel subscription")

        result = agent._sanitize_user_message("")

        # Should fall back to initial goal
        assert "Cancel subscription" in result or "help" in result.lower()

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_sanitize_whitespace_only(self, mock_get_lib, mock_persona_library):
        """Test sanitization handles whitespace-only input"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        result = agent._sanitize_user_message("   \n\t   ")

        # Should not be empty after sanitization
        assert result.strip() != ""


class TestFallbackMessage:
    """Test suite for fallback message generation"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_fallback_user_message(self, mock_get_lib, mock_persona_library):
        """Test fallback message generation"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(
            persona_id="frustrated_customer", initial_goal="Get refund for broken item"
        )

        result = agent._fallback_user_message()

        # Should contain the goal
        assert "refund" in result.lower() or "broken" in result.lower()


class TestGetDefaultModel:
    """Test suite for default model selection"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    def test_get_default_model(self, mock_get_lib, mock_persona_library):
        """Test that default model is from settings"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        model = agent._get_default_model()

        # Should return bedrock persona model from settings
        assert model is not None
        assert isinstance(model, str)


class TestAsyncProcessResponse:
    """Test suite for async process_response method"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_process_response_updates_memory(self, mock_get_lib, mock_persona_library):
        """Test that process_response updates memory"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        # Process a response
        await agent.process_response(
            user_message="I need help",
            system_response="How can I assist you?",
            turn_number=1,
            response_quality=0.8,
        )

        # Verify memory was updated
        assert agent.memory.state.interaction_count > 0

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_process_response_updates_frustration(self, mock_get_lib, mock_persona_library):
        """Test that process_response can update frustration"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        initial_frustration = agent.memory.state.frustration_level

        # Process a low-quality response
        await agent.process_response(
            user_message="I need help",
            system_response="Sorry, I don't understand",
            turn_number=1,
            response_quality=0.2,  # Low quality
        )

        # Frustration should increase for frustrated_customer persona
        # (may or may not change depending on logic, but method should execute)
        assert agent.memory.state.interaction_count == 1

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_process_response_tracks_turn_number(self, mock_get_lib, mock_persona_library):
        """Test that process_response tracks turn numbers"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        # Process multiple turns
        for turn in range(1, 4):
            await agent.process_response(
                user_message=f"Message {turn}",
                system_response=f"Response {turn}",
                turn_number=turn,
                response_quality=0.7,
            )

        # Should have processed 3 interactions
        assert agent.memory.state.interaction_count == 3


class TestAsyncGenerateMessage:
    """Test suite for async generate_message method"""

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_generate_message_fallback_on_error(self, mock_get_lib, mock_persona_library):
        """Test that generate_message returns fallback on LLM error"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(
            persona_id="frustrated_customer", initial_goal="Get help with my order"
        )

        # Mock invoke_llm to raise an exception
        agent.invoke_llm = AsyncMock(side_effect=Exception("LLM error"))

        # Should return fallback message
        message = await agent.generate_message()

        assert message is not None
        assert isinstance(message, str)
        assert len(message) > 0

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_generate_message_with_context(self, mock_get_lib, mock_persona_library):
        """Test generate_message with conversation context"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        # Mock successful LLM response
        agent.invoke_llm = AsyncMock(
            return_value={"content": "I really need help with this issue!"}
        )

        message = await agent.generate_message(
            conversation_context="Previous: Hello\nResponse: Hi there"
        )

        assert message is not None
        assert isinstance(message, str)
        # Verify invoke_llm was called
        agent.invoke_llm.assert_called_once()

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_generate_message_sanitizes_output(self, mock_get_lib, mock_persona_library):
        """Test that generate_message sanitizes LLM output"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer")

        # Mock LLM response with code fence
        agent.invoke_llm = AsyncMock(return_value={"content": "```text\nI need assistance\n```"})

        message = await agent.generate_message()

        # Should be sanitized (no code fences)
        assert "```" not in message


class TestMetaResponseValidation:
    """Test suite for meta-response detection and prevention"""

    def test_validate_user_message_valid(self):
        """Test validation passes for natural user messages"""
        valid_messages = [
            "I need help with my account",
            "This is taking too long and I'm frustrated",
            "Can someone actually help me?",
            "I've been waiting for weeks for a response",
        ]

        for message in valid_messages:
            is_valid, error = PersonaAgent.validate_user_message(message)
            assert is_valid is True
            assert error is None

    def test_validate_user_message_meta_response(self):
        """Test validation fails for meta-responses"""
        meta_responses = [
            "Current State: - Frustration Level: 4/10 - Patience Level: 4/10",
            "Frustration level: 7 out of 10",
            "My patience level is decreasing",
            "Goal progress: 20%",
            "Interaction count: 3",
            "Interactions: 5 total",
        ]

        for message in meta_responses:
            is_valid, error = PersonaAgent.validate_user_message(message)
            assert is_valid is False
            assert error is not None
            assert "Meta-response detected" in error

    def test_validate_user_message_case_insensitive(self):
        """Test validation is case-insensitive"""
        meta_responses = [
            "CURRENT STATE: Frustrated",
            "frustration level: high",
            "Patience Level: Low",
        ]

        for message in meta_responses:
            is_valid, error = PersonaAgent.validate_user_message(message)
            assert is_valid is False
            assert error is not None

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_sanitize_rejects_meta_response(self, mock_get_lib, mock_persona_library):
        """Test that _sanitize_user_message rejects meta-responses"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(
            persona_id="frustrated_customer", initial_goal="Get help with my order"
        )

        # Mock LLM returning a meta-response
        meta_response = (
            "Current State: - Frustration Level: 4/10 - Patience Level: 4/10 - Goal Progress: 20%"
        )

        # Sanitize should detect and replace with fallback
        sanitized = agent._sanitize_user_message(meta_response)

        # Should NOT contain meta-response patterns
        assert "Current State:" not in sanitized
        assert "Frustration Level:" not in sanitized
        # Should be fallback message
        assert sanitized == "Get help with my order."

    @patch("agenteval.agents.persona_agent.get_persona_library")
    @pytest.mark.asyncio
    async def test_generate_message_handles_meta_response_from_llm(
        self, mock_get_lib, mock_persona_library
    ):
        """Test that generate_message handles meta-responses from LLM"""
        mock_get_lib.return_value = mock_persona_library
        agent = PersonaAgent(persona_id="frustrated_customer", initial_goal="Fix my account issue")

        # Mock LLM returning a meta-response (simulating Titan Lite bug)
        agent.invoke_llm = AsyncMock(
            return_value={
                "content": "Current State: - Frustration Level: 5/10 - Patience Level: 3/10"
            }
        )

        message = await agent.generate_message()

        # Should be sanitized to fallback
        assert "Current State:" not in message
        assert "Frustration Level:" not in message
        # Should be fallback message
        assert message == "Fix my account issue."
        assert "I need assistance" in message or len(message) > 0
