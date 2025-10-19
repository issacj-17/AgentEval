"""
Unit tests for TraceExporter.

Tests the TraceExporter service with all export strategies.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from agenteval.observability.trace_exporter import (
    ExportedTrace,
    ExportResult,
    JaegerExportStrategy,
    JSONExportStrategy,
    OTLPExportStrategy,
    TraceExportConfig,
    TraceExporter,
)


@pytest.fixture
def trace_config(tmp_path):
    """Create trace export configuration."""
    return TraceExportConfig(
        output_dir=tmp_path / "traces",
        export_format="json",
        max_traces=10,
    )


@pytest.fixture
def mock_xray_client():
    """Create mock X-Ray client."""
    client = MagicMock()
    client.get_trace_summaries = AsyncMock()
    client.batch_get_traces = AsyncMock()
    return client


@pytest.fixture
def trace_exporter(trace_config, mock_xray_client):
    """Create TraceExporter instance."""
    return TraceExporter(
        config=trace_config,
        xray_client=mock_xray_client,
    )


@pytest.fixture
def sample_exported_traces():
    """Sample exported traces."""
    return [
        ExportedTrace(
            trace_id="trace-1",
            start_time=datetime(2025, 1, 1, 10, 0, 0),
            end_time=datetime(2025, 1, 1, 10, 0, 5),
            duration_ms=5000.0,
            spans=[
                {
                    "name": "operation-1",
                    "span_id": "span-1",
                    "start_time": "2025-01-01T10:00:00Z",
                    "end_time": "2025-01-01T10:00:05Z",
                    "attributes": {"service": "agenteval"},
                    "events": [],
                }
            ],
            metadata={"source": "xray"},
        ),
        ExportedTrace(
            trace_id="trace-2",
            start_time=datetime(2025, 1, 1, 11, 0, 0),
            end_time=datetime(2025, 1, 1, 11, 0, 3),
            duration_ms=3000.0,
            spans=[
                {
                    "name": "operation-2",
                    "span_id": "span-2",
                    "start_time": "2025-01-01T11:00:00Z",
                    "end_time": "2025-01-01T11:00:03Z",
                    "attributes": {"service": "agenteval"},
                    "events": [],
                }
            ],
            metadata={"source": "xray"},
        ),
    ]


class TestTraceExportConfig:
    """Test suite for TraceExportConfig."""

    def test_default_config(self, tmp_path):
        """Test default configuration values."""
        config = TraceExportConfig(output_dir=tmp_path)

        assert config.output_dir == tmp_path
        assert config.export_format == "json"
        assert config.include_metadata is True
        assert config.compress is False
        assert config.max_traces is None

    def test_custom_config(self, tmp_path):
        """Test custom configuration."""
        config = TraceExportConfig(
            output_dir=tmp_path,
            export_format="otlp",
            include_metadata=False,
            compress=True,
            max_traces=100,
        )

        assert config.export_format == "otlp"
        assert config.include_metadata is False
        assert config.compress is True
        assert config.max_traces == 100


class TestJSONExportStrategy:
    """Test suite for JSON export strategy."""

    def test_export_success(self, tmp_path, sample_exported_traces):
        """Test successful JSON export."""
        strategy = JSONExportStrategy()
        output_path = tmp_path / "traces.json"

        result = strategy.export(sample_exported_traces, output_path)

        # Verify result
        assert result.success is True
        assert result.output_path == output_path
        assert result.traces_exported == 2
        assert result.error_message is None

        # Verify file was created
        assert output_path.exists()

        # Verify JSON content
        content = json.loads(output_path.read_text())
        assert isinstance(content, list)
        assert len(content) == 2
        assert content[0]["trace_id"] == "trace-1"
        assert content[1]["trace_id"] == "trace-2"

    def test_export_with_metadata(self, tmp_path, sample_exported_traces):
        """Test JSON export includes metadata."""
        strategy = JSONExportStrategy()
        output_path = tmp_path / "traces.json"

        strategy.export(sample_exported_traces, output_path)

        content = json.loads(output_path.read_text())
        assert content[0]["metadata"]["source"] == "xray"

    def test_export_failure(self, sample_exported_traces):
        """Test JSON export handles errors."""
        strategy = JSONExportStrategy()
        invalid_path = Path("/invalid/directory/traces.json")

        result = strategy.export(sample_exported_traces, invalid_path)

        assert result.success is False
        assert result.error_message is not None
        assert result.traces_exported == 0


class TestOTLPExportStrategy:
    """Test suite for OTLP export strategy."""

    def test_export_success(self, tmp_path, sample_exported_traces):
        """Test successful OTLP export."""
        strategy = OTLPExportStrategy()
        output_path = tmp_path / "traces.otlp.json"

        result = strategy.export(sample_exported_traces, output_path)

        # Verify result
        assert result.success is True
        assert result.output_path == output_path
        assert result.traces_exported == 2

        # Verify file was created
        assert output_path.exists()

        # Verify OTLP structure
        content = json.loads(output_path.read_text())
        assert "resourceSpans" in content
        assert len(content["resourceSpans"]) == 2

    def test_otlp_format_structure(self, tmp_path, sample_exported_traces):
        """Test OTLP format has correct structure."""
        strategy = OTLPExportStrategy()
        output_path = tmp_path / "traces.otlp.json"

        strategy.export(sample_exported_traces, output_path)

        content = json.loads(output_path.read_text())
        resource_span = content["resourceSpans"][0]

        # Verify OTLP structure
        assert "resource" in resource_span
        assert "scopeSpans" in resource_span
        assert "attributes" in resource_span["resource"]

        # Verify service name attribute
        attrs = resource_span["resource"]["attributes"]
        service_name_attr = next((a for a in attrs if a["key"] == "service.name"), None)
        assert service_name_attr is not None
        assert service_name_attr["value"]["stringValue"] == "agenteval"

    def test_export_failure(self, sample_exported_traces):
        """Test OTLP export handles errors."""
        strategy = OTLPExportStrategy()
        invalid_path = Path("/invalid/directory/traces.otlp.json")

        result = strategy.export(sample_exported_traces, invalid_path)

        assert result.success is False
        assert result.error_message is not None


class TestJaegerExportStrategy:
    """Test suite for Jaeger export strategy."""

    def test_export_success(self, tmp_path, sample_exported_traces):
        """Test successful Jaeger export."""
        strategy = JaegerExportStrategy()
        output_path = tmp_path / "traces.jaeger.json"

        result = strategy.export(sample_exported_traces, output_path)

        # Verify result
        assert result.success is True
        assert result.output_path == output_path
        assert result.traces_exported == 2

        # Verify file was created
        assert output_path.exists()

        # Verify Jaeger structure
        content = json.loads(output_path.read_text())
        assert "data" in content
        assert len(content["data"]) == 2

    def test_jaeger_format_structure(self, tmp_path, sample_exported_traces):
        """Test Jaeger format has correct structure."""
        strategy = JaegerExportStrategy()
        output_path = tmp_path / "traces.jaeger.json"

        strategy.export(sample_exported_traces, output_path)

        content = json.loads(output_path.read_text())
        trace = content["data"][0]

        # Verify Jaeger structure
        assert "traceID" in trace
        assert "spans" in trace
        assert "processes" in trace
        assert "p1" in trace["processes"]
        assert trace["processes"]["p1"]["serviceName"] == "agenteval"

    def test_export_failure(self, sample_exported_traces):
        """Test Jaeger export handles errors."""
        strategy = JaegerExportStrategy()
        invalid_path = Path("/invalid/directory/traces.jaeger.json")

        result = strategy.export(sample_exported_traces, invalid_path)

        assert result.success is False
        assert result.error_message is not None


class TestTraceExporter:
    """Test suite for TraceExporter."""

    def test_initialization(self, trace_exporter, tmp_path):
        """Test exporter initialization."""
        assert trace_exporter.config.output_dir.exists()
        assert trace_exporter.xray_client is not None
        assert len(trace_exporter.strategies) == 3
        assert "json" in trace_exporter.strategies
        assert "otlp" in trace_exporter.strategies
        assert "jaeger" in trace_exporter.strategies

    def test_initialization_without_xray(self, trace_config):
        """Test initialization without X-Ray client."""
        exporter = TraceExporter(config=trace_config, xray_client=None)
        assert exporter.xray_client is None

    @pytest.mark.asyncio
    async def test_export_traces_with_xray(self, trace_exporter, mock_xray_client):
        """Test exporting traces from X-Ray."""
        # Setup mocks
        mock_xray_client.get_trace_summaries.return_value = [
            {"Id": "trace-1", "Duration": 5.0},
            {"Id": "trace-2", "Duration": 3.0},
        ]
        mock_xray_client.batch_get_traces.return_value = [
            {
                "Id": "trace-1",
                "Duration": 5.0,
                "Segments": [
                    json.dumps(
                        {
                            "name": "operation-1",
                            "id": "span-1",
                            "start_time": "2025-01-01T10:00:00Z",
                            "end_time": "2025-01-01T10:00:05Z",
                        }
                    )
                ],
            },
            {
                "Id": "trace-2",
                "Duration": 3.0,
                "Segments": [
                    json.dumps(
                        {
                            "name": "operation-2",
                            "id": "span-2",
                            "start_time": "2025-01-01T11:00:00Z",
                            "end_time": "2025-01-01T11:00:03Z",
                        }
                    )
                ],
            },
        ]

        # Execute
        result = await trace_exporter.export_traces()

        # Verify
        assert result.success is True
        assert result.traces_exported == 2
        assert result.output_path.exists()

        # Verify X-Ray was called
        mock_xray_client.get_trace_summaries.assert_called_once()
        mock_xray_client.batch_get_traces.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_traces_without_xray(self, trace_config):
        """Test exporting traces without X-Ray (mock data)."""
        exporter = TraceExporter(config=trace_config, xray_client=None)

        result = await exporter.export_traces()

        # Should use mock data
        assert result.success is True
        assert result.traces_exported == 3  # Mock generates 3 traces
        assert "mock" in str(result.output_path.read_text())

    @pytest.mark.asyncio
    async def test_export_traces_with_max_limit(self, trace_exporter, mock_xray_client):
        """Test exporting traces with max limit."""
        # Configure for max 2 traces
        trace_exporter.config.max_traces = 2

        # Setup mock to return 5 traces
        mock_xray_client.get_trace_summaries.return_value = [
            {"Id": f"trace-{i}", "Duration": 1.0} for i in range(5)
        ]
        mock_xray_client.batch_get_traces.return_value = [
            {
                "Id": f"trace-{i}",
                "Duration": 1.0,
                "Segments": [
                    json.dumps(
                        {
                            "name": f"op-{i}",
                            "id": f"span-{i}",
                            "start_time": "2025-01-01T10:00:00Z",
                            "end_time": "2025-01-01T10:00:01Z",
                        }
                    )
                ],
            }
            for i in range(5)
        ]

        # Execute
        result = await trace_exporter.export_traces()

        # Verify limited to 2 traces
        assert result.traces_exported == 2

    @pytest.mark.asyncio
    async def test_export_traces_empty(self, trace_exporter, mock_xray_client):
        """Test exporting when no traces found."""
        mock_xray_client.get_trace_summaries.return_value = []
        mock_xray_client.batch_get_traces.return_value = []

        result = await trace_exporter.export_traces()

        assert result.success is True
        assert result.traces_exported == 0
        assert result.error_message == "No traces found"

    @pytest.mark.asyncio
    async def test_export_traces_with_invalid_format(self, trace_exporter, mock_xray_client):
        """Test export with invalid format."""
        trace_exporter.config.export_format = "invalid"

        mock_xray_client.get_trace_summaries.return_value = [{"Id": "trace-1", "Duration": 1.0}]
        mock_xray_client.batch_get_traces.return_value = [
            {
                "Id": "trace-1",
                "Duration": 1.0,
                "Segments": [],
            }
        ]

        result = await trace_exporter.export_traces()

        # Should fail with format error
        assert result.success is False
        assert "Unknown export format" in result.error_message

    @pytest.mark.asyncio
    async def test_export_campaign_traces(self, trace_exporter, mock_xray_client):
        """Test exporting traces for specific campaign."""
        mock_xray_client.get_trace_summaries.return_value = []
        mock_xray_client.batch_get_traces.return_value = []

        result = await trace_exporter.export_campaign_traces("campaign-123")

        assert isinstance(result, ExportResult)

    def test_get_file_extension(self, trace_exporter):
        """Test getting file extension for different formats."""
        assert trace_exporter._get_file_extension() == "json"

        trace_exporter.config.export_format = "otlp"
        assert trace_exporter._get_file_extension() == "json"

        trace_exporter.config.export_format = "jaeger"
        assert trace_exporter._get_file_extension() == "json"

        trace_exporter.config.export_format = "unknown"
        assert trace_exporter._get_file_extension() == "json"

    def test_generate_mock_traces(self, trace_exporter):
        """Test mock trace generation."""
        mock_traces = trace_exporter._generate_mock_traces()

        assert len(mock_traces) == 3
        assert all(isinstance(t, ExportedTrace) for t in mock_traces)
        assert all(t.trace_id.startswith("mock-trace-") for t in mock_traces)
        assert all(t.metadata["source"] == "mock" for t in mock_traces)

    def test_convert_xray_trace_success(self, trace_exporter):
        """Test converting X-Ray trace to ExportedTrace."""
        xray_trace = {
            "Id": "trace-123",
            "Duration": 5.5,
            "Segments": [
                json.dumps(
                    {
                        "name": "test-operation",
                        "id": "segment-123",
                        "start_time": "2025-01-01T10:00:00Z",
                        "end_time": "2025-01-01T10:00:05Z",
                        "annotations": {"key": "value"},
                        "subsegments": [],
                    }
                )
            ],
        }

        exported_trace = trace_exporter._convert_xray_trace(xray_trace)

        assert exported_trace is not None
        assert exported_trace.trace_id == "trace-123"
        assert exported_trace.duration_ms == 5500.0
        assert len(exported_trace.spans) == 1
        assert exported_trace.spans[0]["name"] == "test-operation"

    def test_convert_xray_trace_with_error(self, trace_exporter):
        """Test converting invalid X-Ray trace."""
        invalid_trace = {"Id": "trace-123"}  # Missing required fields

        exported_trace = trace_exporter._convert_xray_trace(invalid_trace)

        # Code handles missing fields gracefully, returns trace with empty spans
        assert exported_trace is not None
        assert exported_trace.trace_id == "trace-123"
        assert len(exported_trace.spans) == 0
        assert exported_trace.duration_ms == 0.0
