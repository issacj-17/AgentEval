"""
Campaign management endpoints
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from agenteval.application.campaign_service import (
    CampaignNotFoundError,
    CampaignService,
    CampaignStateError,
    CampaignValidationError,
)
from agenteval.container import get_campaign_service

logger = logging.getLogger(__name__)

router = APIRouter()  # Auth dependency removed for easier testing; add back for production: dependencies=[Depends(require_api_key)]

# Placeholder for test monkeypatching (used by integration tests)
orchestrator = None


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateCampaignRequest(BaseModel):
    """Request model for creating a campaign"""

    campaign_type: str = Field(..., description="Campaign type: persona, red_team, or combined")
    target_url: str = Field(..., description="Target system URL to evaluate")
    max_turns: int = Field(10, description="Maximum number of turns", ge=1, le=100)

    # Persona-specific config
    persona_type: str | None = Field(None, description="Persona type if campaign_type=persona")
    initial_goal: str | None = Field(None, description="Initial goal for persona")

    # Red team-specific config
    attack_categories: list[str] | None = Field(
        None, description="Attack categories for red_team"
    )
    severity_threshold: str | None = Field(None, description="Minimum attack severity")
    use_mutations: bool | None = Field(True, description="Enable attack mutations")

    class Config:
        json_schema_extra = {
            "example": {
                "campaign_type": "persona",
                "target_url": "https://api.example.com/chat",
                "max_turns": 10,
                "persona_type": "frustrated_customer",
                "initial_goal": "Get help with my billing issue",
            }
        }


class CampaignResponse(BaseModel):
    """Response model for campaign metadata"""

    campaign_id: str
    campaign_type: str
    target_url: str
    status: str
    created_at: str
    updated_at: str
    stats: dict[str, Any]


class CampaignListResponse(BaseModel):
    """Response model for campaign list"""

    campaigns: list[CampaignResponse]
    total: int


# ============================================================================
# Campaign CRUD Endpoints
# ============================================================================


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    request: CreateCampaignRequest,
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, Any]:
    """
    Create a new evaluation campaign

    Args:
        request: Campaign creation request

    Returns:
        Campaign metadata
    """
    try:
        # Call service to create campaign (service handles all validation)
        campaign_metadata = await campaign_service.create_campaign(
            campaign_type=request.campaign_type,
            target_url=request.target_url,
            max_turns=request.max_turns,
            persona_type=request.persona_type,
            initial_goal=request.initial_goal,
            attack_categories=request.attack_categories,
            severity_threshold=request.severity_threshold,
            use_mutations=request.use_mutations,
        )

        return {"message": "Campaign created successfully", "campaign": campaign_metadata}

    except CampaignValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create campaign: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str, campaign_service: CampaignService = Depends(get_campaign_service)
) -> dict[str, Any]:
    """
    Get campaign metadata

    Args:
        campaign_id: Campaign identifier

    Returns:
        Campaign metadata
    """
    try:
        campaign = await campaign_service.get_campaign(campaign_id)
        return {"campaign": campaign}

    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign: {str(e)}",
        )


@router.get("/campaigns")
async def list_campaigns(
    status_filter: str | None = None,
    limit: int = 20,
    offset: int = 0,
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, Any]:
    """
    List campaigns with optional filtering

    Args:
        status_filter: Filter by campaign status
        limit: Maximum number of campaigns to return
        offset: Number of campaigns to skip

    Returns:
        List of campaigns
    """
    try:
        result = await campaign_service.list_campaigns(
            status_filter=status_filter, limit=limit, offset=offset
        )
        return result

    except CampaignValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list campaigns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list campaigns: {str(e)}",
        )


# ============================================================================
# Campaign Execution Endpoints
# ============================================================================


@router.post("/campaigns/{campaign_id}/start")
async def start_campaign(
    campaign_id: str,
    max_turns: int | None = None,
    campaign_service: CampaignService = Depends(get_campaign_service),
) -> dict[str, Any]:
    """
    Start campaign execution

    Executes in background and returns immediately

    Args:
        campaign_id: Campaign identifier
        max_turns: Override max_turns from campaign config

    Returns:
        Execution status
    """
    try:
        result = await campaign_service.start_campaign(campaign_id=campaign_id, max_turns=max_turns)

        return {"message": "Campaign execution started", **result}

    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CampaignStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start campaign: {str(e)}",
        )


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str, campaign_service: CampaignService = Depends(get_campaign_service)
) -> dict[str, Any]:
    """
    Pause campaign execution

    Args:
        campaign_id: Campaign identifier

    Returns:
        Updated status
    """
    try:
        await campaign_service.pause_campaign(campaign_id)

        return {"message": "Campaign paused", "campaign_id": campaign_id, "status": "paused"}

    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CampaignStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to pause campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause campaign: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/status")
async def get_campaign_status(
    campaign_id: str, campaign_service: CampaignService = Depends(get_campaign_service)
) -> dict[str, Any]:
    """
    Get campaign execution status

    Args:
        campaign_id: Campaign identifier

    Returns:
        Execution status and progress
    """
    try:
        return await campaign_service.get_campaign_status(campaign_id)

    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get campaign status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign status: {str(e)}",
        )


@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str, campaign_service: CampaignService = Depends(get_campaign_service)
) -> dict[str, str]:
    """
    Delete a campaign

    Args:
        campaign_id: Campaign identifier

    Returns:
        Deletion confirmation
    """
    try:
        result = await campaign_service.delete_campaign(campaign_id)

        return {"message": "Campaign deleted successfully", **result}

    except CampaignNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except CampaignStateError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete campaign: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete campaign: {str(e)}",
        )
