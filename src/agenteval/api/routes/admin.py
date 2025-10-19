"""
Admin endpoints for system management

Provides consistent endpoints for managing all three libraries:
- PersonaLibrary
- AttackLibrary
- MetricLibrary

Each library supports:
- GET /list - List all items with metadata
- GET /list/{id} - Get specific item details
- POST /reload - Hot-reload library from YAML
- GET /validate - Validate library integrity
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Path as PathParam

from agenteval.api.dependencies import require_api_key
from agenteval.aws.dynamodb import DynamoDBClient
from agenteval.aws.xray import XRayClient
from agenteval.config import settings
from agenteval.container import get_dynamodb, get_xray
from agenteval.evaluation.metrics import (
    get_metric_library,
    metric_registry,
    reload_metric_library,
)
from agenteval.persona import get_persona_library
from agenteval.persona import reload_persona_library as reload_personas
from agenteval.redteam.library import (
    AttackCategory,
    attack_library,
    get_attack_library,
    reload_attack_library,
)

logger = logging.getLogger(__name__)

# All admin routes require API key authentication
router = APIRouter(dependencies=[Depends(require_api_key)])


@router.get("/info")
async def get_system_info() -> dict[str, Any]:
    """
    Get system information

    Returns:
        System configuration and capabilities
    """
    persona_library = get_persona_library()

    return {
        "version": "1.0.0",
        "environment": settings.app.environment,
        "capabilities": {
            "agents": {
                "persona_types": persona_library.list_persona_ids(),
                "persona_count": persona_library.get_persona_count(),
                "persona_categories": persona_library.list_categories(),
                "attack_categories": len(attack_library.get_all_attacks()),
                "evaluation_metrics": len(metric_registry.get_all_metrics()),
            },
            "features": {
                "tracing_enabled": settings.observability.enable_tracing,
                "multi_judge_debate": True,
                "attack_mutations": True,
                "trace_correlation": True,  # SECRET SAUCE
            },
        },
        "aws": {
            "region": settings.aws.region,
            "bedrock_persona_model": settings.aws.bedrock_persona_model,
            "bedrock_redteam_model": settings.aws.bedrock_redteam_model,
            "bedrock_judge_model": settings.aws.bedrock_judge_model,
        },
    }


@router.get("/metrics")
async def list_metrics() -> dict[str, Any]:
    """
    List all available evaluation metrics

    Returns:
        All metrics grouped by category
    """
    all_metrics = metric_registry.get_all_metrics()

    metrics_by_category = {
        "quality": [
            {"type": m.metric_type.value, "threshold": m.threshold, "category": m.category.value}
            for m in metric_registry.get_quality_metrics()
        ],
        "safety": [
            {"type": m.metric_type.value, "threshold": m.threshold, "category": m.category.value}
            for m in metric_registry.get_safety_metrics()
        ],
        "agent_specific": [
            {"type": m.metric_type.value, "threshold": m.threshold, "category": m.category.value}
            for m in metric_registry.get_agent_metrics()
        ],
    }

    return {"total_metrics": len(all_metrics), "metrics_by_category": metrics_by_category}


@router.get("/attacks")
async def list_attacks() -> dict[str, Any]:
    """
    List all available attack patterns

    Returns:
        All attacks grouped by category
    """

    attacks_by_category = {}

    for category in AttackCategory:
        category_attacks = attack_library.get_attacks_by_category(category)
        attacks_by_category[category.value] = [
            {
                "name": attack.name,
                "severity": attack.severity.value,
                "description": attack.description,
                "tags": attack.tags,
            }
            for attack in category_attacks
        ]

    attack_counts = attack_library.get_attack_count()

    return {
        "total_attacks": attack_counts["total"],
        "counts_by_category": {
            cat: count for cat, count in attack_counts.items() if cat != "total"
        },
        "attacks_by_category": attacks_by_category,
    }


@router.get("/personas")
async def list_personas() -> dict[str, Any]:
    """
    List all available persona types from library

    Returns:
        All persona types with descriptions from YAML library
    """
    persona_library = get_persona_library()
    all_personas = persona_library.get_all_personas()

    personas = {}
    for persona in all_personas:
        personas[persona.id] = {
            "id": persona.id,
            "name": persona.name,
            "category": persona.category,
            "description": persona.description,
            "attributes": persona.attributes,
            "behavioral_traits": persona.behavioral_traits,
            "patience_level": persona.patience_level,
            "frustration_level": persona.frustration_level,
            "communication_style": persona.communication_style,
        }

    # Group by category
    personas_by_category = {}
    for category in persona_library.list_categories():
        category_personas = persona_library.get_personas_by_category(category)
        personas_by_category[category] = [p.id for p in category_personas]

    return {
        "total_personas": persona_library.get_persona_count(),
        "categories": persona_library.list_categories(),
        "personas_by_category": personas_by_category,
        "personas": personas,
    }


@router.get("/personas/{persona_id}")
async def get_persona_detail(
    persona_id: str = PathParam(..., description="Persona ID"),
) -> dict[str, Any]:
    """
    Get detailed information about a specific persona

    Args:
        persona_id: Unique persona identifier

    Returns:
        Complete persona definition
    """
    persona_library = get_persona_library()
    persona = persona_library.get_persona(persona_id)

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Persona '{persona_id}' not found"
        )

    return {"persona": persona.to_dict()}


@router.post("/personas/reload")
async def reload_persona_library_endpoint() -> dict[str, Any]:
    """
    Reload persona library from YAML file

    Useful for hot-reloading persona definitions without restarting the API.

    Returns:
        Reload confirmation with updated persona count
    """
    try:
        reload_personas()
        persona_library = get_persona_library()

        logger.info("Persona library reloaded")

        return {
            "message": "Persona library reloaded successfully",
            "library_type": "persona",
            "total_items": persona_library.get_persona_count(),
            "item_ids": persona_library.list_persona_ids(),
            "categories": persona_library.list_categories(),
            "library_path": persona_library.library_path,
        }

    except Exception as e:
        logger.error(f"Failed to reload persona library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload persona library: {str(e)}",
        )


@router.get("/personas/validate")
async def validate_persona_library() -> dict[str, Any]:
    """
    Validate persona library integrity

    Returns:
        Validation results
    """
    try:
        persona_library = get_persona_library()
        validation = persona_library.validate()

        return {"library_type": "persona", "validation": validation}

    except Exception as e:
        logger.error(f"Failed to validate persona library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate persona library: {str(e)}",
        )


@router.get("/attacks/{attack_id}")
async def get_attack_detail(
    attack_id: str = PathParam(..., description="Attack ID"),
) -> dict[str, Any]:
    """
    Get detailed information about a specific attack pattern

    Args:
        attack_id: Unique attack identifier

    Returns:
        Complete attack definition
    """
    attack = attack_library.get_attack(attack_id)

    if not attack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Attack '{attack_id}' not found"
        )

    return {"attack": attack.to_dict()}


@router.post("/attacks/reload")
async def reload_attack_library_endpoint() -> dict[str, Any]:
    """
    Reload attack library from YAML file

    Useful for hot-reloading attack definitions without restarting the API.

    Returns:
        Reload confirmation with updated attack count
    """
    try:
        reload_attack_library()
        attack_lib = get_attack_library()

        logger.info("Attack library reloaded")

        return {
            "message": "Attack library reloaded successfully",
            "library_type": "attack",
            "total_items": attack_lib.count(),
            "item_ids": attack_lib.list_ids(),
            "categories": attack_lib.list_categories(),
            "library_path": attack_lib.library_path,
        }

    except Exception as e:
        logger.error(f"Failed to reload attack library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload attack library: {str(e)}",
        )


@router.get("/attacks/validate")
async def validate_attack_library() -> dict[str, Any]:
    """
    Validate attack library integrity

    Returns:
        Validation results
    """
    try:
        attack_lib = get_attack_library()
        validation = attack_lib.validate()

        return {"library_type": "attack", "validation": validation}

    except Exception as e:
        logger.error(f"Failed to validate attack library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate attack library: {str(e)}",
        )


@router.get("/metrics/{metric_id}")
async def get_metric_detail(
    metric_id: str = PathParam(..., description="Metric ID"),
) -> dict[str, Any]:
    """
    Get detailed information about a specific metric

    Args:
        metric_id: Unique metric identifier

    Returns:
        Complete metric definition
    """
    metric_lib = get_metric_library()
    metric = metric_lib.get_metric(metric_id)

    if not metric:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Metric '{metric_id}' not found"
        )

    return {"metric": metric.to_dict()}


@router.post("/metrics/reload")
async def reload_metric_library_endpoint() -> dict[str, Any]:
    """
    Reload metric library from YAML file

    Useful for hot-reloading metric definitions without restarting the API.
    Also reloads the metric registry with updated definitions.

    Returns:
        Reload confirmation with updated metric count
    """
    try:
        reload_metric_library()

        # Also reload the metric registry to pick up changes
        metric_registry.reload()

        metric_lib = get_metric_library()

        logger.info("Metric library and registry reloaded")

        return {
            "message": "Metric library reloaded successfully",
            "library_type": "metric",
            "total_items": metric_lib.count(),
            "item_ids": metric_lib.list_ids(),
            "categories": metric_lib.list_categories(),
            "library_path": metric_lib.library_path,
            "registry_reloaded": True,
        }

    except Exception as e:
        logger.error(f"Failed to reload metric library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload metric library: {str(e)}",
        )


@router.get("/metrics/validate")
async def validate_metric_library() -> dict[str, Any]:
    """
    Validate metric library integrity

    Returns:
        Validation results
    """
    try:
        metric_lib = get_metric_library()
        validation = metric_lib.validate()

        return {"library_type": "metric", "validation": validation}

    except Exception as e:
        logger.error(f"Failed to validate metric library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate metric library: {str(e)}",
        )


@router.get("/libraries")
async def get_libraries_overview() -> dict[str, Any]:
    """
    Get overview of all libraries

    Returns:
        Summary of all three libraries
    """
    try:
        persona_library = get_persona_library()
        attack_lib = get_attack_library()
        metric_lib = get_metric_library()

        return {
            "libraries": {
                "persona": {
                    "total_items": persona_library.count(),
                    "categories": persona_library.list_categories(),
                    "library_path": persona_library.library_path,
                    "library_type": persona_library.library_type.value,
                },
                "attack": {
                    "total_items": attack_lib.count(),
                    "categories": attack_lib.list_categories(),
                    "library_path": attack_lib.library_path,
                    "library_type": attack_lib.library_type.value,
                },
                "metric": {
                    "total_items": metric_lib.count(),
                    "categories": metric_lib.list_categories(),
                    "library_path": metric_lib.library_path,
                    "library_type": metric_lib.library_type.value,
                },
            },
            "totals": {
                "personas": persona_library.count(),
                "attacks": attack_lib.count(),
                "metrics": metric_lib.count(),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get libraries overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get libraries overview: {str(e)}",
        )


@router.post("/libraries/reload")
async def reload_all_libraries() -> dict[str, Any]:
    """
    Reload all libraries from YAML files

    Reloads persona, attack, and metric libraries in one operation.

    Returns:
        Reload confirmation for all libraries
    """
    try:
        # Reload all libraries
        reload_personas()
        reload_attack_library()
        reload_metric_library()
        metric_registry.reload()

        # Get updated libraries
        persona_library = get_persona_library()
        attack_lib = get_attack_library()
        metric_lib = get_metric_library()

        logger.info("All libraries reloaded successfully")

        return {
            "message": "All libraries reloaded successfully",
            "libraries_reloaded": ["persona", "attack", "metric"],
            "results": {
                "persona": {
                    "total_items": persona_library.count(),
                    "categories": persona_library.list_categories(),
                },
                "attack": {
                    "total_items": attack_lib.count(),
                    "categories": attack_lib.list_categories(),
                },
                "metric": {
                    "total_items": metric_lib.count(),
                    "categories": metric_lib.list_categories(),
                    "registry_reloaded": True,
                },
            },
        }

    except Exception as e:
        logger.error(f"Failed to reload all libraries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload all libraries: {str(e)}",
        )


@router.get("/libraries/validate")
async def validate_all_libraries() -> dict[str, Any]:
    """
    Validate all libraries

    Returns:
        Validation results for all three libraries
    """
    try:
        persona_library = get_persona_library()
        attack_lib = get_attack_library()
        metric_lib = get_metric_library()

        persona_validation = persona_library.validate()
        attack_validation = attack_lib.validate()
        metric_validation = metric_lib.validate()

        all_valid = (
            persona_validation["valid"]
            and attack_validation["valid"]
            and metric_validation["valid"]
        )

        return {
            "all_valid": all_valid,
            "validations": {
                "persona": persona_validation,
                "attack": attack_validation,
                "metric": metric_validation,
            },
        }

    except Exception as e:
        logger.error(f"Failed to validate all libraries: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate all libraries: {str(e)}",
        )


@router.post("/cache/clear")
async def clear_cache(xray: XRayClient = Depends(get_xray)) -> dict[str, str]:
    """
    Clear system caches

    Args:
        xray: Injected X-Ray client

    Returns:
        Cache clear confirmation
    """
    try:
        # Clear X-Ray trace cache
        xray._trace_cache.clear()

        logger.info("System caches cleared")

        return {"message": "Caches cleared successfully", "caches_cleared": ["xray_trace_cache"]}

    except Exception as e:
        logger.error(f"Failed to clear cache: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}",
        )


@router.get("/stats")
async def get_system_stats(dynamodb: DynamoDBClient = Depends(get_dynamodb)) -> dict[str, Any]:
    """
    Get system-wide statistics

    Args:
        dynamodb: Injected DynamoDB client

    Returns:
        Aggregate system statistics
    """
    try:
        # Get all campaigns
        campaigns = await dynamodb.list_campaigns(limit=10000)

        # Calculate stats
        total_campaigns = len(campaigns)
        completed_campaigns = sum(1 for c in campaigns if c.get("status") == "completed")
        running_campaigns = sum(1 for c in campaigns if c.get("status") == "running")

        total_turns = sum(c.get("stats", {}).get("total_turns", 0) for c in campaigns)

        persona_library = get_persona_library()

        return {
            "campaigns": {
                "total": total_campaigns,
                "completed": completed_campaigns,
                "running": running_campaigns,
            },
            "turns": {"total": total_turns},
            "capabilities": {
                "total_metrics": len(metric_registry.get_all_metrics()),
                "total_attacks": len(attack_library.get_all_attacks()),
                "total_personas": persona_library.get_persona_count(),
            },
        }

    except Exception as e:
        logger.error(f"Failed to get system stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system stats: {str(e)}",
        )
