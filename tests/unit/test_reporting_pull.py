"""
Unit tests for reporting pull utilities.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.reporting.pull import _ensure_directory, _write_json, pull_campaign_data


class TestEnsureDirectory:
    """Test suite for _ensure_directory function"""

    def test_ensure_directory_creates_new_dir(self):
        """Test that _ensure_directory creates a new directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_dir"
            assert not test_path.exists()

            result = _ensure_directory(test_path)

            assert result.exists()
            assert result.is_dir()
            assert result == test_path

    def test_ensure_directory_idempotent(self):
        """Test that _ensure_directory is idempotent"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "test_dir"

            # Create directory first time
            result1 = _ensure_directory(test_path)
            # Create again
            result2 = _ensure_directory(test_path)

            assert result1 == result2
            assert result2.exists()

    def test_ensure_directory_creates_parents(self):
        """Test that _ensure_directory creates parent directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_path = Path(tmpdir) / "parent" / "child" / "grandchild"
            assert not test_path.exists()

            result = _ensure_directory(test_path)

            assert result.exists()
            assert result.parents[0].exists()  # child
            assert result.parents[1].exists()  # parent


class TestWriteJson:
    """Test suite for _write_json function"""

    def test_write_json_creates_file(self):
        """Test that _write_json creates a JSON file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            payload = {"key": "value", "number": 42}

            _write_json(test_file, payload)

            assert test_file.exists()
            content = json.loads(test_file.read_text())
            assert content["key"] == "value"
            assert content["number"] == 42

    def test_write_json_creates_parent_directories(self):
        """Test that _write_json creates parent directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "subdir1" / "subdir2" / "test.json"
            payload = {"data": "test"}

            _write_json(test_file, payload)

            assert test_file.exists()
            assert test_file.parent.exists()

    def test_write_json_formats_with_indent(self):
        """Test that _write_json formats JSON with indentation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            payload = {"nested": {"key": "value"}}

            _write_json(test_file, payload)

            content = test_file.read_text()
            # Check for indentation (formatted JSON)
            assert "\n" in content
            assert "  " in content  # 2-space indent

    def test_write_json_handles_complex_types(self):
        """Test that _write_json handles complex types with default=str"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"
            from datetime import datetime

            payload = {"timestamp": datetime(2024, 1, 1, 12, 0, 0), "path": Path("/some/path")}

            _write_json(test_file, payload)

            assert test_file.exists()
            content = json.loads(test_file.read_text())
            # Should be converted to strings
            assert isinstance(content["timestamp"], str)
            assert isinstance(content["path"], str)


class TestPullCampaignData:
    """Test suite for pull_campaign_data function"""

    @pytest.mark.asyncio
    async def test_pull_campaign_data_with_campaign_id(self):
        """Test pulling data for a specific campaign"""
        mock_container = MagicMock()
        mock_dynamodb = AsyncMock()
        mock_s3 = AsyncMock()

        mock_container.dynamodb.return_value = mock_dynamodb
        mock_container.s3.return_value = mock_s3

        # Mock campaign data
        mock_dynamodb.get_campaign = AsyncMock(
            return_value={"campaign_id": "camp-123", "status": "completed"}
        )
        mock_dynamodb.get_turns = AsyncMock(return_value=[])
        mock_dynamodb.get_evaluations = AsyncMock(return_value=[])
        mock_s3.list_objects = AsyncMock(return_value=[])
        mock_s3.results_bucket = "results-bucket"
        mock_s3.reports_bucket = "reports-bucket"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            result = await pull_campaign_data(
                container=mock_container, output_dir=output_dir, campaign_id="camp-123", limit=10
            )

            # Verify connections were established
            mock_dynamodb.connect.assert_called_once()
            mock_s3.connect.assert_called_once()

            # Verify campaign was fetched
            mock_dynamodb.get_campaign.assert_called_once_with("camp-123")

            # Verify directory structure was created
            campaign_dir = output_dir / "camp-123"
            assert campaign_dir.exists()
            assert (campaign_dir / "dynamodb").exists()

    @pytest.mark.asyncio
    async def test_pull_campaign_data_lists_campaigns_when_no_id(self):
        """Test pulling data for multiple campaigns"""
        mock_container = MagicMock()
        mock_dynamodb = AsyncMock()
        mock_s3 = AsyncMock()

        mock_container.dynamodb.return_value = mock_dynamodb
        mock_container.s3.return_value = mock_s3

        # Mock multiple campaigns
        mock_dynamodb.list_campaigns = AsyncMock(
            return_value=[{"campaign_id": "camp-1"}, {"campaign_id": "camp-2"}]
        )
        mock_dynamodb.get_turns = AsyncMock(return_value=[])
        mock_dynamodb.get_evaluations = AsyncMock(return_value=[])
        mock_s3.list_objects = AsyncMock(return_value=[])
        mock_s3.results_bucket = "results-bucket"
        mock_s3.reports_bucket = "reports-bucket"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            result = await pull_campaign_data(
                container=mock_container, output_dir=output_dir, campaign_id=None, limit=10
            )

            # Verify list_campaigns was called
            mock_dynamodb.list_campaigns.assert_called_once_with(limit=10, offset=0)

    @pytest.mark.asyncio
    async def test_pull_campaign_data_returns_empty_list_when_no_campaigns(self):
        """Test pulling data when no campaigns found"""
        mock_container = MagicMock()
        mock_dynamodb = AsyncMock()
        mock_s3 = AsyncMock()

        mock_container.dynamodb.return_value = mock_dynamodb
        mock_container.s3.return_value = mock_s3

        mock_dynamodb.get_campaign = AsyncMock(return_value=None)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            result = await pull_campaign_data(
                container=mock_container, output_dir=output_dir, campaign_id="nonexistent", limit=10
            )

            assert result == []

    @pytest.mark.asyncio
    async def test_pull_campaign_data_skips_invalid_campaigns(self):
        """Test pulling data skips campaigns without IDs"""
        mock_container = MagicMock()
        mock_dynamodb = AsyncMock()
        mock_s3 = AsyncMock()

        mock_container.dynamodb.return_value = mock_dynamodb
        mock_container.s3.return_value = mock_s3

        # Mock campaigns with missing data
        mock_dynamodb.list_campaigns = AsyncMock(
            return_value=[
                None,  # None campaign
                {},  # Campaign without ID
                {"campaign_id": "camp-valid"},  # Valid campaign
            ]
        )
        mock_dynamodb.get_turns = AsyncMock(return_value=[])
        mock_dynamodb.get_evaluations = AsyncMock(return_value=[])
        mock_s3.list_objects = AsyncMock(return_value=[])
        mock_s3.results_bucket = "results-bucket"
        mock_s3.reports_bucket = "reports-bucket"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            result = await pull_campaign_data(
                container=mock_container, output_dir=output_dir, campaign_id=None, limit=10
            )

            # Should only process the valid campaign
            assert (output_dir / "camp-valid").exists()
            # Invalid campaigns should not create directories
            assert not (output_dir / "None").exists()

    @pytest.mark.asyncio
    async def test_pull_campaign_data_downloads_s3_objects(self):
        """Test that S3 objects are downloaded"""
        mock_container = MagicMock()
        mock_dynamodb = AsyncMock()
        mock_s3 = AsyncMock()

        mock_container.dynamodb.return_value = mock_dynamodb
        mock_container.s3.return_value = mock_s3

        mock_dynamodb.get_campaign = AsyncMock(return_value={"campaign_id": "camp-123"})
        mock_dynamodb.get_turns = AsyncMock(return_value=[])
        mock_dynamodb.get_evaluations = AsyncMock(return_value=[])

        # Mock S3 objects
        mock_s3.list_objects = AsyncMock(
            side_effect=[
                [{"key": "campaigns/camp-123/result1.json"}],  # results
                [{"key": "reports/camp-123/report1.html"}],  # reports
            ]
        )
        mock_s3.download_object = AsyncMock(return_value=Path("/tmp/downloaded.json"))
        mock_s3.results_bucket = "results-bucket"
        mock_s3.reports_bucket = "reports-bucket"

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            result = await pull_campaign_data(
                container=mock_container, output_dir=output_dir, campaign_id="camp-123", limit=10
            )

            # Verify download was called
            assert mock_s3.download_object.call_count == 2
            assert len(result) == 2  # 2 files downloaded
