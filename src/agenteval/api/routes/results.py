"""
Results and reporting endpoints
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from agenteval.api.dependencies import require_api_key
from agenteval.application.report_service import (
    ReportGenerationError,
    ReportNotFoundError,
    ReportService,
)
from agenteval.container import get_report_service

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/campaigns/{campaign_id}/turns")
async def get_campaign_turns(
    campaign_id: str,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    report_service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    """
    Get all turns for a campaign

    Args:
        campaign_id: Campaign identifier
        limit: Maximum turns to return (1-1000)
        offset: Number of turns to skip
        report_service: Injected report service

    Returns:
        List of turn results with metadata
    """
    try:
        result = await report_service.get_campaign_turns(
            campaign_id=campaign_id, limit=limit, offset=offset
        )
        return result

    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get campaign turns: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign turns: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/turns/{turn_id}")
async def get_turn_detail(
    campaign_id: str, turn_id: str, report_service: ReportService = Depends(get_report_service)
) -> dict[str, Any]:
    """
    Get detailed results for a specific turn

    Args:
        campaign_id: Campaign identifier
        turn_id: Turn identifier
        report_service: Injected report service

    Returns:
        Detailed turn result including evaluation and correlation
    """
    try:
        turn_data = await report_service.get_turn_detail(campaign_id=campaign_id, turn_id=turn_id)

        return {"campaign_id": campaign_id, "turn": turn_data}

    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get turn detail: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get turn detail: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/report")
async def get_campaign_report(
    campaign_id: str,
    format: str | None = Query("json", description="Report format: json, csv, pdf, html"),
    report_service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    """
    Generate comprehensive campaign report

    Includes:
    - Aggregate metrics
    - All turn results
    - Downloadable report in requested format

    Args:
        campaign_id: Campaign identifier
        format: Report format (json, csv, pdf, html)
        report_service: Injected report service

    Returns:
        Campaign report with download URL
    """
    try:
        result = await report_service.generate_campaign_report(
            campaign_id=campaign_id, report_format=format
        )
        return result

    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ReportGenerationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get campaign report: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign report: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/summary")
async def get_campaign_summary(
    campaign_id: str, report_service: ReportService = Depends(get_report_service)
) -> dict[str, Any]:
    """
    Get high-level campaign summary with aggregate metrics

    Args:
        campaign_id: Campaign identifier
        report_service: Injected report service

    Returns:
        Campaign summary with key metrics
    """
    try:
        result = await report_service.get_campaign_summary(campaign_id)
        return result

    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get campaign summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign summary: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/correlations")
async def get_campaign_correlations(
    campaign_id: str, report_service: ReportService = Depends(get_report_service)
) -> dict[str, Any]:
    """
    Get all trace correlations for campaign (SECRET SAUCE results)

    Args:
        campaign_id: Campaign identifier
        report_service: Injected report service

    Returns:
        All correlations and root causes found
    """
    try:
        result = await report_service.get_campaign_correlations(campaign_id)
        return result

    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get campaign correlations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get campaign correlations: {str(e)}",
        )


@router.get("/campaigns/{campaign_id}/recommendations")
async def get_campaign_recommendations(
    campaign_id: str,
    limit: int = Query(20, ge=1, le=100, description="Maximum recommendations to return"),
    report_service: ReportService = Depends(get_report_service),
) -> dict[str, Any]:
    """
    Get actionable recommendations for improving the target system

    Args:
        campaign_id: Campaign identifier
        limit: Maximum number of recommendations to return (1-100)
        report_service: Injected report service

    Returns:
        Prioritized recommendations based on root cause analysis
    """
    try:
        result = await report_service.get_campaign_recommendations(
            campaign_id=campaign_id, limit=limit
        )
        return result

    except ReportNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}",
        )
