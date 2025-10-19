"""
Unit tests for API Authentication

Tests API key verification and authentication enforcement.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from agenteval.api.auth import verify_api_key, verify_api_key_optional


class TestAPIKeyVerification:
    """Test API key verification"""

    @pytest.mark.asyncio
    async def test_verify_api_key_with_valid_key(self):
        """Test that valid API key is accepted"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = "test-api-key-123"

            result = await verify_api_key(x_api_key="test-api-key-123")
            assert result == "test-api-key-123"

    @pytest.mark.asyncio
    async def test_verify_api_key_with_invalid_key(self):
        """Test that invalid API key is rejected"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = "test-api-key-123"

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(x_api_key="wrong-key")

            assert exc_info.value.status_code == 403
            assert "Invalid API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_verify_api_key_with_missing_key(self):
        """Test that missing API key is rejected"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = "test-api-key-123"

            with pytest.raises(HTTPException) as exc_info:
                await verify_api_key(x_api_key=None)

            assert exc_info.value.status_code == 401
            assert "Missing API key" in exc_info.value.detail
            assert "WWW-Authenticate" in exc_info.value.headers

    @pytest.mark.asyncio
    async def test_verify_api_key_when_auth_disabled(self):
        """Test that authentication is skipped when no API key configured"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = None

            # Should not raise even with missing key
            result = await verify_api_key(x_api_key=None)
            assert result == "no-auth-configured"

    @pytest.mark.asyncio
    async def test_verify_api_key_optional_with_valid_key(self):
        """Test optional verification with valid key"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = "test-key"

            result = await verify_api_key_optional(x_api_key="test-key")
            assert result == "test-key"

    @pytest.mark.asyncio
    async def test_verify_api_key_optional_with_invalid_key(self):
        """Test optional verification with invalid key returns None"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = "test-key"

            result = await verify_api_key_optional(x_api_key="wrong-key")
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_optional_with_missing_key(self):
        """Test optional verification with missing key returns None"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = "test-key"

            result = await verify_api_key_optional(x_api_key=None)
            assert result is None

    @pytest.mark.asyncio
    async def test_verify_api_key_optional_when_auth_disabled(self):
        """Test optional verification when auth is disabled"""
        with patch("agenteval.api.auth.settings") as mock_settings:
            mock_settings.app.api_key = None

            result = await verify_api_key_optional(x_api_key=None)
            assert result is None
