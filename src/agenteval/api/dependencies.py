"""
Common FastAPI dependencies for authentication and request handling.
"""

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from agenteval.config import settings

logger = logging.getLogger(__name__)

# API Key header extraction (auto_error=False for optional checks)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_optional_api_key(api_key: str | None = Depends(api_key_header)) -> str | None:
    """
    Extract API key from headers without enforcing it.

    Returns:
        API key if present, None otherwise
    """
    return api_key


async def verify_api_key(api_key: str | None) -> bool:
    """
    Verify if provided API key matches configured key.

    Args:
        api_key: API key to verify

    Returns:
        True if valid, False otherwise
    """
    if not settings.app.api_key:
        # No API key configured - reject if auth is enabled
        if settings.app.api_key_enabled:
            logger.error("API key authentication enabled but no key configured!")
            return False
        # Auth disabled, allow
        return True

    return api_key == settings.app.api_key


async def require_api_key(
    api_key: str | None = Depends(api_key_header), request: Request = None
) -> str:
    """
    Require valid API key for request authentication.

    This dependency enforces API key authentication when enabled in settings.
    In production, API keys are always required (enforced by config validation).

    Args:
        api_key: API key from header
        request: FastAPI request object

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is invalid or missing
    """
    # Check if API key authentication is enabled
    if not settings.app.api_key_enabled:
        logger.warning(
            "API key authentication is disabled - allowing unauthenticated request. "
            "This should NEVER happen in production!"
        )
        return "disabled"

    # Get expected API key
    expected_key = settings.app.api_key

    if not expected_key:
        # This should never happen in production due to config validation
        logger.critical(
            "API key authentication enabled but no key configured! This is a configuration error."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API key authentication misconfigured",
        )

    # Check if API key was provided
    if not api_key:
        logger.warning(
            f"API request without API key from {request.client.host if request else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Verify API key matches
    if api_key != expected_key:
        logger.warning(
            f"Invalid API key attempt from {request.client.host if request else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    logger.debug(f"Authenticated request from {request.client.host if request else 'unknown'}")
    return api_key


async def require_admin_api_key(
    api_key: str = Depends(require_api_key), request: Request = None
) -> str:
    """
    Require API key for admin operations.

    This is a stricter version of require_api_key that's intended for
    admin-only operations (e.g., deleting campaigns, accessing sensitive data).

    In the future, this can be enhanced to check for admin-specific keys
    or role-based access control.

    Args:
        api_key: API key from require_api_key dependency
        request: FastAPI request object

    Returns:
        Validated API key

    Raises:
        HTTPException: If not authorized for admin operations
    """
    # For now, any valid API key grants admin access
    # TODO: Implement role-based access control (RBAC)
    logger.info(f"Admin operation requested from {request.client.host if request else 'unknown'}")
    return api_key


async def optional_api_key(api_key: str | None = Depends(api_key_header)) -> str | None:
    """
    Optional API key dependency for endpoints that work with or without auth.

    Verifies the key if provided, but doesn't require it.
    Useful for public endpoints that offer enhanced features with authentication.

    Args:
        api_key: API key from header (optional)

    Returns:
        Validated API key if provided and valid, None otherwise

    Raises:
        HTTPException: If API key is provided but invalid
    """
    if not api_key:
        return None

    # If a key is provided, it must be valid
    if not await verify_api_key(api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    return api_key


def get_security_status() -> dict:
    """
    Get current security configuration status for debugging.

    Returns:
        Dictionary with security status
    """
    return {
        "environment": settings.app.environment,
        "api_key_enabled": settings.app.api_key_enabled,
        "api_key_configured": settings.app.api_key is not None,
        "is_production": settings.is_production,
        "https_required": settings.app.require_https_in_production,
        "base_url": settings.app.api_base_url,
    }
