"""
Centralized output directory management for AgentEval.

This module provides a single source of truth for all file generation paths,
ensuring consistent output structure across the entire workflow.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agenteval.config import Settings


class OutputManager:
    """
    Centralized manager for all AgentEval output paths.

    Provides consistent directory structure for all generated files:
    - Campaign data (DynamoDB exports, S3 downloads)
    - Reports (HTML, Markdown, JSON)
    - Logs (execution logs, debug logs)
    - Traces (X-Ray trace reports)

    Directory Structure:
        evidence_root/
        ├── {timestamp}-run/          # Timestamped run directory
        │   ├── campaigns/             # All campaign data
        │   │   └── {campaign-id}/
        │   │       ├── dynamodb/      # DynamoDB exports
        │   │       └── s3/            # S3 downloads
        │   ├── reports/               # HTML/markdown reports
        │   ├── logs/                  # Execution logs
        │   ├── traces/                # X-Ray traces
        │   ├── dashboard.md           # Generated dashboard
        │   └── summary.md             # Generated summary
        └── latest -> {timestamp}-run/ # Symlink to latest run
    """

    def __init__(self, settings: Settings | None = None, run_timestamp: str | None = None):
        """
        Initialize OutputManager.

        Args:
            settings: AgentEval settings instance (uses global settings if None)
            run_timestamp: Timestamp string for run directory (generates new if None)
        """
        if settings is None:
            from agenteval.config import settings as global_settings

            settings = global_settings

        self.settings = settings
        self.run_timestamp = run_timestamp or self._generate_timestamp()

        # Base evidence directory (configurable)
        self.evidence_root = Path(settings.app.evidence_report_output_dir).resolve()

        # Run-specific directory (timestamped)
        self.run_dir = self.evidence_root / f"{self.run_timestamp}-run"

        # Subdirectories within run
        self._campaigns_dir = self.run_dir / "campaigns"
        self._reports_dir = self.run_dir / "reports"
        self._logs_dir = self.run_dir / "logs"
        self._traces_dir = self.run_dir / "traces"

    @staticmethod
    def _generate_timestamp() -> str:
        """Generate UTC timestamp string in ISO format (YYYYMMDDTHHMMSS)."""
        return datetime.utcnow().strftime("%Y%m%dT%H%M%S")

    def ensure_directories(self) -> None:
        """Create all output directories if they don't exist."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self._campaigns_dir.mkdir(parents=True, exist_ok=True)
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        self._traces_dir.mkdir(parents=True, exist_ok=True)

        # Create or update 'latest' symlink
        self._create_latest_symlink()

    def _create_latest_symlink(self) -> None:
        """Create or update 'latest' symlink pointing to current run."""
        latest_link = self.evidence_root / "latest"

        # Remove existing symlink if it exists
        if latest_link.is_symlink():
            latest_link.unlink()
        elif latest_link.exists():
            # If it's a regular directory/file, don't overwrite
            return

        # Create new symlink
        try:
            # Use relative path for symlink
            relative_target = self.run_dir.relative_to(self.evidence_root)
            latest_link.symlink_to(relative_target)
        except (OSError, NotImplementedError):
            # Symlinks might not be supported on all platforms (e.g., Windows without admin)
            pass

    @property
    def campaigns_dir(self) -> Path:
        """Directory for all campaign data."""
        return self._campaigns_dir

    @property
    def reports_dir(self) -> Path:
        """Directory for generated reports (HTML, markdown, JSON)."""
        return self._reports_dir

    @property
    def logs_dir(self) -> Path:
        """Directory for execution logs."""
        return self._logs_dir

    @property
    def traces_dir(self) -> Path:
        """Directory for X-Ray trace reports."""
        return self._traces_dir

    @property
    def dashboard_path(self) -> Path:
        """Path to main dashboard markdown file."""
        return self.run_dir / "dashboard.md"

    @property
    def dashboard_html_path(self) -> Path:
        """Path to main dashboard HTML file."""
        return self.reports_dir / "dashboard.html"

    @property
    def summary_path(self) -> Path:
        """Path to summary markdown file."""
        return self.run_dir / "summary.md"

    @property
    def summary_html_path(self) -> Path:
        """Path to summary HTML file."""
        return self.reports_dir / "summary.html"

    @property
    def latest_dir(self) -> Path:
        """Path to 'latest' symlink directory."""
        return self.evidence_root / "latest"

    def get_campaign_dir(self, campaign_id: str) -> Path:
        """
        Get directory path for a specific campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Path to campaign directory
        """
        return self._campaigns_dir / campaign_id

    def get_campaign_dynamodb_dir(self, campaign_id: str) -> Path:
        """
        Get directory path for campaign DynamoDB exports.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Path to campaign DynamoDB directory
        """
        return self.get_campaign_dir(campaign_id) / "dynamodb"

    def get_campaign_s3_dir(self, campaign_id: str) -> Path:
        """
        Get directory path for campaign S3 downloads.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Path to campaign S3 directory
        """
        return self.get_campaign_dir(campaign_id) / "s3"

    def get_campaign_s3_results_dir(self, campaign_id: str) -> Path:
        """
        Get directory path for campaign S3 results.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Path to campaign S3 results directory
        """
        return self.get_campaign_s3_dir(campaign_id) / "results"

    def get_campaign_s3_reports_dir(self, campaign_id: str) -> Path:
        """
        Get directory path for campaign S3 reports.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Path to campaign S3 reports directory
        """
        return self.get_campaign_s3_dir(campaign_id) / "reports"

    def get_log_path(self, log_name: str) -> Path:
        """
        Get path for a specific log file.

        Args:
            log_name: Name of log file (with or without extension)

        Returns:
            Path to log file
        """
        if not log_name.endswith(".log"):
            log_name = f"{log_name}.log"
        return self._logs_dir / log_name

    def get_trace_report_path(self, campaign_id: str) -> Path:
        """
        Get path for campaign trace report.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Path to trace report file
        """
        return self._traces_dir / f"{self.run_timestamp}-{campaign_id}-traces.json"

    def get_report_path(self, report_name: str) -> Path:
        """
        Get path for a specific report file.

        Args:
            report_name: Name of report file (with or without extension)

        Returns:
            Path to report file
        """
        return self._reports_dir / report_name

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> OutputManager:
        """
        Create OutputManager from settings.

        Args:
            settings: AgentEval settings instance (uses global settings if None)

        Returns:
            Configured OutputManager instance
        """
        return cls(settings=settings)

    @classmethod
    def for_existing_run(cls, run_dir: Path, settings: Settings | None = None) -> OutputManager:
        """
        Create OutputManager for an existing run directory.

        Args:
            run_dir: Path to existing run directory
            settings: AgentEval settings instance (uses global settings if None)

        Returns:
            OutputManager instance configured for existing run
        """
        # Extract timestamp from run directory name
        run_dir = Path(run_dir).resolve()
        run_name = run_dir.name

        # Handle both "{timestamp}-run" and plain "{timestamp}" formats
        if run_name.endswith("-run"):
            timestamp = run_name[:-4]
        else:
            timestamp = run_name

        return cls(settings=settings, run_timestamp=timestamp)

    def __repr__(self) -> str:
        return f"OutputManager(run_dir={self.run_dir!r})"

    def __str__(self) -> str:
        return f"OutputManager({self.run_timestamp})"


# Global output manager instance (lazy-initialized)
_global_output_manager: OutputManager | None = None


def get_output_manager(
    settings: Settings | None = None, run_timestamp: str | None = None
) -> OutputManager:
    """
    Get or create global OutputManager instance.

    Args:
        settings: AgentEval settings instance (uses global settings if None)
        run_timestamp: Timestamp string for run directory (reuses global if None)

    Returns:
        Global OutputManager instance
    """
    global _global_output_manager

    if _global_output_manager is None or run_timestamp is not None:
        _global_output_manager = OutputManager(settings=settings, run_timestamp=run_timestamp)

    return _global_output_manager


def reset_output_manager() -> None:
    """Reset global OutputManager instance (useful for testing)."""
    global _global_output_manager
    _global_output_manager = None
