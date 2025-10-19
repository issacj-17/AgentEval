"""
FastAPI Lifespan Management

Handles application startup and shutdown, including DI container lifecycle.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from agenteval.container import get_container
from agenteval.observability.tracer import cleanup_tracing, setup_tracing

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager

    Handles startup and shutdown tasks:
    - Initialize DI container and connect clients
    - Setup distributed tracing
    - Cleanup resources on shutdown

    Usage:
        app = FastAPI(lifespan=lifespan)

    Args:
        app: FastAPI application instance

    Yields:
        None (application runs during yield)
    """
    # ========================================================================
    # Startup
    # ========================================================================
    logger.info("=" * 60)
    logger.info("AgentEval API starting up...")
    logger.info("=" * 60)

    try:
        # Initialize distributed tracing
        logger.info("Setting up distributed tracing...")
        setup_tracing()
        logger.info("✓ Distributed tracing configured")

        # Get container and connect all clients
        logger.info("Initializing DI container...")
        container = get_container()

        # Pre-create commonly used clients to establish connections early
        logger.info("Pre-initializing AWS clients...")
        container.dynamodb()
        container.s3()
        container.xray()
        container.eventbridge()
        logger.info("✓ AWS clients created")

        # Connect all clients
        logger.info("Connecting to AWS services...")
        await container.connect()
        logger.info("✓ All AWS clients connected")

        # Store container in app state for access in routes
        app.state.container = container

        logger.info("=" * 60)
        logger.info("✓ AgentEval API startup complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.critical(f"Failed to start application: {e}", exc_info=True)
        raise

    # ========================================================================
    # Application Running (yield point)
    # ========================================================================
    yield

    # ========================================================================
    # Shutdown
    # ========================================================================
    logger.info("=" * 60)
    logger.info("AgentEval API shutting down...")
    logger.info("=" * 60)

    try:
        # Close DI container and all clients
        logger.info("Closing DI container...")
        container = get_container()
        await container.close()
        logger.info("✓ DI container closed")

        # Cleanup tracing
        logger.info("Cleaning up distributed tracing...")
        cleanup_tracing()
        logger.info("✓ Distributed tracing cleaned up")

        logger.info("=" * 60)
        logger.info("✓ AgentEval API shutdown complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


def get_container_from_app(app: FastAPI):
    """
    Get container from FastAPI app state

    This allows routes to access the container if needed,
    though they should prefer using FastAPI Depends.

    Args:
        app: FastAPI application instance

    Returns:
        Container instance from app state
    """
    if not hasattr(app.state, "container"):
        raise RuntimeError(
            "Container not initialized. Ensure app is using lifespan context manager."
        )
    return app.state.container
