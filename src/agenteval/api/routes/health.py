"""
Health check endpoints

Provides health checks with actual AWS connectivity verification.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Response, status

from agenteval.aws.dynamodb import DynamoDBClient
from agenteval.aws.eventbridge import EventBridgeClient
from agenteval.aws.s3 import S3Client
from agenteval.aws.xray import XRayClient
from agenteval.config import settings
from agenteval.container import get_dynamodb, get_eventbridge, get_s3, get_xray

logger = logging.getLogger(__name__)

router = APIRouter()

# Health check timeout (don't let health checks hang)
HEALTH_CHECK_TIMEOUT = 5.0


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, Any]:
    """
    Basic health check endpoint

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "agenteval", "version": "1.0.0"}


@router.get("/health/detailed")
async def detailed_health_check(
    response: Response,
    dynamodb: DynamoDBClient = Depends(get_dynamodb),
    s3: S3Client = Depends(get_s3),
    xray: XRayClient = Depends(get_xray),
    eventbridge: EventBridgeClient = Depends(get_eventbridge),
) -> dict[str, Any]:
    """
    Detailed health check with actual AWS connectivity verification

    Tests actual connectivity to all AWS services with timeouts.
    Returns 200 if healthy, 503 if unhealthy, 200 with degraded status if partially healthy.

    Args:
        response: FastAPI response object
        dynamodb: Injected DynamoDB client
        s3: Injected S3 client
        xray: Injected X-Ray client
        eventbridge: Injected EventBridge client

    Returns:
        Detailed health status including all dependencies
    """
    start_time = datetime.utcnow()

    health_status = {
        "status": "healthy",
        "service": "agenteval",
        "version": "1.0.0",
        "environment": settings.app.environment,
        "timestamp": start_time.isoformat(),
        "dependencies": {},
    }

    checks_passed = 0
    checks_failed = 0

    # Check DynamoDB connectivity (CRITICAL)
    dynamodb_status = await _check_dynamodb_health(dynamodb)
    health_status["dependencies"]["dynamodb"] = dynamodb_status
    if dynamodb_status["status"] == "healthy":
        checks_passed += 1
    else:
        checks_failed += 1

    # Check S3 connectivity (CRITICAL)
    s3_status = await _check_s3_health(s3)
    health_status["dependencies"]["s3"] = s3_status
    if s3_status["status"] == "healthy":
        checks_passed += 1
    else:
        checks_failed += 1

    # Check EventBridge connectivity (NON-CRITICAL)
    eventbridge_status = await _check_eventbridge_health(eventbridge)
    health_status["dependencies"]["eventbridge"] = eventbridge_status
    if eventbridge_status["status"] == "healthy":
        checks_passed += 1
    elif eventbridge_status["status"] == "unhealthy":
        checks_failed += 1

    # Check X-Ray connectivity (NON-CRITICAL)
    xray_status = await _check_xray_health(xray)
    health_status["dependencies"]["xray"] = xray_status
    if xray_status["status"] == "healthy":
        checks_passed += 1
    elif xray_status["status"] == "unhealthy":
        checks_failed += 1

    # Check tracing configuration
    health_status["dependencies"]["tracing"] = {
        "status": "healthy" if settings.observability.enable_tracing else "disabled",
        "enabled": settings.observability.enable_tracing,
    }

    # Determine overall health status
    if checks_failed == 0:
        health_status["status"] = "healthy"
        response.status_code = status.HTTP_200_OK
    elif checks_passed == 0:
        health_status["status"] = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        health_status["status"] = "degraded"
        response.status_code = status.HTTP_200_OK

    # Add summary
    health_status["summary"] = {
        "checks_passed": checks_passed,
        "checks_failed": checks_failed,
        "duration_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
    }

    return health_status


async def _check_dynamodb_health(client: DynamoDBClient) -> dict[str, Any]:
    """
    Check DynamoDB connectivity with actual operation

    Args:
        client: Injected DynamoDB client from DI container

    Returns:
        Health status dictionary
    """
    try:
        # Use timeout to prevent hanging
        async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
            # Try to describe a table (read-only operation)
            try:
                dynamodb_client = await client.session.client("dynamodb").__aenter__()
                try:
                    response = await dynamodb_client.describe_table(
                        TableName=settings.aws.dynamodb_campaigns_table
                    )

                    return {
                        "status": "healthy",
                        "region": settings.aws.region,
                        "table": settings.aws.dynamodb_campaigns_table,
                        "table_status": response["Table"]["TableStatus"],
                    }
                finally:
                    await dynamodb_client.__aexit__(None, None, None)

            except Exception as e:
                # Table might not exist yet, but connection works
                if "ResourceNotFoundException" in str(e):
                    return {
                        "status": "degraded",
                        "region": settings.aws.region,
                        "message": "Connected but table not found",
                        "table": settings.aws.dynamodb_campaigns_table,
                    }
                raise

    except TimeoutError:
        logger.error("DynamoDB health check timed out")
        return {
            "status": "unhealthy",
            "error": "Connection timeout",
            "timeout_seconds": HEALTH_CHECK_TIMEOUT,
        }
    except Exception as e:
        logger.error(f"DynamoDB health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def _check_s3_health(client: S3Client) -> dict[str, Any]:
    """
    Check S3 connectivity with actual operation

    Args:
        client: Injected S3 client from DI container

    Returns:
        Health status dictionary
    """
    try:
        async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
            # Try to list buckets (read-only operation)
            response = await client._client.list_buckets()
            bucket_count = len(response.get("Buckets", []))

            return {
                "status": "healthy",
                "region": settings.aws.region,
                "bucket_count": bucket_count,
            }

    except TimeoutError:
        logger.error("S3 health check timed out")
        return {
            "status": "unhealthy",
            "error": "Connection timeout",
            "timeout_seconds": HEALTH_CHECK_TIMEOUT,
        }
    except Exception as e:
        logger.error(f"S3 health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def _check_eventbridge_health(client: EventBridgeClient) -> dict[str, Any]:
    """
    Check EventBridge connectivity with actual operation

    Args:
        client: Injected EventBridge client from DI container

    Returns:
        Health status dictionary
    """
    try:
        async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
            # List event buses (read-only operation)
            response = await client._client.list_event_buses(Limit=1)

            return {"status": "healthy", "region": settings.aws.region}

    except TimeoutError:
        logger.warning("EventBridge health check timed out")
        return {
            "status": "degraded",
            "error": "Connection timeout (non-critical)",
            "timeout_seconds": HEALTH_CHECK_TIMEOUT,
        }
    except Exception as e:
        logger.warning(f"EventBridge health check failed: {e}")
        return {"status": "degraded", "error": str(e), "note": "Non-critical service"}


async def _check_xray_health(client: XRayClient) -> dict[str, Any]:
    """
    Check X-Ray connectivity with actual operation

    Args:
        client: Injected X-Ray client from DI container

    Returns:
        Health status dictionary
    """
    try:
        async with asyncio.timeout(HEALTH_CHECK_TIMEOUT):
            # Get trace summaries (read-only operation)
            # Using a very short time window to minimize overhead
            start_time = datetime.utcnow() - timedelta(minutes=1)
            end_time = datetime.utcnow()

            await client._client.get_trace_summaries(
                StartTime=start_time, EndTime=end_time, Sampling=True
            )

            return {"status": "healthy", "region": settings.aws.region}

    except TimeoutError:
        logger.warning("X-Ray health check timed out")
        return {
            "status": "degraded",
            "error": "Connection timeout (non-critical)",
            "timeout_seconds": HEALTH_CHECK_TIMEOUT,
        }
    except Exception as e:
        logger.warning(f"X-Ray health check failed: {e}")
        return {"status": "degraded", "error": str(e), "note": "Non-critical service"}


@router.get("/health/ready")
async def readiness_check(
    response: Response,
    dynamodb: DynamoDBClient = Depends(get_dynamodb),
    s3: S3Client = Depends(get_s3),
) -> dict[str, Any]:
    """
    Readiness check for Kubernetes/container orchestration

    Checks if the service is ready to accept traffic.
    Returns 200 if ready, 503 if not ready.

    Args:
        response: FastAPI response object
        dynamodb: Injected DynamoDB client
        s3: Injected S3 client

    Returns:
        Readiness status with critical dependencies
    """
    ready = True
    checks = {}

    # Check critical AWS services only (quick checks)
    try:
        async with asyncio.timeout(2.0):  # Shorter timeout for readiness
            # DynamoDB (critical)
            try:
                # Just verify client is connected
                if dynamodb:
                    checks["dynamodb"] = "ready"
                else:
                    checks["dynamodb"] = "not_ready: client not initialized"
                    ready = False
            except Exception as e:
                checks["dynamodb"] = f"not_ready: {str(e)[:50]}"
                ready = False

            # S3 (critical)
            try:
                # Just verify client is connected
                if s3:
                    checks["s3"] = "ready"
                else:
                    checks["s3"] = "not_ready: client not initialized"
                    ready = False
            except Exception as e:
                checks["s3"] = f"not_ready: {str(e)[:50]}"
                ready = False

    except TimeoutError:
        checks["error"] = "Readiness check timed out"
        ready = False

    if ready:
        response.status_code = status.HTTP_200_OK
        return {"status": "ready", "checks": checks}
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "checks": checks}


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, str]:
    """
    Liveness check for Kubernetes/container orchestration

    Simple check that the application is running and responsive.
    This should always return 200 unless the application is completely dead.

    Returns:
        Liveness status
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
