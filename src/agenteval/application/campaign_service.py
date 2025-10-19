"""
Campaign Service - Business Logic Layer

Handles all campaign-related business operations including:
- Campaign creation and validation
- Campaign execution orchestration
- Campaign lifecycle management
- Campaign status tracking

This service is framework-agnostic and can be used from:
- FastAPI routes
- CLI commands
- Background tasks
- Tests (with mocked dependencies)
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from agenteval.orchestration.campaign import CampaignOrchestrator, CampaignStatus, CampaignType
from agenteval.persona import get_persona_library
from agenteval.redteam.library import AttackCategory, AttackSeverity

logger = logging.getLogger(__name__)


class CampaignValidationError(Exception):
    """Raised when campaign configuration is invalid"""

    pass


class CampaignNotFoundError(Exception):
    """Raised when campaign is not found"""

    pass


class CampaignStateError(Exception):
    """Raised when campaign is in invalid state for operation"""

    pass


class CampaignService:
    """
    Campaign business logic service

    Provides high-level business operations for campaigns,
    handling validation, orchestration, and state management.
    """

    def __init__(self, orchestrator: CampaignOrchestrator):
        """
        Initialize campaign service

        Args:
            orchestrator: Campaign orchestrator for execution
        """
        self.orchestrator = orchestrator
        logger.debug("CampaignService initialized")

    async def create_campaign(
        self,
        campaign_type: str,
        target_url: str,
        max_turns: int = 10,
        persona_type: str | None = None,
        initial_goal: str | None = None,
        attack_categories: list[str] | None = None,
        severity_threshold: str | None = None,
        use_mutations: bool = True,
        combined_strategy: str | None = None,
        persona_turns: int | None = None,
        persona_weight: float | None = None,
    ) -> dict[str, Any]:
        """
        Create a new evaluation campaign

        Args:
            campaign_type: Type of campaign (persona, red_team, combined)
            target_url: URL of target system
            max_turns: Maximum turns to execute
            persona_type: Persona type for persona campaigns
            initial_goal: Initial goal for persona
            attack_categories: Attack categories for red team
            severity_threshold: Minimum attack severity
            use_mutations: Enable attack mutations
            combined_strategy: Strategy for combined campaigns (round_robin, persona_first, weighted)
            persona_turns: Number of persona turns for persona_first strategy
            persona_weight: Persona weight for weighted strategy

        Returns:
            Campaign metadata

        Raises:
            CampaignValidationError: If configuration is invalid
        """
        # Validate and convert campaign type
        try:
            campaign_type_enum = CampaignType(campaign_type)
        except ValueError:
            valid_types = [t.value for t in CampaignType]
            raise CampaignValidationError(
                f"Invalid campaign_type '{campaign_type}'. Must be one of: {', '.join(valid_types)}"
            )

        # Build campaign config
        campaign_config = {"max_turns": max_turns}

        # Validate persona campaign config
        if campaign_type_enum == CampaignType.PERSONA:
            if not persona_type:
                raise CampaignValidationError("persona_type required for persona campaigns")

            # Validate persona type exists
            persona_library = get_persona_library()
            if not persona_library.get_persona(persona_type):
                available_personas = persona_library.list_persona_ids()
                raise CampaignValidationError(
                    f"Invalid persona_type '{persona_type}'. "
                    f"Available personas: {', '.join(available_personas)}"
                )

            campaign_config["persona_type"] = persona_type
            campaign_config["initial_goal"] = initial_goal or "Get help with my issue"

        # Validate red team campaign config
        elif campaign_type_enum == CampaignType.RED_TEAM:
            if attack_categories:
                try:
                    # Validate each category
                    [AttackCategory(cat) for cat in attack_categories]
                except ValueError:
                    valid_cats = [ac.value for ac in AttackCategory]
                    raise CampaignValidationError(
                        f"Invalid attack_categories. Must be from: {', '.join(valid_cats)}"
                    )
                campaign_config["attack_categories"] = attack_categories

            if severity_threshold:
                try:
                    AttackSeverity(severity_threshold)
                except ValueError:
                    valid_severities = [s.value for s in AttackSeverity]
                    raise CampaignValidationError(
                        f"Invalid severity_threshold. Must be one of: {', '.join(valid_severities)}"
                    )
                campaign_config["severity_threshold"] = severity_threshold

            campaign_config["use_mutations"] = use_mutations

        # Validate combined campaign config
        elif campaign_type_enum == CampaignType.COMBINED:
            # Both persona and red team config needed
            if not persona_type:
                raise CampaignValidationError("persona_type required for combined campaigns")

            persona_library = get_persona_library()
            if not persona_library.get_persona(persona_type):
                available_personas = persona_library.list_persona_ids()
                raise CampaignValidationError(
                    f"Invalid persona_type '{persona_type}'. "
                    f"Available personas: {', '.join(available_personas)}"
                )

            campaign_config["persona_type"] = persona_type
            campaign_config["initial_goal"] = initial_goal or "Get help with my issue"

            # Add combined strategy config
            if combined_strategy:
                valid_strategies = ["round_robin", "persona_first", "weighted"]
                if combined_strategy not in valid_strategies:
                    raise CampaignValidationError(
                        f"Invalid combined_strategy. Must be one of: {', '.join(valid_strategies)}"
                    )
                campaign_config["combined_strategy"] = combined_strategy

                if combined_strategy == "persona_first" and persona_turns:
                    campaign_config["persona_turns"] = persona_turns

                if combined_strategy == "weighted" and persona_weight is not None:
                    if not 0.0 <= persona_weight <= 1.0:
                        raise CampaignValidationError("persona_weight must be between 0.0 and 1.0")
                    campaign_config["persona_weight"] = persona_weight

            # Add red team config for combined
            if attack_categories:
                try:
                    [AttackCategory(cat) for cat in attack_categories]
                except ValueError:
                    valid_cats = [ac.value for ac in AttackCategory]
                    raise CampaignValidationError(
                        f"Invalid attack_categories. Must be from: {', '.join(valid_cats)}"
                    )
                campaign_config["attack_categories"] = attack_categories

            if severity_threshold:
                try:
                    AttackSeverity(severity_threshold)
                except ValueError:
                    valid_severities = [s.value for s in AttackSeverity]
                    raise CampaignValidationError(
                        f"Invalid severity_threshold. Must be one of: {', '.join(valid_severities)}"
                    )
                campaign_config["severity_threshold"] = severity_threshold

            campaign_config["use_mutations"] = use_mutations

        # Create campaign via orchestrator
        campaign_metadata = await self.orchestrator.create_campaign(
            campaign_type=campaign_type_enum, target_url=target_url, campaign_config=campaign_config
        )

        logger.info(
            f"Campaign created via service: {campaign_metadata['campaign_id']}",
            extra={"campaign_id": campaign_metadata["campaign_id"]},
        )

        return campaign_metadata

    async def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        """
        Get campaign by ID

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign metadata

        Raises:
            CampaignNotFoundError: If campaign doesn't exist
        """
        campaign = await self.orchestrator.dynamodb.get_campaign(campaign_id)

        if not campaign:
            raise CampaignNotFoundError(f"Campaign not found: {campaign_id}")

        return campaign

    async def list_campaigns(
        self, status_filter: str | None = None, limit: int = 20, offset: int = 0
    ) -> dict[str, Any]:
        """
        List campaigns with optional filtering

        Args:
            status_filter: Filter by status (created, running, paused, completed, failed)
            limit: Maximum results to return
            offset: Number of results to skip

        Returns:
            Dict with campaigns list and metadata

        Raises:
            CampaignValidationError: If status filter is invalid
        """
        # Validate status filter
        if status_filter:
            try:
                CampaignStatus(status_filter)
            except ValueError:
                valid_statuses = [s.value for s in CampaignStatus]
                raise CampaignValidationError(
                    f"Invalid status filter '{status_filter}'. "
                    f"Must be one of: {', '.join(valid_statuses)}"
                )

        # Get campaigns from DynamoDB
        campaigns = await self.orchestrator.dynamodb.list_campaigns(
            status_filter=status_filter, limit=limit, offset=offset
        )

        return {"campaigns": campaigns, "total": len(campaigns), "limit": limit, "offset": offset}

    async def start_campaign(
        self, campaign_id: str, max_turns: int | None = None, enable_parallel_turns: bool = False
    ) -> dict[str, Any]:
        """
        Start campaign execution in background

        Args:
            campaign_id: Campaign identifier
            max_turns: Override max_turns from config
            enable_parallel_turns: Enable parallel turn execution

        Returns:
            Execution status

        Raises:
            CampaignNotFoundError: If campaign doesn't exist
            CampaignStateError: If campaign is already running
        """
        # Verify campaign exists
        campaign = await self.get_campaign(campaign_id)

        # Check if already running
        if campaign["status"] == CampaignStatus.RUNNING.value:
            raise CampaignStateError(f"Campaign {campaign_id} is already running")

        # Determine effective max_turns
        effective_max_turns = max_turns or campaign["config"].get("max_turns", 10)

        # Execute campaign in background
        task = asyncio.create_task(
            self.orchestrator.run_campaign(
                campaign_id=campaign_id,
                max_turns=effective_max_turns,
                enable_parallel_turns=enable_parallel_turns,
            )
        )
        self.orchestrator._track_task(campaign_id, task)

        logger.info(
            f"Campaign execution started via service: {campaign_id}",
            extra={"campaign_id": campaign_id, "max_turns": effective_max_turns},
        )

        return {
            "campaign_id": campaign_id,
            "status": "running",
            "max_turns": effective_max_turns,
            "parallel_turns": enable_parallel_turns,
            "started_at": datetime.utcnow().isoformat(),
        }

    async def pause_campaign(self, campaign_id: str) -> dict[str, Any]:
        """
        Pause campaign execution

        Args:
            campaign_id: Campaign identifier

        Returns:
            Updated campaign status

        Raises:
            CampaignNotFoundError: If campaign doesn't exist
            CampaignStateError: If campaign is not running
        """
        campaign = await self.get_campaign(campaign_id)

        if campaign["status"] != CampaignStatus.RUNNING.value:
            raise CampaignStateError(
                f"Campaign {campaign_id} is not running (status: {campaign['status']})"
            )

        # Update status to paused
        updated_campaign = await self.orchestrator.dynamodb.update_campaign_status(
            campaign_id=campaign_id, status=CampaignStatus.PAUSED.value
        )

        logger.info(f"Campaign paused via service: {campaign_id}")

        return updated_campaign

    async def get_campaign_status(self, campaign_id: str) -> dict[str, Any]:
        """
        Get campaign execution status and progress

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign status information

        Raises:
            CampaignNotFoundError: If campaign doesn't exist
        """
        campaign = await self.get_campaign(campaign_id)

        return {
            "campaign_id": campaign_id,
            "status": campaign["status"],
            "stats": campaign.get("stats", {}),
            "created_at": campaign["created_at"],
            "updated_at": campaign["updated_at"],
            "config": campaign.get("config", {}),
        }

    async def delete_campaign(self, campaign_id: str) -> dict[str, str]:
        """
        Delete a campaign

        Args:
            campaign_id: Campaign identifier

        Returns:
            Deletion confirmation

        Raises:
            CampaignNotFoundError: If campaign doesn't exist
            CampaignStateError: If campaign is running
        """
        campaign = await self.get_campaign(campaign_id)

        # Don't allow deletion of running campaigns
        if campaign["status"] == CampaignStatus.RUNNING.value:
            raise CampaignStateError(
                f"Cannot delete running campaign {campaign_id}. Pause it first."
            )

        # Delete campaign (orchestrator will handle DynamoDB deletion)
        # Note: This assumes orchestrator has a delete_campaign method
        # If not, we use DynamoDB directly
        try:
            await self.orchestrator.delete_campaign(campaign_id)
        except AttributeError:
            # Orchestrator doesn't have delete method yet, use DynamoDB directly
            logger.warning("Orchestrator.delete_campaign not implemented, using DynamoDB directly")
            # For now, we'll mark it as deleted status
            await self.orchestrator.dynamodb.update_campaign_status(
                campaign_id=campaign_id, status="deleted"
            )

        logger.info(f"Campaign deleted via service: {campaign_id}")

        return {
            "campaign_id": campaign_id,
            "status": "deleted",
            "deleted_at": datetime.utcnow().isoformat(),
        }
