"""
Authentication and Authorization for AgentEval API

Provides API key authentication for admin routes.
"""

import logging

from fastapi import Header, HTTPException, status
from fastapi.security import APIKeyHeader

from agenteval.config import settings

logger = logging.getLogger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """
    Verify API key from request header

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The verified API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not settings.app.api_key:
        # If no API key is configured, authentication is disabled
        logger.warning(
            "API authentication disabled: No API key configured. "
            "Set API_KEY environment variable to enable authentication."
        )
        return "no-auth-configured"

    if not x_api_key:
        logger.warning("API request missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if x_api_key != settings.app.api_key:
        logger.warning(f"Invalid API key attempted: {x_api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return x_api_key


async def verify_api_key_optional(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> str | None:
    """
    Optionally verify API key (doesn't raise exception if missing)

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        The API key if present and valid, None otherwise
    """
    if not settings.app.api_key:
        # Authentication disabled
        return None

    if not x_api_key:
        return None

    if x_api_key != settings.app.api_key:
        return None

    return x_api_key
