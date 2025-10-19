"""
Amazon EventBridge Client for Event-Driven Architecture
"""

import json
import logging
from datetime import datetime
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from agenteval.config import settings

logger = logging.getLogger(__name__)


class EventBridgeClient:
    """
    Async client for Amazon EventBridge

    Supports dependency injection of configuration parameters.
    Falls back to global settings if not provided.
    """

    def __init__(
        self,
        region: str | None = None,
        profile: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        bus_name: str | None = None,
    ) -> None:
        """
        Initialize EventBridge client

        Args:
            region: AWS region (defaults to settings.aws.region)
            profile: AWS profile name (defaults to settings.aws.profile)
            access_key_id: AWS access key ID (defaults to settings.aws.access_key_id)
            secret_access_key: AWS secret access key (defaults to settings.aws.secret_access_key)
            bus_name: EventBridge bus name (defaults to settings.aws.eventbridge_bus_name)
        """
        # Use provided config or fall back to settings (backward compatibility)
        self.region = region or settings.aws.region
        self.profile = profile or settings.aws.profile
        self.access_key_id = access_key_id or settings.aws.access_key_id
        self.secret_access_key = secret_access_key or settings.aws.secret_access_key
        self.bus_name = bus_name or settings.aws.eventbridge_bus_name

        self.session = aioboto3.Session(
            region_name=self.region,
            profile_name=self.profile,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        self._client: Any | None = None
        self._connected: bool = False

        logger.debug(
            "EventBridgeClient initialized",
            extra={"region": self.region, "bus_name": self.bus_name},
        )

    async def connect(self) -> None:
        """Initialize EventBridge client connection"""
        if not self._connected:
            self._client = await self.session.client("events").__aenter__()
            self._connected = True
            logger.info("EventBridge client connected")

    async def close(self) -> None:
        """Close EventBridge client connection"""
        if self._connected and self._client:
            await self._client.__aexit__(None, None, None)
            self._connected = False
            logger.info("EventBridge client closed")

    async def __aenter__(self) -> "EventBridgeClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _ensure_connected(self) -> None:
        """Ensure client is connected before operations"""
        if not self._connected or not self._client:
            raise RuntimeError("EventBridge client not connected. Call connect() first.")

    async def publish_event(
        self, detail_type: str, detail: dict[str, Any], source: str = "agenteval"
    ) -> str:
        """
        Publish event to EventBridge

        Args:
            detail_type: Event type (e.g., "CampaignStarted")
            detail: Event payload
            source: Event source identifier

        Returns:
            Event ID
        """
        self._ensure_connected()
        try:
            response = await self._client.put_events(
                Entries=[
                    {
                        "Time": datetime.utcnow(),
                        "Source": source,
                        "DetailType": detail_type,
                        "Detail": json.dumps(detail),
                        "EventBusName": self.bus_name,
                    }
                ]
            )

            if response["FailedEntryCount"] > 0:
                logger.error(f"Failed to publish event: {response['Entries'][0]}")
                raise RuntimeError("Event publication failed")

            event_id = response["Entries"][0]["EventId"]
            logger.info(f"Published event {detail_type}: {event_id}")
            return event_id

        except ClientError as e:
            logger.error(f"EventBridge error: {e}")
            raise

    async def publish_campaign_event(self, event_type: str, campaign_id: str, **extra: Any) -> str:
        """
        Publish campaign-related event

        Args:
            event_type: Event type (Started, Paused, Resumed, Completed, Cancelled)
            campaign_id: Campaign identifier
            **extra: Additional event data

        Returns:
            Event ID
        """
        detail = {"campaign_id": campaign_id, "timestamp": datetime.utcnow().isoformat(), **extra}
        return await self.publish_event(f"Campaign{event_type}", detail)

    async def publish_turn_event(
        self, campaign_id: str, turn_id: str, agent_type: str, trace_id: str, **extra: Any
    ) -> str:
        """
        Publish conversation turn event

        Args:
            campaign_id: Campaign identifier
            turn_id: Turn identifier
            agent_type: Type of agent (persona, redteam)
            trace_id: Distributed trace ID
            **extra: Additional event data

        Returns:
            Event ID
        """
        detail = {
            "campaign_id": campaign_id,
            "turn_id": turn_id,
            "agent_type": agent_type,
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            **extra,
        }
        return await self.publish_event("TurnCompleted", detail)

    async def publish_attack_event(
        self,
        campaign_id: str,
        attack_id: str,
        attack_type: str,
        success: bool,
        severity: str,
        trace_id: str,
        **extra: Any,
    ) -> str:
        """
        Publish attack event

        Args:
            campaign_id: Campaign identifier
            attack_id: Attack identifier
            attack_type: Type of attack
            success: Whether attack succeeded
            severity: Attack severity
            trace_id: Distributed trace ID
            **extra: Additional event data

        Returns:
            Event ID
        """
        detail = {
            "campaign_id": campaign_id,
            "attack_id": attack_id,
            "attack_type": attack_type,
            "success": success,
            "severity": severity,
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            **extra,
        }

        event_type = "AttackSuccessful" if success else "AttackFailed"
        return await self.publish_event(event_type, detail)

    async def publish_evaluation_event(
        self,
        campaign_id: str,
        eval_id: str,
        overall_score: float,
        critical_issues: int,
        **extra: Any,
    ) -> str:
        """
        Publish evaluation completion event

        Args:
            campaign_id: Campaign identifier
            eval_id: Evaluation identifier
            overall_score: Overall evaluation score
            critical_issues: Number of critical issues found
            **extra: Additional event data

        Returns:
            Event ID
        """
        detail = {
            "campaign_id": campaign_id,
            "eval_id": eval_id,
            "overall_score": overall_score,
            "critical_issues": critical_issues,
            "timestamp": datetime.utcnow().isoformat(),
            **extra,
        }
        return await self.publish_event("EvaluationCompleted", detail)


async def get_eventbridge_client() -> EventBridgeClient:
    """Dependency injection for EventBridge client"""
    return EventBridgeClient()
