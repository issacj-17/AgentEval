"""
Report Service - Report Generation and Management

Handles all report-related business operations including:
- Report generation in multiple formats (JSON, CSV, PDF, HTML)
- Report storage and retrieval
- Presigned URL generation for downloads
- Report aggregation and statistics

This service is framework-agnostic and coordinates between:
- CampaignOrchestrator for campaign data
- S3Client for report storage
- Report renderers for format conversion
"""

import logging
from datetime import datetime
from typing import Any

from agenteval.aws.s3 import ReportFormat, S3Client
from agenteval.orchestration.campaign import CampaignOrchestrator

logger = logging.getLogger(__name__)


class ReportNotFoundError(Exception):
    """Raised when report is not found"""

    pass


class ReportGenerationError(Exception):
    """Raised when report generation fails"""

    pass


class ReportService:
    """
    Report business logic service

    Provides high-level operations for report generation,
    storage, and retrieval.
    """

    def __init__(self, orchestrator: CampaignOrchestrator, s3_client: S3Client):
        """
        Initialize report service

        Args:
            orchestrator: Campaign orchestrator for data access
            s3_client: S3 client for report storage
        """
        self.orchestrator = orchestrator
        self.s3 = s3_client
        logger.debug("ReportService initialized")

    async def generate_campaign_report(
        self, campaign_id: str, report_format: str = "json"
    ) -> dict[str, Any]:
        """
        Generate and store campaign report

        Args:
            campaign_id: Campaign identifier
            report_format: Report format (json, csv, pdf, html)

        Returns:
            Dict with report metadata including download URLs

        Raises:
            ReportGenerationError: If report generation fails
        """
        try:
            # Validate format
            try:
                format_enum = ReportFormat(report_format.lower())
            except ValueError:
                valid_formats = [f.value for f in ReportFormat]
                raise ReportGenerationError(
                    f"Invalid report format '{report_format}'. "
                    f"Must be one of: {', '.join(valid_formats)}"
                )

            # Get campaign data
            campaign = await self.orchestrator.dynamodb.get_campaign(campaign_id)
            if not campaign:
                raise ReportGenerationError(f"Campaign not found: {campaign_id}")

            # Get turn results
            turns = await self.orchestrator.dynamodb.get_campaign_turns(campaign_id=campaign_id)

            # Build report data
            report_data = self._build_report_data(campaign, turns)

            # Generate and store report in requested format
            s3_uri, presigned_url = await self.s3.store_report(
                campaign_id=campaign_id, report_data=report_data, report_format=format_enum
            )

            logger.info(
                f"Report generated for campaign {campaign_id} in {report_format} format",
                extra={"campaign_id": campaign_id, "format": report_format, "s3_uri": s3_uri},
            )

            return {
                "campaign_id": campaign_id,
                "format": report_format,
                "s3_uri": s3_uri,
                "download_url": presigned_url,
                "generated_at": datetime.utcnow().isoformat(),
                "expires_at": self._calculate_expiry(24),  # 24 hours
            }

        except Exception as e:
            logger.error(
                f"Failed to generate report for campaign {campaign_id}: {e}", exc_info=True
            )
            raise ReportGenerationError(f"Failed to generate report: {str(e)}")

    def _build_report_data(
        self, campaign: dict[str, Any], turns: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Build comprehensive report data from campaign and turns

        Args:
            campaign: Campaign metadata
            turns: List of turn results

        Returns:
            Report data dictionary
        """
        # Extract turn results
        turn_results = []
        for turn in turns:
            turn_result = {
                "turn_number": turn.get("turn_number"),
                "turn_id": turn.get("turn_id"),
                "agent_type": turn.get("agent_type"),
                "user_message": turn.get("user_message"),
                "system_response": turn.get("system_response"),
                "timestamp": turn.get("timestamp"),
                "status": turn.get("status"),
            }

            # Add evaluation if present
            if "evaluation" in turn:
                turn_result["evaluation_result"] = turn["evaluation"]

            # Add correlation if present
            if "correlation" in turn:
                turn_result["correlation_analysis"] = turn["correlation"]

            # Add persona memory if present
            if "persona_memory" in turn:
                turn_result["persona_state"] = {
                    "frustration_level": turn["persona_memory"]
                    .get("state", {})
                    .get("frustration_level"),
                    "goal_progress": turn["persona_memory"].get("state", {}).get("goal_progress"),
                    "patience_level": turn["persona_memory"].get("state", {}).get("patience_level"),
                }

            turn_results.append(turn_result)

        # Calculate aggregate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(turns)

        # Build comprehensive report
        report = {
            "campaign_id": campaign["campaign_id"],
            "campaign_type": campaign["campaign_type"],
            "target_url": campaign.get("target_url"),
            "status": campaign["status"],
            "created_at": campaign["created_at"],
            "updated_at": campaign["updated_at"],
            "completed_at": campaign.get("completed_at"),
            "config": campaign.get("config", {}),
            "stats": campaign.get("stats", {}),
            "aggregate_metrics": aggregate_metrics,
            "turn_results": turn_results,
            "turns_completed": len(turns),
            "success_rate": aggregate_metrics.get("success_rate", 0.0),
        }

        return report

    def _calculate_aggregate_metrics(self, turns: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Calculate aggregate metrics from turn results

        Args:
            turns: List of turn results

        Returns:
            Aggregate metrics dictionary
        """
        if not turns:
            return {
                "overall_score": 0.0,
                "quality_score": 0.0,
                "safety_score": 0.0,
                "helpfulness_score": 0.0,
                "accuracy_score": 0.0,
                "success_rate": 0.0,
                "total_turns": 0,
                "completed_turns": 0,
                "failed_turns": 0,
            }

        # Extract scores
        overall_scores = []
        quality_scores = []
        safety_scores = []
        helpfulness_scores = []
        accuracy_scores = []
        completed_count = 0
        failed_count = 0

        for turn in turns:
            status = turn.get("status", "")
            if status == "completed":
                completed_count += 1
            elif status == "failed":
                failed_count += 1

            # Extract evaluation scores
            if "evaluation" in turn:
                eval_data = turn["evaluation"]
                if "aggregate_scores" in eval_data:
                    scores = eval_data["aggregate_scores"]
                    overall_scores.append(scores.get("overall", 0.0))
                    quality_scores.append(scores.get("quality", 0.0))
                    safety_scores.append(scores.get("safety", 0.0))
                    helpfulness_scores.append(scores.get("helpfulness", 0.0))
                    accuracy_scores.append(scores.get("accuracy", 0.0))

        # Calculate averages
        def avg(scores: list[float]) -> float:
            return sum(scores) / len(scores) if scores else 0.0

        total_turns = len(turns)
        success_rate = completed_count / total_turns if total_turns > 0 else 0.0

        return {
            "overall_score": avg(overall_scores),
            "quality_score": avg(quality_scores),
            "safety_score": avg(safety_scores),
            "helpfulness_score": avg(helpfulness_scores),
            "accuracy_score": avg(accuracy_scores),
            "success_rate": success_rate,
            "total_turns": total_turns,
            "completed_turns": completed_count,
            "failed_turns": failed_count,
        }

    def _calculate_expiry(self, hours: int = 24) -> str:
        """
        Calculate expiry timestamp

        Args:
            hours: Hours until expiry

        Returns:
            ISO format expiry timestamp
        """
        from datetime import timedelta

        expiry = datetime.utcnow() + timedelta(hours=hours)
        return expiry.isoformat()

    async def get_campaign_turns(
        self, campaign_id: str, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """
        Get turn results for a campaign

        Args:
            campaign_id: Campaign identifier
            limit: Maximum turns to return
            offset: Number of turns to skip

        Returns:
            Dict with turns and metadata
        """
        # Get campaign to verify it exists
        campaign = await self.orchestrator.dynamodb.get_campaign(campaign_id)
        if not campaign:
            raise ReportNotFoundError(f"Campaign not found: {campaign_id}")

        # Get turns with pagination
        turns = await self.orchestrator.dynamodb.get_campaign_turns(
            campaign_id=campaign_id, limit=limit, offset=offset
        )

        return {
            "campaign_id": campaign_id,
            "turns": turns,
            "total": len(turns),
            "limit": limit,
            "offset": offset,
        }

    async def get_turn_detail(self, campaign_id: str, turn_id: str) -> dict[str, Any]:
        """
        Get detailed information for a specific turn

        Args:
            campaign_id: Campaign identifier
            turn_id: Turn identifier

        Returns:
            Turn detail with all associated data

        Raises:
            ReportNotFoundError: If turn not found
        """
        turn = await self.orchestrator.dynamodb.get_turn(campaign_id=campaign_id, turn_id=turn_id)

        if not turn:
            raise ReportNotFoundError(f"Turn {turn_id} not found for campaign {campaign_id}")

        return turn

    async def get_campaign_summary(self, campaign_id: str) -> dict[str, Any]:
        """
        Get high-level campaign summary

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign summary with key metrics

        Raises:
            ReportNotFoundError: If campaign not found
        """
        # Get campaign
        campaign = await self.orchestrator.dynamodb.get_campaign(campaign_id)
        if not campaign:
            raise ReportNotFoundError(f"Campaign not found: {campaign_id}")

        # Get all turns
        turns = await self.orchestrator.dynamodb.get_campaign_turns(campaign_id=campaign_id)

        # Calculate metrics
        aggregate_metrics = self._calculate_aggregate_metrics(turns)

        return {
            "campaign_id": campaign_id,
            "campaign_type": campaign["campaign_type"],
            "status": campaign["status"],
            "created_at": campaign["created_at"],
            "updated_at": campaign["updated_at"],
            "config": campaign.get("config", {}),
            "metrics": aggregate_metrics,
            "turns_completed": len(turns),
        }

    async def get_campaign_correlations(self, campaign_id: str) -> dict[str, Any]:
        """
        Get all trace correlations for campaign

        Args:
            campaign_id: Campaign identifier

        Returns:
            Dict with correlations and root causes

        Raises:
            ReportNotFoundError: If campaign not found
        """
        # Get all turns
        turns = await self.orchestrator.dynamodb.get_campaign_turns(
            campaign_id=campaign_id, limit=1000
        )

        if not turns:
            raise ReportNotFoundError(f"No turns found for campaign: {campaign_id}")

        # Extract all correlations
        all_correlations = []
        all_root_causes = []

        for turn in turns:
            correlation = turn.get("correlation")
            if correlation:
                all_correlations.extend(correlation.get("correlations", []))
                all_root_causes.extend(correlation.get("root_causes", []))

        # Group root causes by issue
        root_cause_summary = {}
        for rc in all_root_causes:
            issue = rc["issue"]
            if issue not in root_cause_summary:
                root_cause_summary[issue] = {
                    "count": 0,
                    "avg_severity": 0.0,
                    "recommendations": set(),
                }

            root_cause_summary[issue]["count"] += 1
            root_cause_summary[issue]["avg_severity"] += rc["severity"]
            root_cause_summary[issue]["recommendations"].update(rc["recommendations"])

        # Calculate averages and convert sets to lists
        for issue_data in root_cause_summary.values():
            issue_data["avg_severity"] /= issue_data["count"]
            issue_data["recommendations"] = list(issue_data["recommendations"])

        return {
            "campaign_id": campaign_id,
            "total_correlations": len(all_correlations),
            "total_root_causes": len(all_root_causes),
            "root_cause_summary": root_cause_summary,
            "all_correlations": all_correlations[:50],  # Limit to first 50 for response size
        }

    async def get_campaign_recommendations(
        self, campaign_id: str, limit: int = 20
    ) -> dict[str, Any]:
        """
        Get actionable recommendations for improving the target system

        Args:
            campaign_id: Campaign identifier
            limit: Maximum number of recommendations to return

        Returns:
            Dict with prioritized recommendations

        Raises:
            ReportNotFoundError: If campaign not found
        """
        # Get all turns
        turns = await self.orchestrator.dynamodb.get_campaign_turns(
            campaign_id=campaign_id, limit=1000
        )

        if not turns:
            raise ReportNotFoundError(f"No turns found for campaign: {campaign_id}")

        # Extract all recommendations
        all_recommendations = []

        for turn in turns:
            correlation = turn.get("correlation")
            if correlation:
                recs = correlation.get("recommendations", [])
                all_recommendations.extend(recs)

        # Sort by priority and severity
        all_recommendations.sort(key=lambda r: (r.get("priority", 999), -r.get("severity", 0)))

        # Deduplicate while preserving order
        seen = set()
        unique_recommendations = []

        for rec in all_recommendations:
            rec_text = rec["recommendation"]
            if rec_text not in seen:
                seen.add(rec_text)
                unique_recommendations.append(rec)

        return {
            "campaign_id": campaign_id,
            "total_recommendations": len(unique_recommendations),
            "recommendations": unique_recommendations[:limit],
        }
