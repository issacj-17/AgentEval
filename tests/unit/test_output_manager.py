"""
Unit tests for OutputManager.

Tests centralized output directory management for consistent file generation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from agenteval.config import Settings
from agenteval.reporting.output_manager import (
    OutputManager,
    get_output_manager,
    reset_output_manager,
)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.app = MagicMock()
    settings.app.evidence_report_output_dir = "test-evidence"
    return settings


@pytest.fixture
def temp_output_manager(tmp_path, mock_settings):
    """Create OutputManager with temporary directory."""
    mock_settings.app.evidence_report_output_dir = str(tmp_path / "evidence")
    return OutputManager(settings=mock_settings, run_timestamp="20250120T120000")


@pytest.fixture(autouse=True)
def cleanup_global_manager():
    """Reset global OutputManager after each test."""
    yield
    reset_output_manager()


class TestOutputManagerInitialization:
    """Test OutputManager initialization."""

    def test_init_with_custom_timestamp(self, mock_settings):
        """Test initialization with custom timestamp."""
        timestamp = "20250120T120000"
        manager = OutputManager(settings=mock_settings, run_timestamp=timestamp)

        assert manager.run_timestamp == timestamp
        assert manager.run_dir.name == f"{timestamp}-run"

    def test_init_generates_timestamp_if_none(self, mock_settings):
        """Test timestamp generation when not provided."""
        with patch("agenteval.reporting.output_manager.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value.strftime.return_value = "20250120T123456"

            manager = OutputManager(settings=mock_settings)

            assert manager.run_timestamp == "20250120T123456"

    def test_init_uses_settings_evidence_dir(self, mock_settings):
        """Test initialization uses evidence directory from settings."""
        mock_settings.app.evidence_report_output_dir = "/custom/evidence"
        manager = OutputManager(settings=mock_settings, run_timestamp="20250120T120000")

        assert manager.evidence_root == Path("/custom/evidence").resolve()

    def test_init_creates_subdirectory_paths(self, temp_output_manager):
        """Test initialization creates correct subdirectory paths."""
        assert temp_output_manager.campaigns_dir.name == "campaigns"
        assert temp_output_manager.reports_dir.name == "reports"
        assert temp_output_manager.logs_dir.name == "logs"
        assert temp_output_manager.traces_dir.name == "traces"


class TestOutputManagerDirectoryCreation:
    """Test OutputManager directory creation."""

    def test_ensure_directories_creates_all_dirs(self, temp_output_manager):
        """Test ensure_directories creates all required directories."""
        temp_output_manager.ensure_directories()

        assert temp_output_manager.run_dir.exists()
        assert temp_output_manager.campaigns_dir.exists()
        assert temp_output_manager.reports_dir.exists()
        assert temp_output_manager.logs_dir.exists()
        assert temp_output_manager.traces_dir.exists()

    def test_ensure_directories_creates_latest_symlink(self, temp_output_manager):
        """Test ensure_directories creates 'latest' symlink."""
        temp_output_manager.ensure_directories()

        latest_link = temp_output_manager.evidence_root / "latest"

        # Symlink creation might not be supported on all platforms
        if latest_link.exists():
            assert latest_link.is_symlink()
            assert latest_link.resolve() == temp_output_manager.run_dir

    def test_ensure_directories_idempotent(self, temp_output_manager):
        """Test ensure_directories can be called multiple times safely."""
        temp_output_manager.ensure_directories()
        temp_output_manager.ensure_directories()  # Should not raise

        assert temp_output_manager.run_dir.exists()

    def test_ensure_directories_updates_latest_symlink(self, tmp_path, mock_settings):
        """Test ensure_directories updates 'latest' symlink for new runs."""
        mock_settings.app.evidence_report_output_dir = str(tmp_path / "evidence")

        # Create first run
        manager1 = OutputManager(settings=mock_settings, run_timestamp="20250120T120000")
        manager1.ensure_directories()

        # Create second run
        manager2 = OutputManager(settings=mock_settings, run_timestamp="20250120T130000")
        manager2.ensure_directories()

        latest_link = manager2.evidence_root / "latest"

        if latest_link.exists() and latest_link.is_symlink():
            assert latest_link.resolve() == manager2.run_dir


class TestOutputManagerPathGetters:
    """Test OutputManager path getter methods."""

    def test_get_campaign_dir(self, temp_output_manager):
        """Test get_campaign_dir returns correct path."""
        campaign_id = "test-campaign-123"
        path = temp_output_manager.get_campaign_dir(campaign_id)

        assert path.parent == temp_output_manager.campaigns_dir
        assert path.name == campaign_id

    def test_get_campaign_dynamodb_dir(self, temp_output_manager):
        """Test get_campaign_dynamodb_dir returns correct path."""
        campaign_id = "test-campaign-123"
        path = temp_output_manager.get_campaign_dynamodb_dir(campaign_id)

        assert path.parent.name == campaign_id
        assert path.name == "dynamodb"

    def test_get_campaign_s3_dir(self, temp_output_manager):
        """Test get_campaign_s3_dir returns correct path."""
        campaign_id = "test-campaign-123"
        path = temp_output_manager.get_campaign_s3_dir(campaign_id)

        assert path.parent.name == campaign_id
        assert path.name == "s3"

    def test_get_campaign_s3_results_dir(self, temp_output_manager):
        """Test get_campaign_s3_results_dir returns correct path."""
        campaign_id = "test-campaign-123"
        path = temp_output_manager.get_campaign_s3_results_dir(campaign_id)

        assert path.parents[1].name == campaign_id
        assert path.parent.name == "s3"
        assert path.name == "results"

    def test_get_campaign_s3_reports_dir(self, temp_output_manager):
        """Test get_campaign_s3_reports_dir returns correct path."""
        campaign_id = "test-campaign-123"
        path = temp_output_manager.get_campaign_s3_reports_dir(campaign_id)

        assert path.parents[1].name == campaign_id
        assert path.parent.name == "s3"
        assert path.name == "reports"

    def test_get_log_path(self, temp_output_manager):
        """Test get_log_path returns correct path."""
        log_name = "test-log"
        path = temp_output_manager.get_log_path(log_name)

        assert path.parent == temp_output_manager.logs_dir
        assert path.name == "test-log.log"

    def test_get_log_path_with_extension(self, temp_output_manager):
        """Test get_log_path handles .log extension."""
        log_name = "test-log.log"
        path = temp_output_manager.get_log_path(log_name)

        assert path.name == "test-log.log"

    def test_get_trace_report_path(self, temp_output_manager):
        """Test get_trace_report_path returns correct path."""
        campaign_id = "test-campaign-123"
        path = temp_output_manager.get_trace_report_path(campaign_id)

        assert path.parent == temp_output_manager.traces_dir
        assert campaign_id in path.name
        assert path.suffix == ".json"

    def test_get_report_path(self, temp_output_manager):
        """Test get_report_path returns correct path."""
        report_name = "dashboard.html"
        path = temp_output_manager.get_report_path(report_name)

        assert path.parent == temp_output_manager.reports_dir
        assert path.name == report_name

    def test_dashboard_path_property(self, temp_output_manager):
        """Test dashboard_path property returns correct path."""
        path = temp_output_manager.dashboard_path

        assert path.parent == temp_output_manager.run_dir
        assert path.name == "dashboard.md"

    def test_summary_path_property(self, temp_output_manager):
        """Test summary_path property returns correct path."""
        path = temp_output_manager.summary_path

        assert path.parent == temp_output_manager.run_dir
        assert path.name == "summary.md"

    def test_latest_dir_property(self, temp_output_manager):
        """Test latest_dir property returns correct path."""
        path = temp_output_manager.latest_dir

        assert path.parent == temp_output_manager.evidence_root
        assert path.name == "latest"


class TestOutputManagerFactoryMethods:
    """Test OutputManager factory methods."""

    def test_from_settings_creates_manager(self, mock_settings):
        """Test from_settings creates OutputManager instance."""
        manager = OutputManager.from_settings(settings=mock_settings)

        assert isinstance(manager, OutputManager)
        assert manager.evidence_root == Path(mock_settings.app.evidence_report_output_dir).resolve()

    def test_for_existing_run_with_run_suffix(self, tmp_path, mock_settings):
        """Test for_existing_run handles '-run' suffix."""
        mock_settings.app.evidence_report_output_dir = str(tmp_path / "evidence")
        run_dir = tmp_path / "evidence" / "20250120T120000-run"
        run_dir.mkdir(parents=True)

        manager = OutputManager.for_existing_run(run_dir, settings=mock_settings)

        assert manager.run_timestamp == "20250120T120000"
        assert manager.run_dir == run_dir

    def test_for_existing_run_without_run_suffix(self, tmp_path, mock_settings):
        """Test for_existing_run handles plain timestamp."""
        mock_settings.app.evidence_report_output_dir = str(tmp_path / "evidence")
        run_dir = tmp_path / "evidence" / "20250120T120000"
        run_dir.mkdir(parents=True)

        manager = OutputManager.for_existing_run(run_dir, settings=mock_settings)

        assert manager.run_timestamp == "20250120T120000"


class TestGlobalOutputManager:
    """Test global OutputManager singleton."""

    def test_get_output_manager_returns_singleton(self, mock_settings):
        """Test get_output_manager returns same instance."""
        manager1 = get_output_manager(settings=mock_settings)
        manager2 = get_output_manager()

        assert manager1 is manager2

    def test_get_output_manager_with_new_timestamp_creates_new(self, mock_settings):
        """Test get_output_manager with timestamp creates new instance."""
        manager1 = get_output_manager(settings=mock_settings, run_timestamp="20250120T120000")
        manager2 = get_output_manager(settings=mock_settings, run_timestamp="20250120T130000")

        assert manager1 is not manager2
        assert manager1.run_timestamp != manager2.run_timestamp

    def test_reset_output_manager_clears_singleton(self, mock_settings):
        """Test reset_output_manager clears global instance."""
        manager1 = get_output_manager(settings=mock_settings)
        reset_output_manager()
        manager2 = get_output_manager(settings=mock_settings)

        assert manager1 is not manager2


class TestOutputManagerRepresentation:
    """Test OutputManager string representations."""

    def test_repr(self, temp_output_manager):
        """Test __repr__ returns informative string."""
        repr_str = repr(temp_output_manager)

        assert "OutputManager" in repr_str
        assert "run_dir" in repr_str

    def test_str(self, temp_output_manager):
        """Test __str__ returns readable string."""
        str_repr = str(temp_output_manager)

        assert "OutputManager" in str_repr
        assert temp_output_manager.run_timestamp in str_repr


class TestOutputManagerIntegration:
    """Integration tests for OutputManager."""

    def test_full_workflow_creates_expected_structure(self, tmp_path, mock_settings):
        """Test full workflow creates expected directory structure."""
        mock_settings.app.evidence_report_output_dir = str(tmp_path / "evidence")
        manager = OutputManager(settings=mock_settings, run_timestamp="20250120T120000")
        manager.ensure_directories()

        # Create campaign structure
        campaign_id = "test-campaign-123"
        dynamodb_dir = manager.get_campaign_dynamodb_dir(campaign_id)
        dynamodb_dir.mkdir(parents=True)

        s3_results_dir = manager.get_campaign_s3_results_dir(campaign_id)
        s3_results_dir.mkdir(parents=True)

        s3_reports_dir = manager.get_campaign_s3_reports_dir(campaign_id)
        s3_reports_dir.mkdir(parents=True)

        # Create log file
        log_path = manager.get_log_path("test-run")
        log_path.write_text("test log content")

        # Create trace report
        trace_path = manager.get_trace_report_path(campaign_id)
        trace_path.write_text('{"trace": "data"}')

        # Verify structure
        assert dynamodb_dir.exists()
        assert s3_results_dir.exists()
        assert s3_reports_dir.exists()
        assert log_path.exists()
        assert trace_path.exists()

        # Verify hierarchy
        assert dynamodb_dir.parent.parent == manager.campaigns_dir
        assert s3_results_dir.parents[2] == manager.campaigns_dir
        assert log_path.parent == manager.logs_dir
        assert trace_path.parent == manager.traces_dir

    def test_multiple_campaigns_coexist(self, tmp_path, mock_settings):
        """Test multiple campaigns can coexist in same run."""
        mock_settings.app.evidence_report_output_dir = str(tmp_path / "evidence")
        manager = OutputManager(settings=mock_settings, run_timestamp="20250120T120000")
        manager.ensure_directories()

        campaign_ids = ["campaign-1", "campaign-2", "campaign-3"]

        for campaign_id in campaign_ids:
            campaign_dir = manager.get_campaign_dir(campaign_id)
            campaign_dir.mkdir(parents=True)

        # Verify all campaigns exist
        for campaign_id in campaign_ids:
            assert manager.get_campaign_dir(campaign_id).exists()

        # Verify they're all in the same campaigns directory
        created_campaigns = list(manager.campaigns_dir.iterdir())
        assert len(created_campaigns) == 3
