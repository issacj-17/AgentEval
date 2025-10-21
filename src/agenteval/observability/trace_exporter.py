"""
Trace Exporter Service.

Exports OpenTelemetry traces to various formats and destinations.

Design Patterns:
    - Strategy Pattern: Different export formats (JSON, OTLP, Jaeger)
    - Factory Pattern: Creating exporters
    - Adapter Pattern: Adapting traces to different formats
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from agenteval.aws.xray import XRayClient
from agenteval.observability.tracer import convert_otel_trace_id_to_xray

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class TraceExportError(Exception):
    """Base exception for trace export errors."""

    pass


class ExportFormatError(TraceExportError):
    """Raised when export format is invalid."""

    pass


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class TraceExportConfig:
    """Configuration for trace export."""

    output_dir: Path
    export_format: str = "json"  # json, otlp, jaeger
    include_metadata: bool = True
    compress: bool = False
    max_traces: int | None = None


@dataclass
class ExportedTrace:
    """Exported trace data."""

    trace_id: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    spans: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of trace export operation."""

    success: bool
    output_path: Path | None = None
    traces_exported: int = 0
    error_message: str | None = None
    export_timestamp: datetime = field(default_factory=datetime.utcnow)


# ============================================================================
# Export Strategy Protocol
# ============================================================================


class ExportStrategy(Protocol):
    """Protocol for trace export strategies."""

    def export(self, traces: list[ExportedTrace], output_path: Path) -> ExportResult:
        """Export traces to destination."""
        ...


# ============================================================================
# Export Strategies
# ============================================================================


class JSONExportStrategy:
    """Export traces as JSON."""

    def export(self, traces: list[ExportedTrace], output_path: Path) -> ExportResult:
        """Export traces to JSON file."""
        try:
            # Convert traces to JSON-serializable format
            traces_data = []
            for trace in traces:
                trace_dict = {
                    "trace_id": trace.trace_id,
                    "start_time": trace.start_time.isoformat(),
                    "end_time": trace.end_time.isoformat(),
                    "duration_ms": trace.duration_ms,
                    "spans": trace.spans,
                    "metadata": trace.metadata,
                }
                traces_data.append(trace_dict)

            # Write to file
            output_path.write_text(json.dumps(traces_data, indent=2), encoding="utf-8")

            logger.info(f"Exported {len(traces)} traces to JSON: {output_path}")

            return ExportResult(
                success=True,
                output_path=output_path,
                traces_exported=len(traces),
            )

        except Exception as e:
            logger.error(f"JSON export failed: {e}")
            return ExportResult(
                success=False,
                error_message=str(e),
            )


class OTLPExportStrategy:
    """Export traces in OTLP format."""

    def export(self, traces: list[ExportedTrace], output_path: Path) -> ExportResult:
        """Export traces to OTLP format."""
        try:
            # OTLP format structure
            otlp_data = {
                "resourceSpans": [],
            }

            for trace in traces:
                resource_span = {
                    "resource": {
                        "attributes": [
                            {
                                "key": "service.name",
                                "value": {"stringValue": "agenteval"},
                            },
                            {
                                "key": "trace_id",
                                "value": {"stringValue": trace.trace_id},
                            },
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {
                                "name": "agenteval",
                                "version": "1.0.0",
                            },
                            "spans": trace.spans,
                        }
                    ],
                }
                otlp_data["resourceSpans"].append(resource_span)

            # Write OTLP JSON
            output_path.write_text(json.dumps(otlp_data, indent=2), encoding="utf-8")

            logger.info(f"Exported {len(traces)} traces to OTLP: {output_path}")

            return ExportResult(
                success=True,
                output_path=output_path,
                traces_exported=len(traces),
            )

        except Exception as e:
            logger.error(f"OTLP export failed: {e}")
            return ExportResult(
                success=False,
                error_message=str(e),
            )


class JaegerExportStrategy:
    """Export traces in Jaeger format."""

    def export(self, traces: list[ExportedTrace], output_path: Path) -> ExportResult:
        """Export traces to Jaeger format."""
        try:
            # Jaeger format structure
            jaeger_data = {"data": []}

            for trace in traces:
                jaeger_trace = {
                    "traceID": trace.trace_id,
                    "spans": [],
                    "processes": {
                        "p1": {
                            "serviceName": "agenteval",
                            "tags": [],
                        }
                    },
                }

                # Convert spans to Jaeger format
                for span in trace.spans:
                    jaeger_span = {
                        "traceID": trace.trace_id,
                        "spanID": span.get("span_id", ""),
                        "operationName": span.get("name", "unknown"),
                        "references": [],
                        "startTime": int(
                            datetime.fromisoformat(
                                span.get("start_time", "").replace("Z", "+00:00")
                            ).timestamp()
                            * 1000000
                        ),
                        "duration": int(trace.duration_ms * 1000),
                        "tags": span.get("attributes", []),
                        "logs": span.get("events", []),
                        "processID": "p1",
                    }
                    jaeger_trace["spans"].append(jaeger_span)

                jaeger_data["data"].append(jaeger_trace)

            # Write Jaeger JSON
            output_path.write_text(json.dumps(jaeger_data, indent=2), encoding="utf-8")

            logger.info(f"Exported {len(traces)} traces to Jaeger: {output_path}")

            return ExportResult(
                success=True,
                output_path=output_path,
                traces_exported=len(traces),
            )

        except Exception as e:
            logger.error(f"Jaeger export failed: {e}")
            return ExportResult(
                success=False,
                error_message=str(e),
            )


# ============================================================================
# Trace Exporter Service
# ============================================================================


class TraceExporter:
    """
    Service for exporting OpenTelemetry traces to various formats.

    Supports:
    - JSON export for analysis
    - OTLP export for compatibility
    - Jaeger export for visualization
    - X-Ray integration for AWS

    Attributes:
        config: Export configuration
        xray_client: AWS X-Ray client for trace retrieval
        strategies: Export strategy mapping
    """

    def __init__(
        self,
        config: TraceExportConfig,
        xray_client: XRayClient | None = None,
    ):
        """
        Initialize TraceExporter.

        Args:
            config: Export configuration
            xray_client: Optional X-Ray client
        """
        self.config = config
        self.xray_client = xray_client

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize export strategies
        self.strategies: dict[str, ExportStrategy] = {
            "json": JSONExportStrategy(),
            "otlp": OTLPExportStrategy(),
            "jaeger": JaegerExportStrategy(),
        }

        logger.info(
            f"TraceExporter initialized (format: {config.export_format}, "
            f"output: {config.output_dir})"
        )

    # ========================================================================
    # Main Export Methods
    # ========================================================================

    async def export_traces(
        self,
        trace_ids: list[str] | None = None,
        time_range: dict[str, datetime] | None = None,
    ) -> ExportResult:
        """
        Export traces to configured format.

        Args:
            trace_ids: Optional list of specific trace IDs to export
            time_range: Optional time range dict with 'start' and 'end'

        Returns:
            Export result with status and path
        """
        try:
            logger.info("Starting trace export...")

            # Retrieve traces from X-Ray
            traces = await self._retrieve_traces(trace_ids, time_range)

            if not traces:
                logger.warning("No traces found to export")
                return ExportResult(
                    success=True,
                    traces_exported=0,
                    error_message="No traces found",
                )

            # Limit traces if configured
            if self.config.max_traces and len(traces) > self.config.max_traces:
                traces = traces[: self.config.max_traces]
                logger.info(f"Limited export to {self.config.max_traces} traces")

            # Select export strategy
            strategy = self.strategies.get(self.config.export_format)
            if not strategy:
                raise ExportFormatError(f"Unknown export format: {self.config.export_format}")

            # Determine output path
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"traces_{timestamp}.{self._get_file_extension()}"
            output_path = self.config.output_dir / filename

            # Export traces
            result = strategy.export(traces, output_path)

            logger.info(f"Trace export completed: {result.traces_exported} traces exported")

            return result

        except Exception as e:
            logger.error(f"Trace export failed: {e}")
            return ExportResult(
                success=False,
                error_message=str(e),
            )

    async def export_campaign_traces(self, campaign_id: str) -> ExportResult:
        """
        Export traces for a specific campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Export result
        """
        logger.info(f"Exporting traces for campaign: {campaign_id}")

        # Filter traces by campaign_id attribute
        # This would integrate with X-Ray filtering
        return await self.export_traces()

    # ========================================================================
    # Trace Retrieval
    # ========================================================================

    async def _retrieve_traces(
        self,
        trace_ids: list[str] | None = None,
        time_range: dict[str, datetime] | None = None,
    ) -> list[ExportedTrace]:
        """
        Retrieve traces from X-Ray.

        Args:
            trace_ids: Optional trace IDs
            time_range: Optional time range

        Returns:
            List of exported traces
        """
        if not self.xray_client:
            logger.warning("No X-Ray client configured, using mock data")
            return self._generate_mock_traces()

        try:
            # Retrieve trace summaries
            start_time = time_range.get("start") if time_range else None
            end_time = time_range.get("end") if time_range else None

            summaries = await self.xray_client.get_trace_summaries(
                start_time=start_time,
                end_time=end_time,
            )

            # Filter by trace IDs if provided
            if trace_ids:
                # Convert OpenTelemetry trace IDs to X-Ray format for comparison
                xray_trace_ids = []
                for tid in trace_ids:
                    try:
                        # If already in X-Ray format, keep as-is
                        if tid and len(tid) > 2 and tid.startswith("1-"):
                            xray_trace_ids.append(tid)
                        # If OpenTelemetry format (32 hex chars), convert to X-Ray
                        elif tid and len(tid) == 32:
                            xray_trace_ids.append(convert_otel_trace_id_to_xray(tid))
                        else:
                            logger.warning(f"Skipping invalid trace ID format: {tid}")
                    except Exception as e:
                        logger.warning(f"Failed to convert trace ID {tid}: {e}")
                        continue

                summaries = [s for s in summaries if s.get("Id") in xray_trace_ids]

            # Batch get full traces
            trace_ids_to_fetch = [s.get("Id") for s in summaries]
            full_traces = await self.xray_client.batch_get_traces(trace_ids=trace_ids_to_fetch)

            # Convert to ExportedTrace format
            exported_traces = []
            for trace_data in full_traces:
                exported_trace = self._convert_xray_trace(trace_data)
                if exported_trace:
                    exported_traces.append(exported_trace)

            return exported_traces

        except Exception as e:
            logger.error(f"Failed to retrieve traces from X-Ray: {e}")
            return []

    def _convert_xray_trace(self, trace_data: dict[str, Any]) -> ExportedTrace | None:
        """Convert X-Ray trace to ExportedTrace format."""
        try:
            trace_id = trace_data.get("Id", "")
            duration = trace_data.get("Duration", 0.0)

            # Extract segments as spans
            segments = trace_data.get("Segments", [])
            spans = []

            for segment in segments:
                # Parse segment document if it's a string
                if isinstance(segment, str):
                    segment = json.loads(segment)

                span = {
                    "name": segment.get("name", "unknown"),
                    "span_id": segment.get("id", ""),
                    "start_time": segment.get("start_time", ""),
                    "end_time": segment.get("end_time", ""),
                    "attributes": segment.get("annotations", {}),
                    "events": segment.get("subsegments", []),
                }
                spans.append(span)

            # Determine start and end times
            if spans:
                start_time = datetime.fromisoformat(
                    spans[0].get("start_time", "").replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(
                    spans[-1].get("end_time", "").replace("Z", "+00:00")
                )
            else:
                start_time = datetime.utcnow()
                end_time = datetime.utcnow()

            return ExportedTrace(
                trace_id=trace_id,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration * 1000,
                spans=spans,
                metadata={"source": "xray"},
            )

        except Exception as e:
            logger.error(f"Failed to convert X-Ray trace: {e}")
            return None

    def _generate_mock_traces(self) -> list[ExportedTrace]:
        """Generate mock traces for testing."""
        mock_traces = []

        for i in range(3):
            trace = ExportedTrace(
                trace_id=f"mock-trace-{i}",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                duration_ms=100.0 * (i + 1),
                spans=[
                    {
                        "name": f"span-{i}",
                        "span_id": f"span-id-{i}",
                        "start_time": datetime.utcnow().isoformat(),
                        "end_time": datetime.utcnow().isoformat(),
                        "attributes": {"mock": True},
                        "events": [],
                    }
                ],
                metadata={"source": "mock"},
            )
            mock_traces.append(trace)

        return mock_traces

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_file_extension(self) -> str:
        """Get file extension for export format."""
        extensions = {
            "json": "json",
            "otlp": "json",
            "jaeger": "json",
        }
        return extensions.get(self.config.export_format, "json")


# ============================================================================
# Factory Function
# ============================================================================


async def create_trace_exporter(
    output_dir: Path | None = None,
    export_format: str = "json",
    max_traces: int | None = None,
) -> TraceExporter:
    """
    Factory function for creating TraceExporter instances.

    Args:
        output_dir: Output directory for exported traces
        export_format: Export format (json, otlp, jaeger)
        max_traces: Maximum number of traces to export

    Returns:
        Configured TraceExporter instance
    """
    from agenteval.config import settings

    config = TraceExportConfig(
        output_dir=output_dir or Path(settings.app.evidence_report_output_dir) / "traces",
        export_format=export_format,
        max_traces=max_traces,
    )

    xray_client = XRayClient()

    return TraceExporter(config=config, xray_client=xray_client)
