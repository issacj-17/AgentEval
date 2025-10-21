"""
OpenTelemetry Tracing Setup

Provides distributed tracing infrastructure for AgentEval.
Critical for the SECRET SAUCE - correlating evaluation scores with traces.
"""

import logging
import socket
from contextlib import contextmanager
from urllib.parse import urlparse

from opentelemetry import baggage, trace
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import get_global_textmap, set_global_textmap
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import Span, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from agenteval.config import settings

logger = logging.getLogger(__name__)


class TracerSetup:
    """OpenTelemetry Tracer Setup and Management"""

    def __init__(self) -> None:
        self.provider: TracerProvider | None = None
        self.tracer: trace.Tracer | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize OpenTelemetry tracing"""
        if self._initialized:
            logger.debug("Tracer already initialized, skipping")
            return

        try:
            if not settings.observability.enable_tracing:
                logger.info("Tracing disabled in configuration")
                return

            # Create resource with service information
            resource = Resource.create(
                {
                    SERVICE_NAME: "agenteval",
                    SERVICE_VERSION: "1.0.0",
                    "environment": settings.app.environment,
                }
            )

            # Create tracer provider
            self.provider = TracerProvider(resource=resource)

            # Add OTLP exporter for production
            if settings.is_production or settings.app.environment != "test":
                endpoint = settings.observability.otel_collector_endpoint
                if endpoint and self._endpoint_reachable(endpoint):
                    url = urlparse(endpoint)
                    insecure = url.scheme != "https"
                    try:
                        otlp_exporter = OTLPSpanExporter(
                            endpoint=endpoint,
                            insecure=insecure,
                            timeout=5,
                        )
                        self.provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                        logger.info("OTLP exporter configured: %s", endpoint)
                    except Exception as exc:  # noqa: BLE001
                        logger.warning(
                            "Failed to initialise OTLP exporter for %s (%s). "
                            "Trace export will fall back to console only.",
                            endpoint,
                            exc,
                        )
                else:
                    if endpoint:
                        logger.info(
                            "OTLP endpoint %s is unreachable; skipping gRPC exporter. "
                            "Set OTEL_COLLECTOR_ENDPOINT to a reachable host to enable export.",
                            endpoint,
                        )
                    else:
                        logger.info("No OTLP endpoint configured, skipping trace export")

            # Add console exporter for development
            if settings.is_development:
                try:
                    console_exporter = ConsoleSpanExporter()
                    self.provider.add_span_processor(BatchSpanProcessor(console_exporter))
                    logger.info("Console span exporter enabled for development")
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to configure console exporter: %s", exc)

            # Set global tracer provider
            trace.set_tracer_provider(self.provider)

            # Configure composite propagator (W3C Trace Context + Baggage)
            composite_propagator = CompositePropagator(
                [TraceContextTextMapPropagator(), W3CBaggagePropagator()]
            )
            set_global_textmap(composite_propagator)
            logger.info("Configured composite propagator (traceparent + baggage)")

            # Create tracer
            self.tracer = trace.get_tracer(__name__)

            # Auto-instrument common libraries
            try:
                FastAPIInstrumentor().instrument()
                HTTPXClientInstrumentor().instrument()
                logger.info("Instrumented FastAPI and HTTPX")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to instrument libraries: %s", exc)

            self._initialized = True
            logger.info("OpenTelemetry tracing initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
            # Don't re-raise - allow system to continue without tracing
            self._initialized = False

    @staticmethod
    def _endpoint_reachable(endpoint: str) -> bool:
        """Return True when the OTLP endpoint host:port appears reachable."""
        if not endpoint:
            return False
        try:
            url = urlparse(endpoint)
            host = url.hostname
            port = url.port or (443 if url.scheme == "https" else 4317)
            if not host or not port:
                return False
            with socket.create_connection((host, port), timeout=1.5):
                return True
        except OSError:
            return False

    def shutdown(self) -> None:
        """Shutdown tracing and flush remaining spans"""
        if self.provider:
            try:
                # Force flush before shutdown to ensure all spans are exported
                self.provider.force_flush(timeout_millis=5000)
                logger.info("Flushed pending spans")
            except Exception as e:
                logger.warning(f"Failed to flush spans: {e}")

            try:
                self.provider.shutdown()
                logger.info("Tracer provider shut down")
            except Exception as e:
                logger.error(f"Error during tracer shutdown: {e}")

            self._initialized = False

    def get_tracer(self) -> trace.Tracer:
        """Get the tracer instance"""
        if not self._initialized:
            self.initialize()
        return self.tracer or trace.get_tracer(__name__)

    def force_flush(self, timeout_millis: int = 5000) -> bool:
        """
        Force flush any pending spans to exporters

        Args:
            timeout_millis: Maximum time to wait for flush in milliseconds

        Returns:
            True if flush was successful, False otherwise
        """
        if self.provider:
            try:
                result = self.provider.force_flush(timeout_millis=timeout_millis)
                logger.debug("Force flushed spans")
                return result
            except Exception as e:
                logger.warning(f"Failed to force flush spans: {e}")
                return False
        return False


# Global tracer setup instance
tracer_setup = TracerSetup()


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance"""
    return tracer_setup.get_tracer()


def create_span(name: str, attributes: dict | None = None, parent: Span | None = None) -> Span:
    """
    Create a new span

    Args:
        name: Span name
        attributes: Optional span attributes
        parent: Optional parent span

    Returns:
        New span
    """
    tracer = get_tracer()

    context = trace.set_span_in_context(parent) if parent else None

    span = tracer.start_span(name, context=context)

    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    return span


@contextmanager
def trace_operation(operation_name: str, **attributes):
    """
    Context manager for tracing operations

    Usage:
        with trace_operation("persona_interaction", persona_type="frustrated"):
            # Your code here
            pass
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(operation_name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        yield span


def get_current_trace_id() -> str | None:
    """Get the current trace ID in OpenTelemetry format (32-character hex)"""
    span = trace.get_current_span()
    if span and span.is_recording():
        trace_id = format(span.get_span_context().trace_id, "032x")
        return trace_id
    return None


def convert_otel_trace_id_to_xray(otel_trace_id: str) -> str:
    """
    Convert OpenTelemetry trace ID to AWS X-Ray format.

    OpenTelemetry format: 32-character hexadecimal string
    Example: "0af7651916cd43dd8448eb211c80319c"  # pragma: allowlist secret

    AWS X-Ray format: 1-{8-hex-timestamp}-{24-hex-unique-id}
    Example: "1-0af76519-16cd43dd8448eb211c80319c"

    Args:
        otel_trace_id: OpenTelemetry trace ID (32 hex characters)

    Returns:
        X-Ray formatted trace ID
    """
    if not otel_trace_id or len(otel_trace_id) != 32:
        raise ValueError(f"Invalid OpenTelemetry trace ID: {otel_trace_id}")

    # Split the 32-character trace ID into timestamp (8 chars) and unique ID (24 chars)
    timestamp_hex = otel_trace_id[:8]
    unique_id_hex = otel_trace_id[8:]

    return f"1-{timestamp_hex}-{unique_id_hex}"


def get_current_xray_trace_id() -> str | None:
    """
    Get the current trace ID in AWS X-Ray format.

    Converts OpenTelemetry trace ID to X-Ray format for use with X-Ray APIs.

    Returns:
        X-Ray formatted trace ID (1-{8hex}-{24hex}) or None if no active span
    """
    otel_trace_id = get_current_trace_id()
    if otel_trace_id:
        return convert_otel_trace_id_to_xray(otel_trace_id)
    return None


def get_current_span_id() -> str | None:
    """Get the current span ID"""
    span = trace.get_current_span()
    if span and span.is_recording():
        span_id = format(span.get_span_context().span_id, "016x")
        return span_id
    return None


def inject_trace_context(headers: dict) -> dict:
    """
    Inject W3C Trace Context and Baggage into HTTP headers

    Uses global composite propagator configured at initialization.

    Args:
        headers: Existing headers dict

    Returns:
        Headers with trace context and baggage injected
    """
    propagator = get_global_textmap()
    propagator.inject(headers)
    return headers


def extract_trace_context(headers: dict) -> trace.Context:
    """
    Extract W3C Trace Context and Baggage from HTTP headers

    Args:
        headers: HTTP headers

    Returns:
        OpenTelemetry context
    """
    propagator = get_global_textmap()
    return propagator.extract(headers)


def set_baggage(key: str, value: str) -> None:
    """
    Set a baggage value in the current context

    Baggage is propagated across service boundaries with traces.
    Use for campaign_id, agent_id, turn_number, etc.

    Args:
        key: Baggage key
        value: Baggage value (must be string)
    """
    baggage.set_baggage(key, str(value))


def get_baggage(key: str) -> str | None:
    """
    Get a baggage value from the current context

    Args:
        key: Baggage key

    Returns:
        Baggage value or None if not found
    """
    return baggage.get_baggage(key)


def inject_baggage_dict(headers: dict, baggage_dict: dict) -> dict:
    """
    Inject multiple baggage key-value pairs into headers

    Args:
        headers: Existing headers dict
        baggage_dict: Dictionary of baggage key-value pairs

    Returns:
        Headers with baggage injected
    """
    # Set baggage in context
    for key, value in baggage_dict.items():
        set_baggage(key, str(value))

    # Inject into headers
    return inject_trace_context(headers)


def build_traceparent_header() -> str:
    """
    Build W3C traceparent header

    Format: version-trace_id-span_id-trace_flags
    Example: 00-0af7651916cd43dd8448eb211c80319c-b9c7c989f97918e1-01

    Returns:
        traceparent header value
    """
    span = trace.get_current_span()
    if not span or not span.is_recording():
        return ""

    ctx = span.get_span_context()
    trace_id = format(ctx.trace_id, "032x")
    span_id = format(ctx.span_id, "016x")
    trace_flags = "01" if ctx.trace_flags.sampled else "00"

    return f"00-{trace_id}-{span_id}-{trace_flags}"


def inject_agentcore_headers(
    headers: dict,
    campaign_id: str | None = None,
    agent_id: str | None = None,
    agent_type: str | None = None,
    turn_number: int | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Inject AgentCore-specific observability headers

    This ensures proper trace correlation with AWS AgentCore dashboards.
    Follows best practices from AWS blog post on AgentCore Observability.

    Args:
        headers: Existing headers dict
        campaign_id: Campaign identifier
        agent_id: Agent identifier
        agent_type: Agent type (persona, red_team, judge)
        turn_number: Turn number in campaign
        session_id: AgentCore session ID

    Returns:
        Headers with AgentCore metadata
    """
    # Standard trace context (traceparent + baggage)
    headers = inject_trace_context(headers)

    # Add AWS X-Ray format trace ID if available
    xray_trace_id = get_current_xray_trace_id()
    if xray_trace_id:
        headers["X-Amzn-Trace-Id"] = f"Root={xray_trace_id}"

    # Add AgentCore-specific metadata as headers
    if campaign_id:
        headers["X-AgentEval-Campaign-Id"] = campaign_id
        set_baggage("campaign.id", campaign_id)

    if agent_id:
        headers["X-AgentEval-Agent-Id"] = agent_id
        set_baggage("agent.id", agent_id)

    if agent_type:
        headers["X-AgentEval-Agent-Type"] = agent_type
        set_baggage("agent.type", agent_type)

    if turn_number is not None:
        headers["X-AgentEval-Turn-Number"] = str(turn_number)
        set_baggage("turn.number", str(turn_number))

    if session_id:
        headers["X-AgentCore-Session-Id"] = session_id
        set_baggage("agentcore.session.id", session_id)

    # Add service identification
    headers["X-AgentEval-Service"] = "agenteval"
    headers["X-AgentEval-Version"] = "1.0.0"

    return headers


def create_agentcore_span_attributes(
    campaign_id: str | None = None,
    agent_id: str | None = None,
    agent_type: str | None = None,
    turn_number: int | None = None,
    session_id: str | None = None,
) -> dict:
    """
    Create span attributes following OpenTelemetry GenAI semantic conventions

    Maps AgentEval concepts to OTel semantic conventions for better
    observability integration with AgentCore dashboards.

    Args:
        campaign_id: Campaign identifier
        agent_id: Agent identifier
        agent_type: Agent type
        turn_number: Turn number
        session_id: AgentCore session ID

    Returns:
        Dictionary of semantic attributes
    """
    attributes = {"service.name": "agenteval", "service.version": "1.0.0"}

    if campaign_id:
        attributes["agenteval.campaign.id"] = campaign_id

    if agent_id:
        attributes["agenteval.agent.id"] = agent_id
        attributes["gen_ai.agent.id"] = agent_id  # OTel GenAI convention

    if agent_type:
        attributes["agenteval.agent.type"] = agent_type
        attributes["gen_ai.agent.type"] = agent_type

    if turn_number is not None:
        attributes["agenteval.turn.number"] = turn_number

    if session_id:
        attributes["agentcore.session.id"] = session_id

    return attributes


# Deferred initialization - tracer will initialize on first use
# This prevents issues with settings not being ready during import
# Call tracer_setup.initialize() explicitly if needed, or it will
# be initialized automatically on first call to get_tracer()
