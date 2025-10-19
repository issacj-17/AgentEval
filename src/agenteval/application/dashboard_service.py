"""
Dashboard Service for AgentEval.

This module provides a high-level orchestration service for generating
comprehensive evaluation dashboards (HTML + Markdown).

Design Patterns:
    - Facade Pattern: Simplifies complex subsystem interactions
    - Dependency Injection: Loosely coupled dependencies
    - Strategy Pattern: Different output formats (HTML, Markdown)
    - Template Method: Dashboard generation workflow

SOLID Principles:
    - SRP: Single responsibility of orchestrating dashboard generation
    - OCP: Open for extension (new report formats)
    - LSP: Substitutable report generators
    - ISP: Clean dashboard interface
    - DIP: Depends on abstractions (services, not implementations)
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from agenteval.application.results_service import (
    ResultsBundle,
    ResultsService,
)
from agenteval.reporting.html_renderer import (
    CampaignContext,
    CampaignSummary,
    DashboardContext,
    HTMLRenderer,
    MetricSummary,
    SummaryContext,
    TurnDetail,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class DashboardServiceError(Exception):
    """Base exception for dashboard service errors."""

    pass


class DataTransformationError(DashboardServiceError):
    """Raised when data transformation fails."""

    pass


class DashboardGenerationError(DashboardServiceError):
    """Raised when dashboard generation fails."""

    pass


# ============================================================================
# Dashboard Service
# ============================================================================


@dataclass
class DashboardConfig:
    """Configuration for dashboard generation."""

    region: str = "us-east-1"
    environment: str = "development"
    output_dir: Path | None = None
    generate_html: bool = True
    generate_markdown: bool = True
    campaign_ids: list[str] | None = None


class DashboardService:
    """
    Facade service for generating comprehensive evaluation dashboards.

    This service orchestrates:
    1. Pulling results from AWS (via ResultsService)
    2. Transforming data into presentation formats
    3. Rendering HTML dashboards (via HTMLRenderer)
    4. Generating markdown reports

    Attributes:
        results_service: Service for pulling AWS results
        html_renderer: Service for rendering HTML templates
        config: Dashboard configuration
    """

    def __init__(
        self,
        results_service: ResultsService,
        html_renderer: HTMLRenderer,
        config: DashboardConfig | None = None,
    ):
        """
        Initialize DashboardService with dependency injection.

        Args:
            results_service: Service for pulling results
            html_renderer: Service for rendering HTML
            config: Dashboard configuration
        """
        self.results_service = results_service
        self.html_renderer = html_renderer
        self.config = config or DashboardConfig()

        logger.info("DashboardService initialized")

    # ========================================================================
    # Main Orchestration Methods
    # ========================================================================

    async def generate_dashboard(
        self,
        campaign_ids: list[str] | None = None,
    ) -> dict[str, Path]:
        """
        Generate complete dashboard (HTML + Markdown).

        This is the main facade method that orchestrates the entire
        dashboard generation workflow.

        Args:
            campaign_ids: Optional list of campaign IDs to include

        Returns:
            Dictionary mapping report type to file path

        Raises:
            DashboardGenerationError: If generation fails
        """
        try:
            logger.info("Starting dashboard generation...")

            # Step 1: Pull results from AWS
            results = await self._pull_results(campaign_ids)

            # Step 2: Transform data for presentation
            dashboard_ctx = self._build_dashboard_context(results)
            campaign_contexts = self._build_campaign_contexts(results)
            summary_ctx = self._build_summary_context(results)

            # Step 3: Render outputs
            output_files = {}

            if self.config.generate_html:
                html_files = await self._generate_html_reports(
                    dashboard_ctx, campaign_contexts, summary_ctx
                )
                output_files.update(html_files)

            if self.config.generate_markdown:
                md_files = await self._generate_markdown_reports(results)
                output_files.update(md_files)

            logger.info(f"Dashboard generation complete. Generated {len(output_files)} files")
            return output_files

        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}")
            raise DashboardGenerationError(f"Generation failed: {e}") from e

    # ========================================================================
    # Data Pulling
    # ========================================================================

    async def _pull_results(self, campaign_ids: list[str] | None = None) -> ResultsBundle:
        """
        Pull results from AWS.

        Args:
            campaign_ids: Optional campaign IDs filter

        Returns:
            Results bundle with all data
        """
        logger.info("Pulling results from AWS...")
        results = await self.results_service.pull_all_results(
            region=self.config.region,
            campaign_ids=campaign_ids or self.config.campaign_ids,
        )
        logger.info(
            f"Pulled {len(results.campaign_data.campaigns)} campaigns, "
            f"{len(results.campaign_data.turns)} turns, "
            f"{len(results.campaign_data.evaluations)} evaluations"
        )
        return results

    # ========================================================================
    # Data Transformation - Dashboard Context
    # ========================================================================

    def _build_dashboard_context(self, results: ResultsBundle) -> DashboardContext:
        """
        Build dashboard context from results bundle.

        Args:
            results: Results bundle

        Returns:
            Dashboard context for template rendering
        """
        logger.debug("Building dashboard context...")

        campaigns = results.campaign_data.campaigns
        turns = results.campaign_data.turns
        evaluations = results.campaign_data.evaluations

        # Calculate statistics
        total_campaigns = len(campaigns)
        total_turns = len(turns)
        completed_turns = sum(1 for t in turns if t.get("status") == "completed")
        failed_turns = total_turns - completed_turns

        # Calculate overall score
        scores = [e.get("score", 0.0) for e in evaluations]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Success rate
        success_rate = completed_turns / total_turns if total_turns > 0 else 0.0

        # Total evaluations and unique metrics
        total_evaluations = len(evaluations)
        unique_metrics = set()
        for eval_data in evaluations:
            metrics = eval_data.get("metrics", {})
            unique_metrics.update(metrics.keys())
        total_metrics = len(unique_metrics)

        # Build campaign summaries
        campaign_summaries = [
            self._build_campaign_summary(c, turns, evaluations) for c in campaigns
        ]

        # Build chart data
        chart_data = self._build_dashboard_chart_data(campaigns, turns, evaluations)

        return DashboardContext(
            title="AgentEval Dashboard",
            subtitle="Comprehensive Multi-Agent Evaluation Results",
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            region=self.config.region,
            environment=self.config.environment,
            total_campaigns=total_campaigns,
            overall_score=overall_score,
            total_turns=total_turns,
            completed_turns=completed_turns,
            failed_turns=failed_turns,
            success_rate=success_rate,
            total_evaluations=total_evaluations,
            total_metrics=total_metrics,
            campaigns=campaign_summaries,
            **chart_data,
        )

    def _build_campaign_summary(
        self,
        campaign: dict[str, Any],
        turns: list[dict[str, Any]],
        evaluations: list[dict[str, Any]],
    ) -> CampaignSummary:
        """
        Build campaign summary from raw data.

        Args:
            campaign: Campaign data
            turns: All turns
            evaluations: All evaluations

        Returns:
            Campaign summary
        """
        campaign_id = campaign.get("campaign_id")

        # Filter turns for this campaign
        campaign_turns = [t for t in turns if t.get("campaign_id") == campaign_id]
        completed = sum(1 for t in campaign_turns if t.get("status") == "completed")
        total = len(campaign_turns)

        # Calculate score from evaluations
        campaign_evals = [e for e in evaluations if e.get("campaign_id") == campaign_id]
        scores = [e.get("score", 0.0) for e in campaign_evals]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        # Calculate duration
        start_time = campaign.get("created_at", "")
        end_time = campaign.get("updated_at", start_time)
        duration = self._calculate_duration(start_time, end_time)

        return CampaignSummary(
            id=campaign_id,
            type=campaign.get("campaign_type", "unknown"),
            status=campaign.get("status", "unknown"),
            status_class=self.html_renderer.calculate_status_class(
                campaign.get("status", "unknown")
            ),
            score=avg_score,
            score_class=self.html_renderer.calculate_score_class(avg_score),
            completed_turns=completed,
            total_turns=total,
            duration=duration,
            created_at=self._format_datetime(start_time),
        )

    def _build_dashboard_chart_data(
        self,
        campaigns: list[dict[str, Any]],
        turns: list[dict[str, Any]],
        evaluations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Build chart data for dashboard.

        Args:
            campaigns: Campaign data
            turns: Turn data
            evaluations: Evaluation data

        Returns:
            Dictionary with chart data arrays
        """
        # Campaign scores chart
        campaign_labels = [c.get("campaign_id", "")[:8] for c in campaigns]
        campaign_scores = []
        for campaign in campaigns:
            campaign_id = campaign.get("campaign_id")
            campaign_evals = [e for e in evaluations if e.get("campaign_id") == campaign_id]
            scores = [e.get("score", 0.0) for e in campaign_evals]
            avg = (sum(scores) / len(scores) * 100) if scores else 0.0
            campaign_scores.append(round(avg, 1))

        # Campaign types distribution
        type_counter = Counter(c.get("campaign_type", "unknown") for c in campaigns)
        campaign_type_labels = list(type_counter.keys())
        campaign_type_counts = list(type_counter.values())

        # Metric performance
        metric_scores_dict: dict[str, list[float]] = defaultdict(list)
        for eval_data in evaluations:
            metrics = eval_data.get("metrics", {})
            for metric_name, metric_value in metrics.items():
                metric_scores_dict[metric_name].append(metric_value)

        metric_labels = list(metric_scores_dict.keys())
        metric_scores = [
            round(sum(scores) / len(scores) * 100, 1) for scores in metric_scores_dict.values()
        ]

        # Turn completion trend (by campaign)
        turn_trend_labels = campaign_labels
        turn_trend_completed = []
        turn_trend_failed = []
        for campaign in campaigns:
            campaign_id = campaign.get("campaign_id")
            campaign_turns = [t for t in turns if t.get("campaign_id") == campaign_id]
            completed = sum(1 for t in campaign_turns if t.get("status") == "completed")
            failed = len(campaign_turns) - completed
            turn_trend_completed.append(completed)
            turn_trend_failed.append(failed)

        return {
            "campaign_labels": campaign_labels,
            "campaign_scores": campaign_scores,
            "campaign_type_labels": campaign_type_labels,
            "campaign_type_counts": campaign_type_counts,
            "metric_labels": metric_labels,
            "metric_scores": metric_scores,
            "turn_trend_labels": turn_trend_labels,
            "turn_trend_completed": turn_trend_completed,
            "turn_trend_failed": turn_trend_failed,
        }

    # ========================================================================
    # Data Transformation - Campaign Contexts
    # ========================================================================

    def _build_campaign_contexts(self, results: ResultsBundle) -> list[CampaignContext]:
        """
        Build campaign contexts for all campaigns.

        Args:
            results: Results bundle

        Returns:
            List of campaign contexts
        """
        logger.debug("Building campaign contexts...")

        contexts = []
        for campaign in results.campaign_data.campaigns:
            try:
                context = self._build_single_campaign_context(campaign, results)
                contexts.append(context)
            except Exception as e:
                campaign_id = campaign.get("campaign_id", "unknown")
                logger.error(f"Failed to build context for campaign {campaign_id}: {e}")

        return contexts

    def _build_single_campaign_context(
        self, campaign: dict[str, Any], results: ResultsBundle
    ) -> CampaignContext:
        """
        Build campaign context for a single campaign.

        Args:
            campaign: Campaign data
            results: Full results bundle

        Returns:
            Campaign context
        """
        campaign_id = campaign.get("campaign_id")

        # Filter data for this campaign
        turns = [t for t in results.campaign_data.turns if t.get("campaign_id") == campaign_id]
        evaluations = [
            e for e in results.campaign_data.evaluations if e.get("campaign_id") == campaign_id
        ]

        # Calculate metrics
        completed = sum(1 for t in turns if t.get("status") == "completed")
        scores = [e.get("score", 0.0) for e in evaluations]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Duration
        start_time = campaign.get("created_at", "")
        end_time = campaign.get("updated_at", start_time)
        duration = self._calculate_duration(start_time, end_time)

        # Build metric summaries
        metric_summaries = self._calculate_metric_summaries(evaluations)

        # Build turn details
        turn_details = self._build_turn_details(turns, evaluations)

        # Build chart data
        chart_data = self._build_campaign_chart_data(metric_summaries, turn_details)

        return CampaignContext(
            campaign_id=campaign_id,
            campaign_type=campaign.get("campaign_type", "unknown"),
            status=campaign.get("status", "unknown"),
            status_class=self.html_renderer.calculate_status_class(
                campaign.get("status", "unknown")
            ),
            overall_score=overall_score,
            completed_turns=completed,
            total_turns=len(turns),
            duration=duration,
            created_at=self._format_datetime(start_time),
            region=self.config.region,
            metrics=metric_summaries,
            turns=turn_details,
            **chart_data,
        )

    def _calculate_metric_summaries(self, evaluations: list[dict[str, Any]]) -> list[MetricSummary]:
        """
        Calculate metric summaries from evaluations.

        Args:
            evaluations: Evaluation data

        Returns:
            List of metric summaries
        """
        metric_scores_dict: dict[str, list[float]] = defaultdict(list)

        for eval_data in evaluations:
            metrics = eval_data.get("metrics", {})
            for metric_name, metric_value in metrics.items():
                metric_scores_dict[metric_name].append(metric_value)

        summaries = []
        for metric_name, scores in metric_scores_dict.items():
            avg_score = sum(scores) / len(scores) if scores else 0.0
            summaries.append(
                MetricSummary(
                    name=metric_name,
                    score=avg_score,
                    score_class=self.html_renderer.calculate_score_class(avg_score),
                )
            )

        return summaries

    def _build_turn_details(
        self,
        turns: list[dict[str, Any]],
        evaluations: list[dict[str, Any]],
    ) -> list[TurnDetail]:
        """
        Build turn details from turn and evaluation data.

        Args:
            turns: Turn data
            evaluations: Evaluation data

        Returns:
            List of turn details
        """
        details = []
        for turn in turns:
            turn_number = turn.get("turn_number", 0)

            # Find evaluation for this turn
            turn_evals = [e for e in evaluations if e.get("turn_number") == turn_number]
            score = turn_evals[0].get("score", 0.0) if turn_evals else 0.0

            # Build metric summaries for this turn
            turn_metrics = []
            if turn_evals:
                metrics = turn_evals[0].get("metrics", {})
                for name, value in metrics.items():
                    turn_metrics.append(
                        MetricSummary(
                            name=name,
                            score=value,
                            score_class=self.html_renderer.calculate_score_class(value),
                        )
                    )

            details.append(
                TurnDetail(
                    number=turn_number,
                    status=turn.get("status", "unknown"),
                    status_class=self.html_renderer.calculate_status_class(
                        turn.get("status", "unknown")
                    ),
                    score=score,
                    user_message=turn.get("user_message", ""),
                    system_response=turn.get("system_response", ""),
                    metrics=turn_metrics,
                    trace_id=turn.get("trace_id"),
                )
            )

        return details

    def _build_campaign_chart_data(
        self,
        metrics: list[MetricSummary],
        turns: list[TurnDetail],
    ) -> dict[str, Any]:
        """
        Build chart data for campaign detail page.

        Args:
            metrics: Metric summaries
            turns: Turn details

        Returns:
            Dictionary with chart data
        """
        metric_labels = [m.name for m in metrics]
        metric_scores = [round(m.score * 100, 1) for m in metrics]

        turn_labels = [f"Turn {t.number}" for t in turns]
        turn_scores = [round(t.score * 100, 1) for t in turns]

        return {
            "metric_labels": metric_labels,
            "metric_scores": metric_scores,
            "turn_labels": turn_labels,
            "turn_scores": turn_scores,
        }

    # ========================================================================
    # Data Transformation - Summary Context
    # ========================================================================

    def _build_summary_context(self, results: ResultsBundle) -> SummaryContext:
        """
        Build executive summary context.

        Args:
            results: Results bundle

        Returns:
            Summary context
        """
        logger.debug("Building summary context...")

        campaigns = results.campaign_data.campaigns
        turns = results.campaign_data.turns
        evaluations = results.campaign_data.evaluations

        # Statistics
        total_campaigns = len(campaigns)
        total_turns = len(turns)
        completed_turns = sum(1 for t in turns if t.get("status") == "completed")
        failed_turns = total_turns - completed_turns

        scores = [e.get("score", 0.0) for e in evaluations]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        success_rate = completed_turns / total_turns if total_turns > 0 else 0.0

        # Evaluation period
        if campaigns:
            start_dates = [c.get("created_at", "") for c in campaigns]
            end_dates = [c.get("updated_at", "") for c in campaigns]
            evaluation_period = f"{min(start_dates)[:10]} to {max(end_dates)[:10]}"
        else:
            evaluation_period = "N/A"

        # Status assessment
        if overall_score >= 0.8:
            overall_status = "Excellent"
            overall_status_class = "success"
            performance_assessment = (
                "excellent system performance with strong capabilities across all dimensions"
            )
        elif overall_score >= 0.6:
            overall_status = "Good"
            overall_status_class = "info"
            performance_assessment = (
                "good system performance with opportunities for targeted improvements"
            )
        else:
            overall_status = "Needs Improvement"
            overall_status_class = "warning"
            performance_assessment = (
                "system performance requiring attention and improvement efforts"
            )

        # Generate recommendations
        recommendations = self._generate_recommendations(results, overall_score, failed_turns)

        # Unique metrics
        unique_metrics = set()
        for eval_data in evaluations:
            metrics = eval_data.get("metrics", {})
            unique_metrics.update(metrics.keys())

        return SummaryContext(
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            evaluation_period=evaluation_period,
            total_campaigns=total_campaigns,
            region=self.config.region,
            overview_text=(
                "This report presents a comprehensive analysis of the AgentEval "
                "multi-agent evaluation system's performance. The evaluation framework "
                "tested conversational AI systems using simulated user personas, red team "
                "adversarial testing, and automated quality assessment across multiple "
                "dimensions including accuracy, safety, and user experience."
            ),
            overall_score=overall_score,
            overall_status=overall_status,
            overall_status_class=overall_status_class,
            performance_assessment=performance_assessment,
            total_turns=total_turns,
            completed_turns=completed_turns,
            failed_turns=failed_turns,
            success_rate=success_rate,
            total_evaluations=len(evaluations),
            total_metrics=len(unique_metrics),
            recommendations=recommendations,
            conclusion_text=(
                "The evaluation results demonstrate strong foundational performance "
                "with clear opportunities for enhancement. We recommend addressing the "
                "identified areas for improvement and conducting follow-up evaluations "
                "to measure progress. Continue monitoring system performance and iterating "
                "based on real-world feedback."
            ),
        )

    def _generate_recommendations(
        self, results: ResultsBundle, overall_score: float, failed_turns: int
    ) -> list[dict[str, str]]:
        """
        Generate recommendations based on results.

        Args:
            results: Results bundle
            overall_score: Overall quality score
            failed_turns: Number of failed turns

        Returns:
            List of recommendations
        """
        recommendations = []

        # Recommendation based on overall score
        if overall_score < 0.8:
            recommendations.append(
                {
                    "title": "Enhance Response Quality",
                    "text": (
                        "Focus on improving overall response quality by analyzing "
                        "low-scoring interactions and refining system prompts. "
                        "Consider implementing additional quality checks and "
                        "response validation mechanisms."
                    ),
                }
            )

        # Recommendation based on failures
        if failed_turns > 0:
            recommendations.append(
                {
                    "title": "Investigate Failed Conversations",
                    "text": (
                        f"Investigate the {failed_turns} failed conversation turns "
                        "to identify root causes. Common issues may include timeout "
                        "errors, API failures, or input validation problems. Implement "
                        "appropriate error handling and retry mechanisms."
                    ),
                }
            )

        # Metric-specific recommendations
        evaluations = results.campaign_data.evaluations
        if evaluations:
            metric_scores_dict: dict[str, list[float]] = defaultdict(list)
            for eval_data in evaluations:
                metrics = eval_data.get("metrics", {})
                for name, value in metrics.items():
                    metric_scores_dict[name].append(value)

            low_metrics = [
                (name, sum(scores) / len(scores))
                for name, scores in metric_scores_dict.items()
                if (sum(scores) / len(scores)) < 0.7
            ]

            if low_metrics:
                metric_names = ", ".join(name for name, _ in low_metrics)
                recommendations.append(
                    {
                        "title": "Target Low-Scoring Metrics",
                        "text": (
                            f"Focus improvement efforts on: {metric_names}. "
                            "Analyze specific examples where these metrics scored "
                            "poorly and develop targeted strategies to address "
                            "identified weaknesses."
                        ),
                    }
                )

        # Always include monitoring recommendation
        recommendations.append(
            {
                "title": "Continuous Monitoring",
                "text": (
                    "Establish continuous monitoring and regular evaluation cycles. "
                    "Track improvements over time and adjust strategies based on "
                    "observed trends. Consider implementing automated alerts for "
                    "performance degradation."
                ),
            }
        )

        return recommendations

    # ========================================================================
    # HTML Generation
    # ========================================================================

    async def _generate_html_reports(
        self,
        dashboard_ctx: DashboardContext,
        campaign_contexts: list[CampaignContext],
        summary_ctx: SummaryContext,
    ) -> dict[str, Path]:
        """
        Generate all HTML reports.

        Args:
            dashboard_ctx: Dashboard context
            campaign_contexts: Campaign contexts
            summary_ctx: Summary context

        Returns:
            Dictionary mapping report type to file path
        """
        logger.info("Generating HTML reports...")

        output_files = {}

        # Generate dashboard
        dashboard_path = self.html_renderer.render_dashboard(dashboard_ctx)
        output_files["html_dashboard"] = dashboard_path

        # Generate campaign details
        for context in campaign_contexts:
            campaign_path = self.html_renderer.render_campaign_detail(context)
            output_files[f"html_campaign_{context.campaign_id}"] = campaign_path

        # Generate summary
        summary_path = self.html_renderer.render_summary(summary_ctx)
        output_files["html_summary"] = summary_path

        logger.info(f"Generated {len(output_files)} HTML reports")
        return output_files

    # ========================================================================
    # Markdown Generation (Compatibility)
    # ========================================================================

    async def _generate_markdown_reports(self, results: ResultsBundle) -> dict[str, Path]:
        """
        Generate markdown reports for compatibility.

        Args:
            results: Results bundle

        Returns:
            Dictionary mapping report type to file path
        """
        logger.info("Generating markdown reports...")

        output_dir = self.config.output_dir or Path("demo/evidence/reports")
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate simple markdown summary
        md_content = self._generate_markdown_summary(results)
        md_path = output_dir / "SUMMARY.md"
        md_path.write_text(md_content, encoding="utf-8")

        logger.info(f"Generated markdown report: {md_path}")
        return {"markdown_summary": md_path}

    def _generate_markdown_summary(self, results: ResultsBundle) -> str:
        """
        Generate markdown summary content.

        Args:
            results: Results bundle

        Returns:
            Markdown content
        """
        campaigns = results.campaign_data.campaigns
        turns = results.campaign_data.turns
        evaluations = results.campaign_data.evaluations

        scores = [e.get("score", 0.0) for e in evaluations]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        md = f"""# AgentEval Results Summary

**Generated**: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
**Region**: {self.config.region}

## Overview

- **Total Campaigns**: {len(campaigns)}
- **Total Turns**: {len(turns)}
- **Total Evaluations**: {len(evaluations)}
- **Overall Score**: {overall_score * 100:.1f}%

## Campaigns

"""

        for campaign in campaigns:
            campaign_id = campaign.get("campaign_id")
            campaign_type = campaign.get("campaign_type", "unknown")
            status = campaign.get("status", "unknown")

            campaign_turns = [t for t in turns if t.get("campaign_id") == campaign_id]
            campaign_evals = [e for e in evaluations if e.get("campaign_id") == campaign_id]

            campaign_scores = [e.get("score", 0.0) for e in campaign_evals]
            campaign_avg = sum(campaign_scores) / len(campaign_scores) if campaign_scores else 0.0

            md += f"""### Campaign: {campaign_id[:8]}

- **Type**: {campaign_type}
- **Status**: {status}
- **Turns**: {len(campaign_turns)}
- **Average Score**: {campaign_avg * 100:.1f}%

"""

        md += """
## Next Steps

1. Review detailed HTML dashboard for comprehensive analysis
2. Investigate any low-scoring interactions
3. Address identified improvement areas
4. Continue monitoring system performance

---

*Generated by AgentEval - AWS AI Agent Global Hackathon 2025*
"""

        return md

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _calculate_duration(self, start: str, end: str) -> str:
        """
        Calculate duration between timestamps.

        Args:
            start: Start timestamp
            end: End timestamp

        Returns:
            Formatted duration string
        """
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            delta = end_dt - start_dt
            return self.html_renderer.format_duration(delta.total_seconds())
        except (ValueError, AttributeError):
            return "N/A"

    def _format_datetime(self, dt_str: str) -> str:
        """
        Format datetime string.

        Args:
            dt_str: Datetime string

        Returns:
            Formatted datetime
        """
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d %H:%M")
        except (ValueError, AttributeError):
            return dt_str[:16] if len(dt_str) >= 16 else dt_str


# ============================================================================
# Factory Function
# ============================================================================


async def create_dashboard_service(
    config: DashboardConfig | None = None,
) -> DashboardService:
    """
    Factory function for creating DashboardService instances.

    Args:
        config: Dashboard configuration

    Returns:
        Configured DashboardService instance
    """
    from agenteval.application.results_service import create_results_service
    from agenteval.reporting.html_renderer import create_html_renderer

    results_service = await create_results_service()
    html_renderer = create_html_renderer()

    return DashboardService(
        results_service=results_service,
        html_renderer=html_renderer,
        config=config,
    )
