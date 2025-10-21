"""
Report Consolidator Service.

Orchestrates report generation using Reporter Agent and formats output
as comprehensive markdown documents.

Design Patterns:
    - Facade Pattern: Simplifies report generation workflow
    - Dependency Injection: Loosely coupled dependencies
    - Template Method: Report formatting workflow
"""

import logging
from dataclasses import dataclass
from pathlib import Path

from agenteval.agents.reporter_agent import (
    GeneratedReport,
    ReportContext,
    ReporterAgent,
)
from agenteval.application.results_service import ResultsBundle

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class ReportConsolidatorError(Exception):
    """Base exception for report consolidator errors."""

    pass


class ReportGenerationError(ReportConsolidatorError):
    """Raised when report generation fails."""

    pass


# ============================================================================
# Configuration
# ============================================================================


@dataclass
class ConsolidatorConfig:
    """Configuration for report consolidator."""

    output_dir: Path
    report_type: str = "comprehensive"  # comprehensive, summary, technical
    include_html_link: bool = True
    include_raw_data: bool = False
    model_id: str = "anthropic.claude-haiku-4-5-20251001-v1:0"


# ============================================================================
# Report Consolidator Service
# ============================================================================


class ReportConsolidator:
    """
    Service for consolidating evaluation results into markdown reports.

    This service:
    1. Takes ResultsBundle as input
    2. Transforms data into ReportContext
    3. Uses Reporter Agent to generate insights
    4. Formats output as comprehensive markdown
    5. Saves to disk

    Attributes:
        reporter_agent: Agent for generating report content
        config: Consolidator configuration
    """

    def __init__(
        self,
        reporter_agent: ReporterAgent,
        config: ConsolidatorConfig,
    ):
        """
        Initialize ReportConsolidator.

        Args:
            reporter_agent: Reporter agent instance
            config: Consolidator configuration
        """
        self.reporter_agent = reporter_agent
        self.config = config

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ReportConsolidator initialized (output: {config.output_dir})")

    # ========================================================================
    # Main Orchestration
    # ========================================================================

    async def consolidate_reports(
        self, results: ResultsBundle, output_filename: str = "REPORT.md"
    ) -> Path:
        """
        Consolidate results into a comprehensive markdown report.

        Args:
            results: Results bundle from AWS
            output_filename: Output markdown filename

        Returns:
            Path to generated report file

        Raises:
            ReportGenerationError: If generation fails
        """
        try:
            logger.info("Starting report consolidation...")

            # Transform results into report context
            context = self._build_report_context(results)

            # Generate report using Reporter Agent
            generated_report = await self.reporter_agent.execute(
                report_context=context,
                report_type=self.config.report_type,
            )

            # Format as markdown
            markdown_content = self._format_as_markdown(generated_report, results)

            # Save to file
            output_path = self.config.output_dir / output_filename
            output_path.write_text(markdown_content, encoding="utf-8")

            logger.info(f"Report consolidated successfully: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Report consolidation failed: {e}")
            raise ReportGenerationError(f"Failed to consolidate: {e}") from e

    # ========================================================================
    # Data Transformation
    # ========================================================================

    def _build_report_context(self, results: ResultsBundle) -> ReportContext:
        """
        Build ReportContext from ResultsBundle.

        Args:
            results: Results bundle

        Returns:
            Report context for agent
        """
        campaign_data = results.campaign_data.campaigns
        turn_data = results.campaign_data.turns
        evaluation_data = results.campaign_data.evaluations

        # Determine time range
        timestamps = []
        for campaign in campaign_data:
            if created := campaign.get("created_at"):
                timestamps.append(created)
            if updated := campaign.get("updated_at"):
                timestamps.append(updated)

        time_range = {
            "start": min(timestamps) if timestamps else "N/A",
            "end": max(timestamps) if timestamps else "N/A",
        }

        return ReportContext(
            campaign_data=campaign_data,
            turn_data=turn_data,
            evaluation_data=evaluation_data,
            time_range=time_range,
            region=results.region,
        )

    # ========================================================================
    # Markdown Formatting
    # ========================================================================

    def _format_as_markdown(self, report: GeneratedReport, results: ResultsBundle) -> str:
        """
        Format generated report as markdown.

        Args:
            report: Generated report from Reporter Agent
            results: Original results bundle

        Returns:
            Formatted markdown content
        """
        md = f"""# AgentEval Evaluation Report

**Generated**: {report.generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Report Type**: {self.config.report_type.title()}
**Region**: {results.region}
**Agent**: {report.metadata.get("agent_id", "N/A")}

---

## Executive Summary

{report.executive_summary}

---

## Key Findings

"""

        for idx, finding in enumerate(report.key_findings, 1):
            md += f"{idx}. {finding}\n"

        md += "\n---\n\n## Recommendations\n\n"

        for idx, recommendation in enumerate(report.recommendations, 1):
            md += f"{idx}. {recommendation}\n"

        md += "\n---\n\n## Detailed Analysis\n\n"
        md += report.detailed_analysis

        # Add report sections
        if report.sections:
            md += "\n\n---\n\n## Additional Sections\n\n"
            for section in sorted(report.sections, key=lambda s: s.priority, reverse=True):
                md += f"### {section.title}\n\n"
                md += f"{section.content}\n\n"

        # Add statistics
        md += "\n---\n\n## Statistics Summary\n\n"
        stats = report.metadata.get("statistics", {})
        md += self._format_statistics_table(stats)

        # Add HTML link if configured
        if self.config.include_html_link:
            md += "\n---\n\n## Interactive Dashboard\n\n"
            md += (
                "For interactive visualizations and detailed exploration, "
                "view the HTML dashboard:\n\n"
            )
            md += "```\nopen reports/dashboard.html\n```\n"

        # Add footer
        md += "\n---\n\n"
        md += "_Report generated by **AgentEval Reporter Agent**_\n"
        md += "_Powered by Amazon Bedrock + OpenTelemetry_\n"

        return md

    def _format_statistics_table(self, stats: dict) -> str:
        """Format statistics as markdown table."""
        if not stats:
            return "_No statistics available_\n"

        md = "| Metric | Value |\n|--------|-------|\n"

        # Key statistics
        key_stats = [
            ("Total Campaigns", "total_campaigns"),
            ("Total Turns", "total_turns"),
            ("Completed Turns", "completed_turns"),
            ("Failed Turns", "failed_turns"),
            ("Success Rate", "success_rate"),
            ("Average Score", "avg_score"),
        ]

        for label, key in key_stats:
            if key in stats:
                value = stats[key]
                if isinstance(value, float):
                    if key in ["success_rate", "avg_score"]:
                        formatted = f"{value * 100:.1f}%"
                    else:
                        formatted = f"{value:.2f}"
                else:
                    formatted = str(value)
                md += f"| {label} | {formatted} |\n"

        return md

    # ========================================================================
    # Quick Summary Generation
    # ========================================================================

    async def generate_quick_summary(self, results: ResultsBundle) -> str:
        """
        Generate quick text summary without full report.

        Args:
            results: Results bundle

        Returns:
            Quick summary string
        """
        context = self._build_report_context(results)
        stats = self.reporter_agent._calculate_statistics(context)

        summary = f"""AgentEval Quick Summary
=====================

Campaigns: {stats["total_campaigns"]}
Turns: {stats["total_turns"]} ({stats["completed_turns"]} completed)
Success Rate: {stats["success_rate"] * 100:.1f}%
Average Score: {stats["avg_score"] * 100:.1f}%

Top Performing Metrics:
"""

        # Sort metrics by score
        sorted_metrics = sorted(
            stats["metric_averages"].items(),
            key=lambda x: x[1],
            reverse=True,
        )

        for name, score in sorted_metrics[:5]:
            summary += f"  - {name}: {score * 100:.1f}%\n"

        return summary


# ============================================================================
# Factory Function
# ============================================================================


async def create_report_consolidator(
    output_dir: Path | None = None,
    report_type: str = "comprehensive",
    model_id: str = "anthropic.claude-haiku-4-5-20251001-v1:0",
) -> ReportConsolidator:
    """
    Factory function for creating ReportConsolidator instances.

    Args:
        output_dir: Output directory for reports
        report_type: Type of report to generate
        model_id: Bedrock model ID

    Returns:
        Configured ReportConsolidator instance
    """
    from agenteval.config import settings

    # Create Reporter Agent
    reporter_agent = ReporterAgent(model_id=model_id)
    await reporter_agent.initialize()

    # Create configuration
    config = ConsolidatorConfig(
        output_dir=output_dir or Path(settings.app.evidence_report_output_dir) / "reports",
        report_type=report_type,
        model_id=model_id,
    )

    return ReportConsolidator(
        reporter_agent=reporter_agent,
        config=config,
    )
