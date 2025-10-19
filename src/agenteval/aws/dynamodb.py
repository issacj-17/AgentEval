"""
Amazon DynamoDB Client for State Management

Handles campaign state, turns, evaluations, and attack knowledge base.
"""

import logging
import re
from datetime import datetime
from decimal import Decimal
from itertools import islice
from typing import Any

import aioboto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from agenteval.config import settings

logger = logging.getLogger(__name__)

_ATTRIBUTE_SANITIZER = re.compile(r"[^a-zA-Z0-9_]")


def _make_placeholder_name(base: str, existing: dict[str, Any], prefix: str) -> str:
    """Generate a DynamoDB expression placeholder name that avoids collisions."""

    sanitized = _ATTRIBUTE_SANITIZER.sub("_", base or "attr")
    if not sanitized or sanitized[0].isdigit():
        sanitized = f"attr_{sanitized}"

    candidate = f"{prefix}{sanitized}"
    index = 1
    while candidate in existing:
        index += 1
        candidate = f"{prefix}{sanitized}_{index}"
    return candidate


def python_to_dynamodb(obj: Any) -> Any:
    """Convert Python types to DynamoDB-compatible types"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: python_to_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [python_to_dynamodb(item) for item in obj]
    return obj


def dynamodb_to_python(obj: Any) -> Any:
    """Convert DynamoDB types to Python types"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: dynamodb_to_python(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [dynamodb_to_python(item) for item in obj]
    return obj


class DynamoDBClient:
    """
    Async client for Amazon DynamoDB operations

    Supports dependency injection of configuration parameters.
    Falls back to global settings if not provided.
    """

    def __init__(
        self,
        region: str | None = None,
        profile: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        campaigns_table: str | None = None,
        turns_table: str | None = None,
        evaluations_table: str | None = None,
        knowledge_base_table: str | None = None,
    ) -> None:
        """
        Initialize DynamoDB client

        Args:
            region: AWS region (defaults to settings.aws.region)
            profile: AWS profile name (defaults to settings.aws.profile)
            access_key_id: AWS access key ID (defaults to settings.aws.access_key_id)
            secret_access_key: AWS secret access key (defaults to settings.aws.secret_access_key)
            campaigns_table: Campaigns table name (defaults to settings.aws.dynamodb_campaigns_table)
            turns_table: Turns table name (defaults to settings.aws.dynamodb_turns_table)
            evaluations_table: Evaluations table name (defaults to settings.aws.dynamodb_evaluations_table)
            knowledge_base_table: Knowledge base table name (defaults to settings.aws.dynamodb_knowledge_base_table)
        """
        # Use provided config or fall back to settings (backward compatibility)
        self.region = region or settings.aws.region
        self.profile = profile or settings.aws.profile
        self.access_key_id = access_key_id or settings.aws.access_key_id
        self.secret_access_key = secret_access_key or settings.aws.secret_access_key

        # Table names
        self.campaigns_table = campaigns_table or settings.aws.dynamodb_campaigns_table
        self.turns_table = turns_table or settings.aws.dynamodb_turns_table
        self.evaluations_table = evaluations_table or settings.aws.dynamodb_evaluations_table
        self.knowledge_base_table = (
            knowledge_base_table or settings.aws.dynamodb_knowledge_base_table
        )

        self.session = aioboto3.Session(
            region_name=self.region,
            profile_name=self.profile,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        self._resource: Any | None = None
        self._connected: bool = False

        logger.debug(
            "DynamoDBClient initialized",
            extra={"region": self.region, "profile": self.profile or "default"},
        )

    async def connect(self) -> None:
        """Initialize DynamoDB resource connection"""
        if not self._connected:
            self._resource = await self.session.resource("dynamodb").__aenter__()
            self._connected = True
            logger.info("DynamoDB client connected")

    async def close(self) -> None:
        """Close DynamoDB resource connection"""
        if self._connected and self._resource:
            await self._resource.__aexit__(None, None, None)
            self._connected = False
            logger.info("DynamoDB client closed")

    async def __aenter__(self) -> "DynamoDBClient":
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.close()

    def _ensure_connected(self) -> None:
        """Ensure client is connected before operations"""
        if not self._connected or not self._resource:
            raise RuntimeError("DynamoDB client not connected. Call connect() first.")

    # ============================================================================
    # Campaign Operations
    # ============================================================================

    def _normalize_campaign_item(self, item: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        Normalize raw DynamoDB campaign item into canonical metadata structure.

        The live system historically stored the full campaign metadata inside a
        nested `config` attribute. Newer records flatten key fields. This helper
        keeps both layouts compatible for consumers.
        """
        if not item:
            return None

        # Historical data stored the full metadata blob under `config`
        raw_metadata = {}
        candidate = item.get("metadata") or item.get("config")
        if isinstance(candidate, dict):
            raw_metadata = candidate.copy()

        normalized: dict[str, Any] = {
            "campaign_id": item.get("campaign_id") or raw_metadata.get("campaign_id"),
            "campaign_type": item.get("campaign_type") or raw_metadata.get("campaign_type"),
            "target_url": item.get("target_url") or raw_metadata.get("target_url"),
            "status": item.get("status") or raw_metadata.get("status") or "created",
            "created_at": raw_metadata.get("created_at") or item.get("created_at"),
            "updated_at": item.get("updated_at") or raw_metadata.get("updated_at"),
            "config": raw_metadata.get("config") or item.get("config") or {},
            "stats": item.get("stats") or raw_metadata.get("stats") or {},
        }

        # Preserve any additional metadata fields (e.g., demo annotations)
        for key, value in raw_metadata.items():
            normalized.setdefault(key, value)

        return normalized

    async def create_campaign(self, campaign_id: str, config: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new campaign

        Args:
            campaign_id: Unique campaign identifier
            config: Campaign configuration

        Returns:
            Created campaign dict
        """
        self._ensure_connected()
        table = await self._resource.Table(self.campaigns_table)

        # Ensure timestamps exist so downstream consumers receive consistent data
        created_at = config.get("created_at") or datetime.utcnow().isoformat()
        updated_at = config.get("updated_at") or created_at

        campaign_record = {
            "PK": f"CAMPAIGN#{campaign_id}",
            "SK": "METADATA",
            "campaign_id": campaign_id,
            "campaign_type": config.get("campaign_type"),
            "target_url": config.get("target_url"),
            "status": config.get("status", "created"),
            "created_at": created_at,
            "updated_at": updated_at,
            "config": python_to_dynamodb(config.get("config", {})),
            "stats": python_to_dynamodb(config.get("stats", {})),
            # Store the full metadata blob for legacy compatibility/debugging
            "metadata": python_to_dynamodb(
                {**config, "created_at": created_at, "updated_at": updated_at}
            ),
        }

        try:
            await table.put_item(Item=campaign_record)
            logger.info(f"Campaign created: {campaign_id}")
            return self._normalize_campaign_item(dynamodb_to_python(campaign_record))
        except ClientError as e:
            logger.error(f"Failed to create campaign: {e}")
            raise

    async def get_campaign(self, campaign_id: str) -> dict[str, Any] | None:
        """
        Retrieve campaign by ID

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign dict or None if not found
        """
        self._ensure_connected()
        table = await self._resource.Table(self.campaigns_table)

        try:
            response = await table.get_item(Key={"PK": f"CAMPAIGN#{campaign_id}", "SK": "METADATA"})
            item = response.get("Item")
            if not item:
                return None

            return self._normalize_campaign_item(dynamodb_to_python(item))
        except ClientError as e:
            logger.error(f"Failed to get campaign: {e}")
            raise

    async def update_campaign_status(
        self, campaign_id: str, status: str, **extra: Any
    ) -> dict[str, Any]:
        """
        Update campaign status

        Args:
            campaign_id: Campaign identifier
            status: New status
            **extra: Additional attributes to update

        Returns:
            Updated campaign dict
        """
        self._ensure_connected()
        table = await self._resource.Table(self.campaigns_table)

        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_values = {":status": status, ":updated_at": datetime.utcnow().isoformat()}
        expression_names = {"#status": "status"}

        # Add extra attributes
        for key, value in extra.items():
            name_placeholder = _make_placeholder_name(key, expression_names, "#attr_")
            value_placeholder = _make_placeholder_name(key, expression_values, ":attr_")
            expression_names[name_placeholder] = key
            expression_values[value_placeholder] = python_to_dynamodb(value)
            update_expression += f", {name_placeholder} = {value_placeholder}"

        try:
            response = await table.update_item(
                Key={"PK": f"CAMPAIGN#{campaign_id}", "SK": "METADATA"},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
                ReturnValues="ALL_NEW",
            )
            return dynamodb_to_python(response["Attributes"])
        except ClientError as e:
            logger.error(f"Failed to update campaign status: {e}")
            raise

    async def update_campaign_stats(
        self, campaign_id: str, stats: dict[str, Any]
    ) -> dict[str, Any]:
        """Update campaign statistics."""
        self._ensure_connected()
        table = await self._resource.Table(self.campaigns_table)

        try:
            response = await table.update_item(
                Key={"PK": f"CAMPAIGN#{campaign_id}", "SK": "METADATA"},
                UpdateExpression="SET stats = :stats, updated_at = :updated_at",
                ExpressionAttributeValues={
                    ":stats": python_to_dynamodb(stats),
                    ":updated_at": datetime.utcnow().isoformat(),
                },
                ReturnValues="ALL_NEW",
            )
            return dynamodb_to_python(response["Attributes"])
        except ClientError as e:
            logger.error(f"Failed to update campaign stats: {e}")
            raise

    async def list_campaigns(
        self, status_filter: str | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List campaigns with optional status filter."""
        self._ensure_connected()
        table = await self._resource.Table(self.campaigns_table)

        scan_kwargs: dict[str, Any] = {}
        if status_filter:
            scan_kwargs["FilterExpression"] = Attr("status").eq(status_filter)

        items: list[dict[str, Any]] = []
        last_evaluated_key: dict[str, Any] | None = None

        try:
            while True:
                if last_evaluated_key:
                    scan_kwargs["ExclusiveStartKey"] = last_evaluated_key

                response = await table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))
                last_evaluated_key = response.get("LastEvaluatedKey")

                if not last_evaluated_key or len(items) >= offset + limit:
                    break

            sliced = list(islice(items, offset, offset + limit))
            return [self._normalize_campaign_item(dynamodb_to_python(item)) for item in sliced]
        except ClientError as e:
            logger.error(f"Failed to list campaigns: {e}")
            raise

    # ============================================================================
    # Turn Operations
    # ============================================================================

    async def save_turn(
        self, campaign_id: str, turn_id: str, turn_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Save conversation turn

        Args:
            campaign_id: Campaign identifier
            turn_id: Turn identifier
            turn_data: Turn data

        Returns:
            Saved turn dict
        """
        self._ensure_connected()
        table = await self._resource.Table(self.turns_table)

        turn = {
            "PK": f"CAMPAIGN#{campaign_id}",
            "SK": f"TURN#{turn_id}",
            "campaign_id": campaign_id,
            "turn_id": turn_id,
            "timestamp": datetime.utcnow().isoformat(),
            **python_to_dynamodb(turn_data),
        }

        try:
            await table.put_item(Item=turn)
            logger.debug(f"Turn saved: {campaign_id}/{turn_id}")
            return dynamodb_to_python(turn)
        except ClientError as e:
            logger.error(f"Failed to save turn: {e}")
            raise

    async def get_turns(
        self, campaign_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Get all turns for a campaign

        Args:
            campaign_id: Campaign identifier
            limit: Maximum number of turns to return

        Returns:
            List of turn dicts
        """
        self._ensure_connected()
        table = await self._resource.Table(self.turns_table)

        query_kwargs = {
            "KeyConditionExpression": "PK = :pk AND begins_with(SK, :sk_prefix)",
            "ExpressionAttributeValues": {":pk": f"CAMPAIGN#{campaign_id}", ":sk_prefix": "TURN#"},
        }

        if limit:
            query_kwargs["Limit"] = limit

        try:
            response = await table.query(**query_kwargs)
            items = response.get("Items", [])
            return [dynamodb_to_python(item) for item in items]
        except ClientError as e:
            logger.error(f"Failed to get turns: {e}")
            raise

    async def get_campaign_turns(
        self, campaign_id: str, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Get campaign turns with pagination support."""
        turns = await self.get_turns(campaign_id)
        return list(islice(turns, offset, offset + limit))

    async def get_turn(self, campaign_id: str, turn_id: str) -> dict[str, Any] | None:
        """Retrieve a specific turn for a campaign."""
        self._ensure_connected()
        table = await self._resource.Table(self.turns_table)

        candidate_ids = [turn_id]
        if not turn_id.startswith(campaign_id):
            candidate_ids.append(f"{campaign_id}-turn-{turn_id.split('-')[-1]}")

        try:
            for candidate in candidate_ids:
                response = await table.get_item(
                    Key={"PK": f"CAMPAIGN#{campaign_id}", "SK": f"TURN#{candidate}"}
                )
                item = response.get("Item")
                if item:
                    return dynamodb_to_python(item)
        except ClientError as e:
            logger.error(f"Failed to get turn: {e}")
            raise
        return None

    async def update_turn_status(
        self, campaign_id: str, turn_id: str, status: str, **extra: Any
    ) -> dict[str, Any]:
        """Update turn status metadata."""
        self._ensure_connected()
        table = await self._resource.Table(self.turns_table)

        update_expression = "SET #status = :status, updated_at = :updated_at"
        expression_values: dict[str, Any] = {
            ":status": status,
            ":updated_at": datetime.utcnow().isoformat(),
        }
        expression_names = {"#status": "status"}

        for key, value in extra.items():
            name_placeholder = _make_placeholder_name(key, expression_names, "#attr_")
            value_placeholder = _make_placeholder_name(key, expression_values, ":attr_")
            expression_names[name_placeholder] = key
            expression_values[value_placeholder] = python_to_dynamodb(value)
            update_expression += f", {name_placeholder} = {value_placeholder}"

        candidate_ids = [turn_id]
        if not turn_id.startswith(campaign_id):
            candidate_ids.append(f"{campaign_id}-turn-{turn_id.split('-')[-1]}")

        for candidate in candidate_ids:
            try:
                response = await table.update_item(
                    Key={"PK": f"CAMPAIGN#{campaign_id}", "SK": f"TURN#{candidate}"},
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_values,
                    ExpressionAttributeNames=expression_names,
                    ConditionExpression="attribute_exists(PK)",
                    ReturnValues="ALL_NEW",
                )
                return dynamodb_to_python(response["Attributes"])
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                if error_code == "ConditionalCheckFailedException":
                    continue
                logger.error(f"Failed to update turn status: {e}")
                raise

        raise ValueError(f"Turn {turn_id} not found for campaign {campaign_id}")

    # ============================================================================
    # Evaluation Operations
    # ============================================================================

    async def save_evaluation(
        self, campaign_id: str, eval_id: str, evaluation_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Save evaluation result

        Args:
            campaign_id: Campaign identifier
            eval_id: Evaluation identifier
            evaluation_data: Evaluation data

        Returns:
            Saved evaluation dict
        """
        self._ensure_connected()
        table = await self._resource.Table(self.evaluations_table)

        evaluation = {
            "PK": f"CAMPAIGN#{campaign_id}",
            "SK": f"EVAL#{eval_id}",
            "campaign_id": campaign_id,
            "eval_id": eval_id,
            "timestamp": datetime.utcnow().isoformat(),
            **python_to_dynamodb(evaluation_data),
        }

        try:
            await table.put_item(Item=evaluation)
            logger.debug(f"Evaluation saved: {campaign_id}/{eval_id}")
            return dynamodb_to_python(evaluation)
        except ClientError as e:
            logger.error(f"Failed to save evaluation: {e}")
            raise

    async def get_evaluations(self, campaign_id: str) -> list[dict[str, Any]]:
        """
        Get all evaluations for a campaign

        Args:
            campaign_id: Campaign identifier

        Returns:
            List of evaluation dicts
        """
        self._ensure_connected()
        table = await self._resource.Table(self.evaluations_table)

        try:
            response = await table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={":pk": f"CAMPAIGN#{campaign_id}", ":sk_prefix": "EVAL#"},
            )
            items = response.get("Items", [])
            return [dynamodb_to_python(item) for item in items]
        except ClientError as e:
            logger.error(f"Failed to get evaluations: {e}")
            raise

    # ============================================================================
    # Attack Knowledge Base Operations
    # ============================================================================

    async def save_attack_knowledge(
        self, attack_id: str, knowledge_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Save successful attack to knowledge base

        Args:
            attack_id: Attack identifier
            knowledge_data: Attack knowledge data

        Returns:
            Saved knowledge dict
        """
        self._ensure_connected()
        table = await self._resource.Table(self.knowledge_base_table)

        knowledge = {
            "PK": f"ATTACK#{attack_id}",
            "SK": "KNOWLEDGE",
            "attack_id": attack_id,
            "timestamp": datetime.utcnow().isoformat(),
            **python_to_dynamodb(knowledge_data),
        }

        try:
            await table.put_item(Item=knowledge)
            logger.info(f"Attack knowledge saved: {attack_id}")
            return dynamodb_to_python(knowledge)
        except ClientError as e:
            logger.error(f"Failed to save attack knowledge: {e}")
            raise

    async def get_successful_attacks(
        self, target_system: str | None = None, category: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Retrieve successful attacks from knowledge base

        Args:
            target_system: Filter by target system
            category: Filter by attack category
            limit: Maximum number of results

        Returns:
            List of successful attack dicts
        """
        self._ensure_connected()
        table = await self._resource.Table(self.knowledge_base_table)

        # For now, use scan (in production, use GSI for better performance)
        scan_kwargs = {"Limit": limit}

        if target_system or category:
            filter_expressions = []
            expression_values = {}

            if target_system:
                filter_expressions.append("target_system = :target")
                expression_values[":target"] = target_system

            if category:
                filter_expressions.append("category = :category")
                expression_values[":category"] = category

            scan_kwargs["FilterExpression"] = " AND ".join(filter_expressions)
            scan_kwargs["ExpressionAttributeValues"] = expression_values

        try:
            response = await table.scan(**scan_kwargs)
            items = response.get("Items", [])
            return [dynamodb_to_python(item) for item in items]
        except ClientError as e:
            logger.error(f"Failed to get successful attacks: {e}")
            raise

    # ============================================================================
    # Generic Table Operations (for dashboard/reporting)
    # ============================================================================

    async def scan_table(
        self, table_name: str, filter_expression: Any | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Scan a DynamoDB table and return all items.

        Args:
            table_name: Name of the table to scan
            filter_expression: Optional boto3 filter expression
            limit: Optional maximum number of items to return

        Returns:
            List of items (converted from DynamoDB format to Python)
        """
        self._ensure_connected()
        table = await self._resource.Table(table_name)

        items = []
        scan_kwargs = {}

        if filter_expression is not None:
            scan_kwargs["FilterExpression"] = filter_expression

        try:
            # Handle pagination
            response = await table.scan(**scan_kwargs)
            items.extend(response.get("Items", []))

            # Continue scanning if there are more items
            while "LastEvaluatedKey" in response and (limit is None or len(items) < limit):
                scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                response = await table.scan(**scan_kwargs)
                items.extend(response.get("Items", []))

            # Apply limit if specified
            if limit is not None:
                items = items[:limit]

            # Convert from DynamoDB format to Python format
            return [dynamodb_to_python(item) for item in items]

        except ClientError as e:
            logger.error(f"Failed to scan table {table_name}: {e}")
            return []  # Return empty list on error (non-fatal for dashboards)

    # ============================================================================
    # Additional Helper Methods (called by orchestrator)
    # ============================================================================

    async def update_campaign_stats(
        self, campaign_id: str, stats: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update campaign statistics

        Args:
            campaign_id: Campaign identifier
            stats: Statistics dict

        Returns:
            Updated campaign dict
        """
        self._ensure_connected()
        table = await self._resource.Table(self.campaigns_table)

        update_expression = "SET stats = :stats, updated_at = :updated_at"
        expression_values = {
            ":stats": python_to_dynamodb(stats),
            ":updated_at": datetime.utcnow().isoformat(),
        }

        try:
            response = await table.update_item(
                Key={"PK": f"CAMPAIGN#{campaign_id}", "SK": "METADATA"},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ReturnValues="ALL_NEW",
            )
            return dynamodb_to_python(response["Attributes"])
        except ClientError as e:
            logger.error(f"Failed to update campaign stats: {e}")
            raise


# Global client instance (use with context manager)
async def get_dynamodb_client() -> DynamoDBClient:
    """Dependency injection for DynamoDB client"""
    return DynamoDBClient()
