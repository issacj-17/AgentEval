"""
Unit tests for BedrockClient

Tests Bedrock client initialization, model invocation, and error handling.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.aws.bedrock import BedrockClient, get_bedrock_client


class TestBedrockClientInitialization:
    """Test BedrockClient initialization"""

    @patch("agenteval.aws.bedrock.settings")
    def test_init_creates_session(self, mock_settings):
        """Test that initialization creates aioboto3 session"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        assert client.session is not None
        assert client._client is None
        assert isinstance(client._model_profiles, dict)
        assert isinstance(client._fallback_models, dict)

    @patch("agenteval.aws.bedrock.settings")
    def test_init_stores_model_profiles(self, mock_settings):
        """Test that initialization stores model profile mappings"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = "arn:aws:bedrock:profile1"
        mock_settings.aws.bedrock_redteam_profile_arn = "arn:aws:bedrock:profile2"
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = "claude-2"
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        assert "claude-3" in client._model_profiles
        assert (
            client._model_profiles["claude-3"] == "arn:aws:bedrock:profile2"
        )  # redteam model is also claude-3
        assert "claude-3" in client._fallback_models


class TestBedrockClientContextManager:
    """Test BedrockClient async context manager"""

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_context_manager_creates_client(self, mock_settings):
        """Test that context manager creates bedrock-runtime client"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        # Mock the session.client context manager
        mock_bedrock_client = AsyncMock()
        mock_bedrock_client.__aexit__ = AsyncMock(return_value=None)

        mock_client_ctx = MagicMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_bedrock_client)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=None)
        client.session.client = MagicMock(return_value=mock_client_ctx)

        async with client as bedrock:
            assert bedrock._client == mock_bedrock_client
            assert bedrock is client

        # After exiting, client should be cleared
        # (The _client.__aexit__ is called, cleaning up the aioboto3 client)


class TestInvokeClaude:
    """Test invoke_claude method"""

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_claude_success(self, mock_settings):
        """Test successful Claude invocation"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3-sonnet"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        # Mock the bedrock client
        mock_response_body = MagicMock()
        mock_response_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "content": [{"text": "Hello from Claude"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                    "model": "claude-3-sonnet",
                }
            ).encode()
        )

        mock_bedrock_client = AsyncMock()
        mock_bedrock_client.invoke_model = AsyncMock(return_value={"body": mock_response_body})
        client._client = mock_bedrock_client

        result = await client.invoke_claude(
            prompt="Hello", model_id="claude-3-sonnet", max_tokens=100, temperature=0.7
        )

        assert result["content"] == "Hello from Claude"
        assert result["stop_reason"] == "end_turn"
        assert result["usage"]["input_tokens"] == 10
        assert result["model_id"] == "claude-3-sonnet"

        # Verify invoke_model was called with correct parameters
        mock_bedrock_client.invoke_model.assert_called_once()
        call_kwargs = mock_bedrock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "claude-3-sonnet"
        body = json.loads(call_kwargs["body"])
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == "Hello"
        assert body["max_tokens"] == 100

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_claude_with_system_prompt(self, mock_settings):
        """Test Claude invocation with system prompt"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3-sonnet"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        mock_response_body = MagicMock()
        mock_response_body.read = AsyncMock(
            return_value=json.dumps(
                {"content": [{"text": "Response"}], "stop_reason": "end_turn", "usage": {}}
            ).encode()
        )

        mock_bedrock_client = AsyncMock()
        mock_bedrock_client.invoke_model = AsyncMock(return_value={"body": mock_response_body})
        client._client = mock_bedrock_client

        await client.invoke_claude(prompt="Hello", system_prompt="You are a helpful assistant")

        call_kwargs = mock_bedrock_client.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])
        assert "system" in body
        assert body["system"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_claude_uses_profile_arn(self, mock_settings):
        """Test that Claude invocation uses profile ARN when available"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3-sonnet"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = "arn:aws:bedrock:profile123"
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        mock_response_body = MagicMock()
        mock_response_body.read = AsyncMock(
            return_value=json.dumps(
                {"content": [{"text": "Response"}], "stop_reason": "end_turn", "usage": {}}
            ).encode()
        )

        mock_bedrock_client = AsyncMock()
        mock_bedrock_client.invoke_model = AsyncMock(return_value={"body": mock_response_body})
        client._client = mock_bedrock_client

        await client.invoke_claude(prompt="Hello", model_id="claude-3-sonnet")

        call_kwargs = mock_bedrock_client.invoke_model.call_args[1]
        assert call_kwargs["modelId"] == "arn:aws:bedrock:profile123"


class TestInvokeNova:
    """Test invoke_nova method"""

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_nova_success(self, mock_settings):
        """Test successful Nova invocation"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-pro"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        mock_response_body = MagicMock()
        mock_response_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "output": {"message": {"content": [{"text": "Hello from Nova"}]}},
                    "stopReason": "end_turn",
                    "usage": {"inputTokens": 10, "outputTokens": 5},
                }
            ).encode()
        )

        mock_bedrock_client = AsyncMock()
        mock_bedrock_client.invoke_model = AsyncMock(return_value={"body": mock_response_body})
        client._client = mock_bedrock_client

        result = await client.invoke_nova(prompt="Hello", model_id="nova-pro", max_tokens=100)

        assert result["content"] == "Hello from Nova"
        assert result["stop_reason"] == "end_turn"
        assert result["model_id"] == "nova-pro"

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_nova_with_system_prompt(self, mock_settings):
        """Test Nova invocation with system prompt"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-pro"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        mock_response_body = MagicMock()
        mock_response_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "output": {"message": {"content": [{"text": "Response"}]}},
                    "stopReason": "end_turn",
                    "usage": {},
                }
            ).encode()
        )

        mock_bedrock_client = AsyncMock()
        mock_bedrock_client.invoke_model = AsyncMock(return_value={"body": mock_response_body})
        client._client = mock_bedrock_client

        await client.invoke_nova(
            prompt="Hello", system_prompt="You are helpful", model_id="nova-pro"
        )

        call_kwargs = mock_bedrock_client.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])
        # Nova includes system prompt as first message with role="system"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][0]["content"][0]["text"] == "You are helpful"
        assert body["messages"][1]["role"] == "user"


class TestInvokeTitan:
    """Test invoke_titan method"""

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_titan_success(self, mock_settings):
        """Test successful Titan invocation"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "titan-text"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        mock_response_body = MagicMock()
        mock_response_body.read = AsyncMock(
            return_value=json.dumps(
                {
                    "results": [
                        {
                            "outputText": "Hello from Titan",
                            "completionReason": "FINISH",
                            "tokenCount": {"inputTokens": 10, "outputTokens": 5},
                        }
                    ]
                }
            ).encode()
        )

        mock_bedrock_client = AsyncMock()
        mock_bedrock_client.invoke_model = AsyncMock(return_value={"body": mock_response_body})
        client._client = mock_bedrock_client

        result = await client.invoke_titan(prompt="Hello", model_id="titan-text")

        assert result["content"] == "Hello from Titan"
        assert result["stop_reason"] == "FINISH"
        assert result["model_id"] == "titan-text"


class TestInvokeModel:
    """Test invoke_model universal dispatcher"""

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_model_routes_to_claude(self, mock_settings):
        """Test that invoke_model routes to Claude for claude models"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()
        client.invoke_claude = AsyncMock(return_value={"content": "test"})

        await client.invoke_model(prompt="Hello", model_id="claude-3-sonnet")

        client.invoke_claude.assert_called_once_with("Hello", "claude-3-sonnet")

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_model_routes_to_nova(self, mock_settings):
        """Test that invoke_model routes to Nova for nova models"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()
        client.invoke_nova = AsyncMock(return_value={"content": "test"})

        await client.invoke_model(prompt="Hello", model_id="nova-pro")

        client.invoke_nova.assert_called_once_with("Hello", "nova-pro")

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_model_routes_to_titan(self, mock_settings):
        """Test that invoke_model routes to Titan for titan models"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()
        client.invoke_titan = AsyncMock(return_value={"content": "test"})

        await client.invoke_model(prompt="Hello", model_id="titan-text-express")

        client.invoke_titan.assert_called_once_with("Hello", "titan-text-express")

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_invoke_model_raises_for_unsupported_model(self, mock_settings):
        """Test that invoke_model raises ValueError for unsupported models"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        with pytest.raises(ValueError, match="Unsupported model"):
            await client.invoke_model(prompt="Hello", model_id="unknown-model")


class TestResolveProfile:
    """Test _resolve_profile method"""

    @patch("agenteval.aws.bedrock.settings")
    def test_resolve_profile_returns_arn(self, mock_settings):
        """Test that _resolve_profile returns configured ARN"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3-sonnet"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = "arn:aws:bedrock:profile123"
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        result = client._resolve_profile("claude-3-sonnet")

        assert result == "arn:aws:bedrock:profile123"

    @patch("agenteval.aws.bedrock.settings")
    def test_resolve_profile_returns_none_when_not_configured(self, mock_settings):
        """Test that _resolve_profile returns None when no ARN configured"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = BedrockClient()

        result = client._resolve_profile("unknown-model")

        assert result is None


class TestGetBedrockClient:
    """Test get_bedrock_client factory function"""

    @pytest.mark.asyncio
    @patch("agenteval.aws.bedrock.settings")
    async def test_get_bedrock_client_returns_instance(self, mock_settings):
        """Test that get_bedrock_client returns BedrockClient instance"""
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.profile = None
        mock_settings.aws.access_key_id = None
        mock_settings.aws.secret_access_key = None
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"
        mock_settings.aws.bedrock_persona_profile_arn = None
        mock_settings.aws.bedrock_redteam_profile_arn = None
        mock_settings.aws.bedrock_judge_profile_arn = None
        mock_settings.aws.bedrock_persona_fallback_model = None
        mock_settings.aws.bedrock_redteam_fallback_model = None
        mock_settings.aws.bedrock_judge_fallback_model = None

        client = await get_bedrock_client()

        assert isinstance(client, BedrockClient)
