"""
Reporter Agent - Consolidates evaluation results into comprehensive reports.

This agent analyzes evaluation data and generates executive summaries,
insights, and recommendations using LLM-powered analysis.

Design Patterns:
    - Template Method: Report generation workflow
    - Strategy Pattern: Different report formats
    - Builder Pattern: Building complex report structures
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from agenteval.agents.base import BaseAgent
from agenteval.observability.tracer import trace_operation

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ReportSection:
    """A section in the generated report."""

    title: str
    content: str
    priority: int = 5  # 1-10, higher = more important
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportContext:
    """Context data for report generation."""

    campaign_data: list[dict[str, Any]]
    turn_data: list[dict[str, Any]]
    evaluation_data: list[dict[str, Any]]
    time_range: dict[str, str]
    region: str = "us-east-1"
    environment: str = "development"


@dataclass
class GeneratedReport:
    """Generated report output."""

    executive_summary: str
    key_findings: list[str]
    recommendations: list[str]
    detailed_analysis: str
    sections: list[ReportSection]
    metadata: dict[str, Any]
    generated_at: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# Reporter Agent
# ============================================================================


class ReporterAgent(BaseAgent):
    """
    Reporter Agent for generating comprehensive evaluation reports.

    This agent uses LLM to analyze evaluation results and generate:
    - Executive summaries
    - Key findings and insights
    - Actionable recommendations
    - Detailed analysis sections

    Attributes:
        model_id: Bedrock model for report generation
        max_tokens: Maximum tokens for LLM generation
        temperature: LLM temperature setting
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-haiku-4-5-20251001-v1:0",
        max_tokens: int = 4000,
        temperature: float = 0.3,  # Lower temp for factual reporting
        agent_id: str | None = None,
    ):
        """
        Initialize Reporter Agent.

        Args:
            model_id: Bedrock model ID for report generation
            max_tokens: Maximum tokens for generation
            temperature: LLM temperature (lower = more factual)
            agent_id: Optional agent identifier
        """
        super().__init__(agent_id=agent_id, agent_type="reporter")
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature

        logger.info(
            f"ReporterAgent initialized (model: {model_id}, "
            f"max_tokens: {max_tokens}, temp: {temperature})"
        )

    # ========================================================================
    # Main Execution Method
    # ========================================================================

    async def execute(
        self,
        report_context: ReportContext,
        report_type: str = "comprehensive",
    ) -> GeneratedReport:
        """
        Generate evaluation report from context data.

        Args:
            report_context: Context with evaluation data
            report_type: Type of report (comprehensive, summary, technical)

        Returns:
            Generated report with all sections
        """
        with trace_operation(
            self.tracer,
            "reporter_agent_execution",
            attributes={
                "agent_id": self.agent_id,
                "report_type": report_type,
                "num_campaigns": len(report_context.campaign_data),
            },
        ):
            logger.info(
                f"Generating {report_type} report for {len(report_context.campaign_data)} campaigns"
            )

            # Calculate statistics
            stats = self._calculate_statistics(report_context)

            # Generate executive summary
            executive_summary = await self._generate_executive_summary(report_context, stats)

            # Generate key findings
            key_findings = await self._generate_key_findings(report_context, stats)

            # Generate recommendations
            recommendations = await self._generate_recommendations(report_context, stats)

            # Generate detailed analysis
            detailed_analysis = await self._generate_detailed_analysis(report_context, stats)

            # Build report sections
            sections = self._build_report_sections(report_context, stats, report_type)

            # Create report
            report = GeneratedReport(
                executive_summary=executive_summary,
                key_findings=key_findings,
                recommendations=recommendations,
                detailed_analysis=detailed_analysis,
                sections=sections,
                metadata={
                    "report_type": report_type,
                    "agent_id": self.agent_id,
                    "model_id": self.model_id,
                    "statistics": stats,
                },
            )

            logger.info(
                f"Report generated: {len(key_findings)} findings, "
                f"{len(recommendations)} recommendations"
            )

            return report

    # ========================================================================
    # Statistics Calculation
    # ========================================================================

    def _calculate_statistics(self, context: ReportContext) -> dict[str, Any]:
        """
        Calculate statistics from evaluation data.

        Args:
            context: Report context

        Returns:
            Dictionary of calculated statistics
        """
        campaigns = context.campaign_data
        turns = context.turn_data
        evaluations = context.evaluation_data

        # Basic counts
        total_campaigns = len(campaigns)
        total_turns = len(turns)
        total_evaluations = len(evaluations)

        # Turn statistics
        completed_turns = sum(1 for t in turns if t.get("status") == "completed")
        failed_turns = total_turns - completed_turns
        success_rate = completed_turns / total_turns if total_turns > 0 else 0.0

        # Score statistics
        scores = [e.get("score", 0.0) for e in evaluations]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        min_score = min(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        # Campaign type distribution
        campaign_types = [c.get("campaign_type") for c in campaigns]
        type_counts = {}
        for ctype in campaign_types:
            type_counts[ctype] = type_counts.get(ctype, 0) + 1

        # Metric aggregation
        metric_scores = {}
        for eval_data in evaluations:
            metrics = eval_data.get("metrics", {})
            for metric_name, metric_value in metrics.items():
                if metric_name not in metric_scores:
                    metric_scores[metric_name] = []
                metric_scores[metric_name].append(metric_value)

        metric_averages = {
            name: sum(scores) / len(scores) for name, scores in metric_scores.items()
        }

        return {
            "total_campaigns": total_campaigns,
            "total_turns": total_turns,
            "total_evaluations": total_evaluations,
            "completed_turns": completed_turns,
            "failed_turns": failed_turns,
            "success_rate": success_rate,
            "avg_score": avg_score,
            "min_score": min_score,
            "max_score": max_score,
            "campaign_type_counts": type_counts,
            "metric_averages": metric_averages,
        }

    # ========================================================================
    # LLM-Powered Content Generation
    # ========================================================================

    async def _generate_executive_summary(
        self, context: ReportContext, stats: dict[str, Any]
    ) -> str:
        """Generate executive summary using LLM."""
        with trace_operation(
            self.tracer,
            "generate_executive_summary",
            attributes={"agent_id": self.agent_id},
        ):
            prompt = self._build_executive_summary_prompt(context, stats)

            system_prompt = (
                "You are an expert AI evaluation analyst generating executive "
                "summaries for stakeholders. Write clearly, concisely, and focus "
                "on business impact. Use professional tone suitable for executives."
            )

            response = await self.invoke_llm(
                prompt=prompt,
                model_id=self.model_id,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system_prompt=system_prompt,
            )

            return response.get("content", "")

    async def _generate_key_findings(
        self, context: ReportContext, stats: dict[str, Any]
    ) -> list[str]:
        """Generate key findings using LLM."""
        with trace_operation(
            self.tracer,
            "generate_key_findings",
            attributes={"agent_id": self.agent_id},
        ):
            prompt = self._build_key_findings_prompt(context, stats)

            system_prompt = (
                "You are an expert data analyst identifying key patterns and "
                "insights from evaluation data. List 3-5 most important findings "
                "as bullet points. Be specific and data-driven."
            )

            response = await self.invoke_llm(
                prompt=prompt,
                model_id=self.model_id,
                max_tokens=1500,
                temperature=self.temperature,
                system_prompt=system_prompt,
            )

            content = response.get("content", "")
            # Parse findings from response (split by lines starting with - or •)
            findings = [
                line.strip().lstrip("-•").strip()
                for line in content.split("\n")
                if line.strip() and line.strip().startswith(("-", "•", "*"))
            ]

            return findings[:5]  # Limit to 5 findings

    async def _generate_recommendations(
        self, context: ReportContext, stats: dict[str, Any]
    ) -> list[str]:
        """Generate actionable recommendations using LLM."""
        with trace_operation(
            self.tracer,
            "generate_recommendations",
            attributes={"agent_id": self.agent_id},
        ):
            prompt = self._build_recommendations_prompt(context, stats)

            system_prompt = (
                "You are an expert AI consultant providing actionable "
                "recommendations for system improvement. List 3-5 specific, "
                "measurable recommendations based on evaluation data."
            )

            response = await self.invoke_llm(
                prompt=prompt,
                model_id=self.model_id,
                max_tokens=1500,
                temperature=self.temperature,
                system_prompt=system_prompt,
            )

            content = response.get("content", "")
            recommendations = [
                line.strip().lstrip("-•").strip()
                for line in content.split("\n")
                if line.strip() and line.strip().startswith(("-", "•", "*"))
            ]

            return recommendations[:5]  # Limit to 5 recommendations

    async def _generate_detailed_analysis(
        self, context: ReportContext, stats: dict[str, Any]
    ) -> str:
        """Generate detailed analysis section using LLM."""
        with trace_operation(
            self.tracer,
            "generate_detailed_analysis",
            attributes={"agent_id": self.agent_id},
        ):
            prompt = self._build_detailed_analysis_prompt(context, stats)

            system_prompt = (
                "You are an expert technical analyst providing in-depth analysis "
                "of AI system evaluation results. Write comprehensive analysis "
                "with technical depth suitable for engineering teams."
            )

            response = await self.invoke_llm(
                prompt=prompt,
                model_id=self.model_id,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system_prompt=system_prompt,
            )

            return response.get("content", "")

    # ========================================================================
    # Prompt Building
    # ========================================================================

    def _build_executive_summary_prompt(self, context: ReportContext, stats: dict[str, Any]) -> str:
        """Build prompt for executive summary generation."""
        return f"""Generate an executive summary for this AI system evaluation:

EVALUATION SCOPE:
- Total Campaigns: {stats["total_campaigns"]}
- Campaign Types: {", ".join(f"{k}: {v}" for k, v in stats["campaign_type_counts"].items())}
- Total Turns: {stats["total_turns"]} ({stats["completed_turns"]} completed)
- Evaluation Period: {context.time_range.get("start", "N/A")} to {context.time_range.get("end", "N/A")}
- Region: {context.region}

PERFORMANCE METRICS:
- Overall Quality Score: {stats["avg_score"] * 100:.1f}%
- Success Rate: {stats["success_rate"] * 100:.1f}%
- Score Range: {stats["min_score"] * 100:.1f}% - {stats["max_score"] * 100:.1f}%

METRIC BREAKDOWN:
{self._format_metrics(stats["metric_averages"])}

Write a 2-3 paragraph executive summary highlighting:
1. Overall system performance assessment
2. Key strengths and areas for improvement
3. Business impact and next steps

Focus on actionable insights for decision-makers."""

    def _build_key_findings_prompt(self, context: ReportContext, stats: dict[str, Any]) -> str:
        """Build prompt for key findings generation."""
        return f"""Analyze this evaluation data and identify 3-5 key findings:

STATISTICS:
- Total Evaluations: {stats["total_evaluations"]}
- Average Score: {stats["avg_score"] * 100:.1f}%
- Success Rate: {stats["success_rate"] * 100:.1f}%
- Failed Turns: {stats["failed_turns"]}

METRIC PERFORMANCE:
{self._format_metrics(stats["metric_averages"])}

CAMPAIGN DISTRIBUTION:
{", ".join(f"{k}: {v}" for k, v in stats["campaign_type_counts"].items())}

Identify 3-5 most important findings. Each finding should:
- Be data-driven and specific
- Highlight patterns or anomalies
- Have clear business implications

Format as bullet points starting with - or •."""

    def _build_recommendations_prompt(self, context: ReportContext, stats: dict[str, Any]) -> str:
        """Build prompt for recommendations generation."""
        low_metrics = [name for name, score in stats["metric_averages"].items() if score < 0.7]

        return f"""Based on this evaluation data, provide 3-5 actionable recommendations:

CURRENT PERFORMANCE:
- Overall Score: {stats["avg_score"] * 100:.1f}%
- Success Rate: {stats["success_rate"] * 100:.1f}%
- Failed Turns: {stats["failed_turns"]}

LOW-PERFORMING METRICS:
{", ".join(low_metrics) if low_metrics else "None - all metrics performing well"}

METRIC SCORES:
{self._format_metrics(stats["metric_averages"])}

Provide 3-5 specific, actionable recommendations for improvement.
Each recommendation should:
- Be concrete and implementable
- Address specific weaknesses
- Include expected impact

Format as bullet points starting with - or •."""

    def _build_detailed_analysis_prompt(self, context: ReportContext, stats: dict[str, Any]) -> str:
        """Build prompt for detailed analysis generation."""
        return f"""Provide comprehensive technical analysis of this AI system evaluation:

EVALUATION DETAILS:
- Campaigns: {stats["total_campaigns"]} across {len(stats["campaign_type_counts"])} types
- Total Interactions: {stats["total_turns"]} turns, {stats["total_evaluations"]} evaluations
- Success Rate: {stats["success_rate"] * 100:.1f}%

QUALITY METRICS:
{self._format_metrics(stats["metric_averages"])}

CAMPAIGN TYPES:
{self._format_campaign_types(stats["campaign_type_counts"])}

Provide detailed analysis covering:
1. **Performance Analysis**: Deep dive into quality metrics
2. **Pattern Identification**: Trends across campaign types
3. **Failure Analysis**: Root causes of failed turns
4. **Comparative Assessment**: Performance across different scenarios
5. **Technical Insights**: System behavior and capabilities

Write 3-4 paragraphs with technical depth suitable for engineering teams."""

    # ========================================================================
    # Report Section Building
    # ========================================================================

    def _build_report_sections(
        self,
        context: ReportContext,
        stats: dict[str, Any],
        report_type: str,
    ) -> list[ReportSection]:
        """Build structured report sections."""
        sections = []

        # Overview section
        sections.append(
            ReportSection(
                title="Evaluation Overview",
                content=self._build_overview_section(context, stats),
                priority=10,
            )
        )

        # Performance metrics section
        sections.append(
            ReportSection(
                title="Performance Metrics",
                content=self._build_metrics_section(stats),
                priority=9,
            )
        )

        # Campaign analysis section
        sections.append(
            ReportSection(
                title="Campaign Analysis",
                content=self._build_campaign_section(context, stats),
                priority=8,
            )
        )

        if report_type == "comprehensive":
            # Add detailed sections for comprehensive reports
            sections.append(
                ReportSection(
                    title="Turn-by-Turn Analysis",
                    content=self._build_turn_analysis_section(context),
                    priority=7,
                )
            )

        return sections

    def _build_overview_section(self, context: ReportContext, stats: dict[str, Any]) -> str:
        """Build overview section content."""
        return f"""**Evaluation Period**: {context.time_range.get("start", "N/A")} to {context.time_range.get("end", "N/A")}
**Region**: {context.region}
**Environment**: {context.environment}

**Summary Statistics**:
- Total Campaigns: {stats["total_campaigns"]}
- Total Turns: {stats["total_turns"]}
- Completed Turns: {stats["completed_turns"]}
- Failed Turns: {stats["failed_turns"]}
- Success Rate: {stats["success_rate"] * 100:.1f}%
- Overall Quality Score: {stats["avg_score"] * 100:.1f}%
"""

    def _build_metrics_section(self, stats: dict[str, Any]) -> str:
        """Build metrics section content."""
        metrics_md = "| Metric | Score |\n|--------|-------|\n"
        for name, score in sorted(
            stats["metric_averages"].items(), key=lambda x: x[1], reverse=True
        ):
            metrics_md += f"| {name} | {score * 100:.1f}% |\n"

        return metrics_md

    def _build_campaign_section(self, context: ReportContext, stats: dict[str, Any]) -> str:
        """Build campaign analysis section."""
        content = "**Campaign Type Distribution**:\n\n"
        for ctype, count in stats["campaign_type_counts"].items():
            percentage = (count / stats["total_campaigns"]) * 100
            content += f"- {ctype}: {count} ({percentage:.1f}%)\n"

        return content

    def _build_turn_analysis_section(self, context: ReportContext) -> str:
        """Build turn-by-turn analysis section."""
        turns = context.turn_data[:10]  # Limit to first 10 for brevity

        content = "**Sample Turn Analysis** (first 10 turns):\n\n"
        for turn in turns:
            turn_num = turn.get("turn_number", "?")
            status = turn.get("status", "unknown")
            content += f"- Turn {turn_num}: {status}\n"

        return content

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _format_metrics(self, metrics: dict[str, float]) -> str:
        """Format metrics dict as readable string."""
        return "\n".join(
            f"- {name}: {score * 100:.1f}%"
            for name, score in sorted(metrics.items(), key=lambda x: x[1], reverse=True)
        )

    def _format_campaign_types(self, types: dict[str, int]) -> str:
        """Format campaign types dict as readable string."""
        return "\n".join(f"- {ctype}: {count} campaigns" for ctype, count in types.items())

    def _get_default_model(self) -> str:
        """Get default Bedrock model for Reporter Agent."""
        return self.model_id
