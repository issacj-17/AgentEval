"""
HTML Renderer Service for AgentEval Reports.

This module provides HTML rendering capabilities with Chart.js integration
following SOLID principles and design patterns.

Design Patterns:
    - Strategy Pattern: Different rendering strategies for templates
    - Template Method Pattern: Base rendering workflow
    - Builder Pattern: Building complex chart configurations
    - Factory Pattern: Creating renderers for different contexts

SOLID Principles:
    - SRP: Single responsibility of rendering HTML from templates
    - OCP: Open for extension (new templates), closed for modification
    - LSP: Template renderers are substitutable
    - ISP: Clean rendering interface
    - DIP: Depends on Jinja2 abstraction, not concrete implementations
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class HTMLRendererError(Exception):
    """Base exception for HTML rendering errors."""

    pass


class TemplateNotFoundError(HTMLRendererError):
    """Raised when a template file is not found."""

    pass


class RenderingError(HTMLRendererError):
    """Raised when rendering fails."""

    pass


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class ChartData:
    """Chart.js data configuration."""

    labels: list[str]
    datasets: list[dict[str, Any]]
    chart_type: str = "bar"  # bar, line, radar, doughnut, pie
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class CampaignSummary:
    """Summary data for a single campaign."""

    id: str
    type: str
    status: str
    status_class: str
    score: float
    score_class: str
    completed_turns: int
    total_turns: int
    duration: str
    created_at: str


@dataclass
class MetricSummary:
    """Summary data for a quality metric."""

    name: str
    score: float
    score_class: str


@dataclass
class TurnDetail:
    """Detailed data for a conversation turn."""

    number: int
    status: str
    status_class: str
    score: float
    user_message: str
    system_response: str
    metrics: list[MetricSummary]
    trace_id: str | None = None


@dataclass
class DashboardContext:
    """Template context for dashboard rendering."""

    title: str
    subtitle: str
    generated_at: str
    region: str
    environment: str
    total_campaigns: int
    overall_score: float
    total_turns: int
    completed_turns: int
    failed_turns: int
    success_rate: float
    total_evaluations: int
    total_metrics: int
    campaigns: list[CampaignSummary]
    # Chart.js data
    campaign_labels: list[str]
    campaign_scores: list[float]
    campaign_type_labels: list[str]
    campaign_type_counts: list[int]
    metric_labels: list[str]
    metric_scores: list[float]
    turn_trend_labels: list[str]
    turn_trend_completed: list[int]
    turn_trend_failed: list[int]


@dataclass
class CampaignContext:
    """Template context for campaign detail rendering."""

    campaign_id: str
    campaign_type: str
    status: str
    status_class: str
    overall_score: float
    completed_turns: int
    total_turns: int
    duration: str
    created_at: str
    region: str
    metrics: list[MetricSummary]
    turns: list[TurnDetail]
    # Chart.js data
    metric_labels: list[str]
    metric_scores: list[float]
    turn_labels: list[str]
    turn_scores: list[float]


@dataclass
class SummaryContext:
    """Template context for executive summary rendering."""

    generated_at: str
    evaluation_period: str
    total_campaigns: int
    region: str
    overview_text: str
    overall_score: float
    overall_status: str
    overall_status_class: str
    performance_assessment: str
    total_turns: int
    completed_turns: int
    failed_turns: int
    success_rate: float
    total_evaluations: int
    total_metrics: int
    recommendations: list[dict[str, str]]
    conclusion_text: str


# ============================================================================
# Protocols (Interface Segregation)
# ============================================================================


class TemplateRenderer(Protocol):
    """Protocol defining template rendering interface."""

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template with given context."""
        ...


# ============================================================================
# HTML Renderer Service
# ============================================================================


class HTMLRenderer:
    """
    Service for rendering HTML reports from Jinja2 templates.

    This service provides high-level rendering methods for different
    report types (dashboard, campaign detail, executive summary) with
    Chart.js integration.

    Attributes:
        template_dir: Directory containing Jinja2 templates
        output_dir: Directory for saving rendered HTML files
        env: Jinja2 environment
    """

    def __init__(
        self,
        template_dir: Path | None = None,
        output_dir: Path | None = None,
    ):
        """
        Initialize HTMLRenderer.

        Args:
            template_dir: Path to templates directory
            output_dir: Path to output directory for rendered files
        """
        self.template_dir = template_dir or self._get_default_template_dir()
        self.output_dir = output_dir or Path("demo/evidence/reports")

        # Ensure directories exist
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self._register_custom_filters()

        logger.info(
            f"HTMLRenderer initialized (templates: {self.template_dir}, output: {self.output_dir})"
        )

    def _get_default_template_dir(self) -> Path:
        """Get default template directory."""
        # Assume this file is in src/agenteval/reporting/
        current_file = Path(__file__)
        return current_file.parent / "templates"

    def _register_custom_filters(self) -> None:
        """Register custom Jinja2 filters."""

        def format_score(value: float) -> str:
            """Format score as percentage."""
            return f"{value * 100:.1f}%"

        def format_datetime(value: str) -> str:
            """Format datetime string."""
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                return value

        def score_class(value: float) -> str:
            """Get CSS class based on score."""
            if value >= 0.8:
                return ""  # High score (default/green)
            elif value >= 0.6:
                return "medium"  # Medium score (yellow)
            else:
                return "low"  # Low score (red)

        def status_badge_class(status: str) -> str:
            """Get badge CSS class based on status."""
            status_lower = status.lower()
            if status_lower in ["completed", "success"]:
                return "success"
            elif status_lower in ["running", "in_progress"]:
                return "info"
            elif status_lower in ["failed", "error"]:
                return "danger"
            else:
                return "warning"

        # Register filters
        self.env.filters["format_score"] = format_score
        self.env.filters["format_datetime"] = format_datetime
        self.env.filters["score_class"] = score_class
        self.env.filters["status_badge_class"] = status_badge_class

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a template with given context.

        Args:
            template_name: Name of template file
            context: Template context data

        Returns:
            Rendered HTML string

        Raises:
            TemplateNotFoundError: If template not found
            RenderingError: If rendering fails
        """
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(**context)
            logger.debug(f"Rendered template: {template_name}")
            return rendered
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            if "not found" in str(e).lower():
                raise TemplateNotFoundError(f"Template not found: {template_name}") from e
            raise RenderingError(f"Rendering failed: {e}") from e

    def save_html(self, html_content: str, filename: str) -> Path:
        """
        Save rendered HTML to file.

        Args:
            html_content: Rendered HTML content
            filename: Output filename

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename
        output_path.write_text(html_content, encoding="utf-8")
        logger.info(f"Saved HTML report: {output_path}")
        return output_path

    # ========================================================================
    # High-Level Rendering Methods
    # ========================================================================

    def render_dashboard(self, context: DashboardContext) -> Path:
        """
        Render dashboard HTML with all campaigns overview.

        Args:
            context: Dashboard context data

        Returns:
            Path to rendered HTML file
        """
        logger.info("Rendering dashboard...")

        # Convert dataclass to dict
        context_dict = self._dataclass_to_dict(context)

        # Render template
        html = self.render_template("dashboard.html", context_dict)

        # Save to file
        output_path = self.save_html(html, "dashboard.html")

        logger.info(f"Dashboard rendered successfully: {output_path}")
        return output_path

    def render_campaign_detail(self, context: CampaignContext) -> Path:
        """
        Render campaign detail HTML for a single campaign.

        Args:
            context: Campaign context data

        Returns:
            Path to rendered HTML file
        """
        campaign_id = context.campaign_id
        logger.info(f"Rendering campaign detail for {campaign_id}...")

        # Convert dataclass to dict
        context_dict = self._dataclass_to_dict(context)

        # Render template
        html = self.render_template("campaign.html", context_dict)

        # Save to file
        filename = f"campaign_{campaign_id}.html"
        output_path = self.save_html(html, filename)

        logger.info(f"Campaign detail rendered successfully: {output_path}")
        return output_path

    def render_summary(self, context: SummaryContext) -> Path:
        """
        Render executive summary HTML.

        Args:
            context: Summary context data

        Returns:
            Path to rendered HTML file
        """
        logger.info("Rendering executive summary...")

        # Convert dataclass to dict
        context_dict = self._dataclass_to_dict(context)

        # Render template
        html = self.render_template("summary.html", context_dict)

        # Save to file
        output_path = self.save_html(html, "summary.html")

        logger.info(f"Executive summary rendered successfully: {output_path}")
        return output_path

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _dataclass_to_dict(self, obj: Any) -> dict[str, Any]:
        """
        Convert dataclass (including nested) to dictionary.

        Args:
            obj: Dataclass instance

        Returns:
            Dictionary representation
        """
        if hasattr(obj, "__dataclass_fields__"):
            result = {}
            for field_name in obj.__dataclass_fields__:
                value = getattr(obj, field_name)
                if isinstance(value, list):
                    result[field_name] = [self._dataclass_to_dict(item) for item in value]
                elif hasattr(value, "__dataclass_fields__"):
                    result[field_name] = self._dataclass_to_dict(value)
                else:
                    result[field_name] = value
            return result
        return obj

    @staticmethod
    def calculate_score_class(score: float) -> str:
        """
        Calculate CSS class based on score value.

        Args:
            score: Score value (0.0 to 1.0)

        Returns:
            CSS class name
        """
        if score >= 0.8:
            return ""  # High score
        elif score >= 0.6:
            return "medium"  # Medium score
        else:
            return "low"  # Low score

    @staticmethod
    def calculate_status_class(status: str) -> str:
        """
        Calculate CSS class based on status.

        Args:
            status: Status string

        Returns:
            CSS class name
        """
        status_lower = status.lower()
        if status_lower in ["completed", "success"]:
            return "success"
        elif status_lower in ["running", "in_progress"]:
            return "info"
        elif status_lower in ["failed", "error"]:
            return "danger"
        else:
            return "warning"

    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format duration in human-readable format.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted duration string
        """
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"


# ============================================================================
# Chart Data Builders (Builder Pattern)
# ============================================================================


class ChartDataBuilder:
    """
    Builder for Chart.js data configurations.

    Implements Builder pattern for constructing complex chart configurations.
    """

    def __init__(self, chart_type: str = "bar"):
        """Initialize builder with chart type."""
        self.chart_type = chart_type
        self.labels: list[str] = []
        self.datasets: list[dict[str, Any]] = []
        self.options: dict[str, Any] = {}

    def with_labels(self, labels: list[str]) -> "ChartDataBuilder":
        """Set chart labels."""
        self.labels = labels
        return self

    def add_dataset(
        self,
        label: str,
        data: list[Any],
        **kwargs: Any,
    ) -> "ChartDataBuilder":
        """
        Add a dataset to the chart.

        Args:
            label: Dataset label
            data: Data values
            **kwargs: Additional Chart.js dataset properties
        """
        dataset = {"label": label, "data": data, **kwargs}
        self.datasets.append(dataset)
        return self

    def with_options(self, options: dict[str, Any]) -> "ChartDataBuilder":
        """Set chart options."""
        self.options = options
        return self

    def build(self) -> ChartData:
        """Build ChartData instance."""
        return ChartData(
            labels=self.labels,
            datasets=self.datasets,
            chart_type=self.chart_type,
            options=self.options,
        )


# ============================================================================
# Factory Functions
# ============================================================================


def create_html_renderer(
    template_dir: Path | None = None,
    output_dir: Path | None = None,
) -> HTMLRenderer:
    """
    Factory function for creating HTMLRenderer instances.

    Args:
        template_dir: Path to templates directory
        output_dir: Path to output directory

    Returns:
        Configured HTMLRenderer instance
    """
    return HTMLRenderer(template_dir=template_dir, output_dir=output_dir)


def create_chart_builder(chart_type: str = "bar") -> ChartDataBuilder:
    """
    Factory function for creating ChartDataBuilder instances.

    Args:
        chart_type: Type of chart (bar, line, radar, etc.)

    Returns:
        Configured ChartDataBuilder instance
    """
    return ChartDataBuilder(chart_type=chart_type)
