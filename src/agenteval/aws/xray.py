"""
AWS X-Ray Client for Trace Retrieval

Critical for SECRET SAUCE - trace-based root cause analysis.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from agenteval.config import settings

logger = logging.getLogger(__name__)


class XRayClient:
    """
    Async client for AWS X-Ray trace retrieval

    Supports dependency injection of configuration parameters.
    Falls back to global settings if not provided.
    """

    def __init__(
        self,
        region: str | None = None,
        profile: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        """
        Initialize X-Ray client

        Args:
            region: AWS region (defaults to settings.aws.region)
            profile: AWS profile name (defaults to settings.aws.profile)
            access_key_id: AWS access key ID (defaults to settings.aws.access_key_id)
            secret_access_key: AWS secret access key (defaults to settings.aws.secret_access_key)
        """
        # Use provided config or fall back to settings (backward compatibility)
        self.region = region or settings.aws.region
        self.profile = profile or settings.aws.profile
        self.access_key_id = access_key_id or settings.aws.access_key_id
        self.secret_access_key = secret_access_key or settings.aws.secret_access_key

        self.session = aioboto3.Session(
            region_name=self.region,
            profile_name=self.profile,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        self._client: Any | None = None
        self._connected: bool = False
        self._trace_cache: dict[str, Any] = {}  # Simple in-memory cache
        self._trace_id_pattern = re.compile(r"^1-[0-9a-fA-F]{8}-[0-9a-fA-F]{24}$")

        logger.debug(
            "XRayClient initialized",
            extra={"region": self.region, "profile": self.profile or "default"},
        )

    async def connect(self) -> None:
        """Initialize X-Ray client connection"""
        if not self._connected:
            self._client = await self.session.client("xray").__aenter__()
            self._connected = True
            logger.info("X-Ray client connected")

    async def close(self) -> None:
        """Close X-Ray client connection"""
        if self._connected and self._client:
            await self._client.__aexit__(None, None, None)
            self._connected = False
            logger.info("X-Ray client closed")

    async def __aenter__(self) -> "XRayClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _ensure_connected(self) -> None:
        """Ensure client is connected before operations"""
        if not self._connected or not self._client:
            raise RuntimeError("X-Ray client not connected. Call connect() first.")

    def _is_valid_trace_id(self, trace_id: str) -> bool:
        """Return True if the provided string matches X-Ray trace ID format."""
        return bool(trace_id and self._trace_id_pattern.match(trace_id))

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """
        Retrieve a single trace by ID

        Args:
            trace_id: X-Ray trace ID

        Returns:
            Trace document or None if not found
        """
        self._ensure_connected()

        if not self._is_valid_trace_id(trace_id):
            logger.warning(
                "Skipping invalid X-Ray trace id: %s",
                trace_id,
            )
            return None

        # Check cache first
        if trace_id in self._trace_cache:
            logger.debug(f"Trace {trace_id} found in cache")
            return self._trace_cache[trace_id]

        try:
            response = await self._client.batch_get_traces(TraceIds=[trace_id])
            traces = response.get("Traces", [])

            if traces:
                trace = traces[0]
                # Cache the trace
                self._trace_cache[trace_id] = trace
                logger.info(f"Retrieved trace {trace_id} from X-Ray")
                return trace
            else:
                logger.warning(f"Trace {trace_id} not found in X-Ray")
                return None

        except ClientError as e:
            logger.error(f"Failed to retrieve trace: {e}")
            raise

    async def get_trace_summaries(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        filter_expression: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get trace summaries within a time range

        Args:
            start_time: Start of time range (defaults to 1 hour ago)
            end_time: End of time range (defaults to now)
            filter_expression: X-Ray filter expression

        Returns:
            List of trace summaries
        """
        self._ensure_connected()

        if not start_time:
            start_time = datetime.utcnow() - timedelta(hours=1)
        if not end_time:
            end_time = datetime.utcnow()

        kwargs = {"StartTime": start_time, "EndTime": end_time}

        if filter_expression:
            kwargs["FilterExpression"] = filter_expression

        try:
            response = await self._client.get_trace_summaries(**kwargs)
            summaries = response.get("TraceSummaries", [])
            logger.info(f"Retrieved {len(summaries)} trace summaries")
            return summaries

        except ClientError as e:
            logger.error(f"Failed to get trace summaries: {e}")
            raise

    async def batch_get_traces(self, trace_ids: list[str]) -> list[dict[str, Any]]:
        """
        Retrieve multiple traces by IDs

        Args:
            trace_ids: List of X-Ray trace IDs

        Returns:
            List of trace documents
        """
        self._ensure_connected()

        # Check cache first
        cached_traces = []
        uncached_ids = []

        for trace_id in trace_ids:
            if not self._is_valid_trace_id(trace_id):
                logger.warning(
                    "Skipping invalid X-Ray trace id in batch request: %s",
                    trace_id,
                )
                continue
            if trace_id in self._trace_cache:
                cached_traces.append(self._trace_cache[trace_id])
            else:
                uncached_ids.append(trace_id)

        if not uncached_ids:
            logger.debug(f"All {len(trace_ids)} traces found in cache")
            return cached_traces

        try:
            response = await self._client.batch_get_traces(TraceIds=uncached_ids)
            new_traces = response.get("Traces", [])

            # Cache new traces
            for trace in new_traces:
                trace_id = trace["Id"]
                self._trace_cache[trace_id] = trace

            all_traces = cached_traces + new_traces
            logger.info(f"Retrieved {len(all_traces)} traces ({len(cached_traces)} from cache)")
            return all_traces

        except ClientError as e:
            logger.error(f"Failed to batch get traces: {e}")
            raise


async def get_xray_client() -> XRayClient:
    """Dependency injection for X-Ray client"""
    return XRayClient()
