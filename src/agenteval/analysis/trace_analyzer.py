"""
Trace Analyzer - SECRET SAUCE Component #1

Parses AWS X-Ray traces to extract actionable insights:
- LLM calls (Bedrock invocations)
- Tool/agent routing decisions
- Database queries (DynamoDB)
- Performance metrics
- Error patterns

Enhanced with OpenTelemetry Semantic Conventions support for better
AgentCore observability integration.

This enables correlation between evaluation scores and system behavior.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# OpenTelemetry Semantic Conventions for GenAI
# Reference: https://opentelemetry.io/docs/specs/semconv/gen-ai/
OTEL_GENAI_OPERATION_NAME = "gen_ai.operation.name"
OTEL_GENAI_SYSTEM = "gen_ai.system"
OTEL_GENAI_REQUEST_MODEL = "gen_ai.request.model"
OTEL_GENAI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
OTEL_GENAI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
OTEL_GENAI_RESPONSE_FINISH_REASON = "gen_ai.response.finish_reason"
OTEL_GENAI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
OTEL_GENAI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

# AWS AgentCore specific attributes
AWS_AGENTCORE_AGENT_ID = "aws.agentcore.agent.id"
AWS_AGENTCORE_SESSION_ID = "aws.agentcore.session.id"
AWS_AGENTCORE_TURN_NUMBER = "aws.agentcore.turn.number"

# AgentEval custom attributes
AGENTEVAL_AGENT_ID = "agenteval.agent.id"
AGENTEVAL_AGENT_TYPE = "agenteval.agent.type"
AGENTEVAL_CAMPAIGN_ID = "agenteval.campaign.id"
AGENTEVAL_TURN_NUMBER = "agenteval.turn.number"

# Schema version for trace format compatibility
TRACE_SCHEMA_VERSION = "1.0.0"


class SpanType(str, Enum):
    """Types of spans in traces"""

    LLM_CALL = "llm_call"
    AGENT_ROUTING = "agent_routing"
    DATABASE_QUERY = "database_query"
    TOOL_INVOCATION = "tool_invocation"
    HTTP_REQUEST = "http_request"
    UNKNOWN = "unknown"


@dataclass
class ParsedSpan:
    """
    Parsed span from X-Ray trace

    Attributes:
        span_id: Unique span identifier
        parent_id: Parent span ID (if any)
        span_type: Type of span
        name: Span name
        start_time: Start timestamp
        end_time: End timestamp
        duration_ms: Duration in milliseconds
        attributes: Span attributes/tags
        error: Error information (if any)
        subsegments: Child spans
        confidence: Confidence score for span type classification (0.0-1.0)
    """

    span_id: str
    parent_id: str | None
    span_type: SpanType
    name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    attributes: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    subsegments: list["ParsedSpan"] = field(default_factory=list)
    confidence: float = 1.0  # Default high confidence


@dataclass
class LLMCall:
    """
    Extracted LLM call information

    Attributes:
        span_id: Associated span ID
        model_id: Bedrock model ID
        prompt_tokens: Input tokens
        completion_tokens: Output tokens
        total_tokens: Total tokens
        latency_ms: Call latency
        temperature: Temperature parameter
        error: Error if call failed
    """

    span_id: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    temperature: float | None = None
    max_tokens: int | None = None
    error: str | None = None


@dataclass
class AgentRouting:
    """
    Extracted agent routing information

    Attributes:
        span_id: Associated span ID
        from_agent: Source agent ID
        to_agent: Destination agent ID
        routing_reason: Why routing occurred
        latency_ms: Routing latency
        success: Whether routing succeeded
    """

    span_id: str
    from_agent: str | None
    to_agent: str
    routing_reason: str | None
    latency_ms: float
    success: bool


@dataclass
class DatabaseQuery:
    """
    Extracted database query information

    Attributes:
        span_id: Associated span ID
        operation: DynamoDB operation (GetItem, Query, PutItem, etc.)
        table_name: Table name
        latency_ms: Query latency
        consumed_capacity: Read/write capacity consumed
        error: Error if query failed
    """

    span_id: str
    operation: str
    table_name: str
    latency_ms: float
    consumed_capacity: dict[str, float] | None = None
    error: str | None = None


@dataclass
class TraceAnalysis:
    """
    Comprehensive trace analysis results

    Attributes:
        trace_id: X-Ray trace ID
        root_span: Root span of trace
        all_spans: All spans in trace
        llm_calls: Extracted LLM calls
        agent_routings: Extracted agent routing decisions
        database_queries: Extracted database queries
        total_duration_ms: Total trace duration
        error_count: Number of errors in trace
        performance_metrics: Aggregate performance metrics
        timeline: Chronological timeline of events
        schema_version: Trace format schema version for compatibility tracking
    """

    trace_id: str
    root_span: ParsedSpan
    all_spans: list[ParsedSpan]
    llm_calls: list[LLMCall]
    agent_routings: list[AgentRouting]
    database_queries: list[DatabaseQuery]
    total_duration_ms: float
    error_count: int
    performance_metrics: dict[str, Any] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    schema_version: str = TRACE_SCHEMA_VERSION


class TraceAnalyzer:
    """
    Analyzes AWS X-Ray traces to extract insights

    This is a core component of the SECRET SAUCE:
    - Parses distributed traces
    - Identifies key operations (LLM, routing, DB)
    - Extracts performance metrics
    - Builds timeline for correlation
    """

    def __init__(self) -> None:
        logger.info("TraceAnalyzer initialized")

    def analyze_trace(self, trace_data: dict[str, Any]) -> TraceAnalysis:
        """
        Analyze a complete X-Ray trace

        Args:
            trace_data: Raw X-Ray trace data from AWS

        Returns:
            Comprehensive trace analysis
        """
        logger.debug(f"Analyzing trace: {trace_data.get('Id', 'unknown')}")

        try:
            # Extract trace ID
            trace_id = trace_data.get("Id", "unknown")

            # Parse all segments/spans
            segments = trace_data.get("Segments", [])
            if not segments:
                logger.warning(f"No segments found in trace {trace_id}")
                return self._create_empty_analysis(trace_id)

            # Parse root span and all subsegments
            all_spans = []
            root_span = None

            for segment_data in segments:
                # Parse segment document (JSON string)
                import json

                segment_doc = json.loads(segment_data.get("Document", "{}"))

                # Parse this segment
                parsed_span = self._parse_segment(segment_doc)
                all_spans.append(parsed_span)

                # Identify root span (no parent)
                if parsed_span.parent_id is None:
                    root_span = parsed_span

                # Parse subsegments recursively
                subsegments = segment_doc.get("subsegments", [])
                for subseg in subsegments:
                    parsed_subseg = self._parse_subsegment(subseg, parsed_span.span_id)
                    all_spans.append(parsed_subseg)
                    parsed_span.subsegments.append(parsed_subseg)

            if not root_span:
                root_span = all_spans[0] if all_spans else None

            # Extract specific operation types
            llm_calls = self._extract_llm_calls(all_spans)
            agent_routings = self._extract_agent_routings(all_spans)
            database_queries = self._extract_database_queries(all_spans)

            # Calculate metrics
            total_duration = root_span.duration_ms if root_span else 0.0
            error_count = sum(1 for span in all_spans if span.error is not None)

            # Build performance metrics
            performance_metrics = self._calculate_performance_metrics(
                all_spans, llm_calls, agent_routings, database_queries
            )

            # Build timeline
            timeline = self._build_timeline(all_spans)

            logger.info(
                f"Trace analyzed: {trace_id}",
                extra={
                    "trace_id": trace_id,
                    "total_spans": len(all_spans),
                    "llm_calls": len(llm_calls),
                    "agent_routings": len(agent_routings),
                    "database_queries": len(database_queries),
                    "duration_ms": total_duration,
                    "errors": error_count,
                },
            )

            return TraceAnalysis(
                trace_id=trace_id,
                root_span=root_span,
                all_spans=all_spans,
                llm_calls=llm_calls,
                agent_routings=agent_routings,
                database_queries=database_queries,
                total_duration_ms=total_duration,
                error_count=error_count,
                performance_metrics=performance_metrics,
                timeline=timeline,
            )

        except Exception as e:
            logger.error(f"Failed to analyze trace: {e}", exc_info=True)
            return self._create_empty_analysis(trace_data.get("Id", "unknown"))

    def _parse_segment(self, segment_doc: dict[str, Any]) -> ParsedSpan:
        """Parse a top-level X-Ray segment"""
        return self._parse_span_data(span_data=segment_doc, parent_id=None)

    def _parse_subsegment(self, subsegment_data: dict[str, Any], parent_id: str) -> ParsedSpan:
        """Parse an X-Ray subsegment"""
        return self._parse_span_data(span_data=subsegment_data, parent_id=parent_id)

    def _parse_span_data(self, span_data: dict[str, Any], parent_id: str | None) -> ParsedSpan:
        """
        Parse span data from X-Ray format

        Args:
            span_data: Raw span/segment data
            parent_id: Parent span ID (if subsegment)

        Returns:
            Parsed span
        """
        # Extract basic info
        span_id = span_data.get("id", "unknown")
        name = span_data.get("name", "unknown")
        start_time = span_data.get("start_time", 0.0)
        end_time = span_data.get("end_time", start_time)

        # Calculate duration
        duration_ms = (end_time - start_time) * 1000.0

        # Extract attributes/annotations
        attributes = {}
        if "annotations" in span_data:
            attributes.update(span_data["annotations"])
        if "metadata" in span_data:
            attributes.update(span_data["metadata"])

        # Determine span type with confidence score
        span_type, confidence = self._determine_span_type(name, attributes)

        # Extract error information
        error = None
        if span_data.get("error") or span_data.get("fault"):
            error = {
                "error": span_data.get("error", False),
                "fault": span_data.get("fault", False),
                "cause": span_data.get("cause"),
            }

        return ParsedSpan(
            span_id=span_id,
            parent_id=parent_id,
            span_type=span_type,
            name=name,
            start_time=datetime.fromtimestamp(start_time),
            end_time=datetime.fromtimestamp(end_time),
            duration_ms=duration_ms,
            attributes=attributes,
            error=error,
            subsegments=[],
            confidence=confidence,
        )

    def _determine_span_type(self, name: str, attributes: dict[str, Any]) -> tuple[SpanType, float]:
        """
        Determine span type from name and attributes using OTel semantic conventions

        Priority order:
        1. OTel semantic attributes (high confidence: 1.0)
        2. AWS AgentCore attributes (high confidence: 0.95)
        3. AgentEval custom attributes (medium-high confidence: 0.9)
        4. Name-based heuristics (medium confidence: 0.7)

        Args:
            name: Span name
            attributes: Span attributes

        Returns:
            Tuple of (SpanType, confidence_score)
        """
        # Priority 1: OpenTelemetry GenAI semantic conventions (confidence: 1.0)
        if OTEL_GENAI_OPERATION_NAME in attributes:
            operation_name = attributes[OTEL_GENAI_OPERATION_NAME].lower()
            if operation_name in ["chat", "completion", "embedding"]:
                return SpanType.LLM_CALL, 1.0

        # Check for OTel GenAI system attribute
        if OTEL_GENAI_SYSTEM in attributes:
            system = attributes[OTEL_GENAI_SYSTEM].lower()
            if system in ["bedrock", "anthropic", "openai"]:
                return SpanType.LLM_CALL, 1.0

        # Priority 2: AWS AgentCore semantic attributes (confidence: 0.95)
        if AWS_AGENTCORE_AGENT_ID in attributes or AWS_AGENTCORE_SESSION_ID in attributes:
            return SpanType.AGENT_ROUTING, 0.95

        # Priority 3: AgentEval custom attributes (confidence: 0.9)
        if AGENTEVAL_AGENT_ID in attributes or AGENTEVAL_AGENT_TYPE in attributes:
            agent_type = attributes.get(AGENTEVAL_AGENT_TYPE, "").lower()
            if agent_type in ["persona", "redteam", "judge"]:
                return SpanType.AGENT_ROUTING, 0.9
            return SpanType.AGENT_ROUTING, 0.85

        if AGENTEVAL_CAMPAIGN_ID in attributes:
            # Campaign-level span, likely routing or orchestration
            return SpanType.AGENT_ROUTING, 0.85

        # Priority 4: Fallback to name-based heuristics (confidence: 0.7)
        name_lower = name.lower()

        # LLM call detection via name
        if any(
            keyword in name_lower
            for keyword in ["bedrock", "llm", "invoke_model", "claude", "nova", "titan"]
        ):
            return SpanType.LLM_CALL, 0.7

        # Agent routing detection via name
        if any(
            keyword in name_lower for keyword in ["agent", "routing", "persona", "redteam", "judge"]
        ):
            return SpanType.AGENT_ROUTING, 0.7

        # Database query detection via name
        if any(
            keyword in name_lower
            for keyword in ["dynamodb", "database", "query", "put_item", "get_item"]
        ):
            return SpanType.DATABASE_QUERY, 0.7

        # Tool invocation detection via name
        if any(keyword in name_lower for keyword in ["tool", "function", "action"]):
            return SpanType.TOOL_INVOCATION, 0.7

        # HTTP request detection via name
        if any(keyword in name_lower for keyword in ["http", "request", "api"]):
            return SpanType.HTTP_REQUEST, 0.7

        # Unknown type (low confidence: 0.3)
        return SpanType.UNKNOWN, 0.3

    def _extract_llm_calls(self, spans: list[ParsedSpan]) -> list[LLMCall]:
        """
        Extract LLM call information from spans using OTel semantic conventions

        Prioritizes OTel GenAI attributes over legacy custom attributes.
        """
        llm_calls = []

        for span in spans:
            if span.span_type != SpanType.LLM_CALL:
                continue

            # Extract LLM-specific attributes
            attrs = span.attributes

            # Prioritize OTel semantic convention attributes
            # Model ID: use gen_ai.request.model, fallback to legacy model_id
            model_id = attrs.get(OTEL_GENAI_REQUEST_MODEL, attrs.get("model_id", "unknown"))

            # Token usage: use OTel attributes, fallback to legacy
            prompt_tokens = attrs.get(
                OTEL_GENAI_USAGE_INPUT_TOKENS, attrs.get("llm.input_tokens", 0)
            )
            completion_tokens = attrs.get(
                OTEL_GENAI_USAGE_OUTPUT_TOKENS, attrs.get("llm.output_tokens", 0)
            )

            # Calculate total if not provided
            total_tokens = prompt_tokens + completion_tokens
            if "llm.total_tokens" in attrs:
                total_tokens = attrs["llm.total_tokens"]

            # Temperature: use OTel attribute, fallback to legacy
            temperature = attrs.get(OTEL_GENAI_REQUEST_TEMPERATURE, attrs.get("temperature"))

            # Max tokens: use OTel attribute, fallback to legacy
            max_tokens = attrs.get(OTEL_GENAI_REQUEST_MAX_TOKENS, attrs.get("max_tokens"))

            llm_call = LLMCall(
                span_id=span.span_id,
                model_id=model_id,
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=int(total_tokens),
                latency_ms=span.duration_ms,
                temperature=temperature,
                max_tokens=max_tokens,
                error=span.error.get("cause") if span.error else None,
            )

            llm_calls.append(llm_call)

        logger.debug(f"Extracted {len(llm_calls)} LLM calls")
        return llm_calls

    def _extract_agent_routings(self, spans: list[ParsedSpan]) -> list[AgentRouting]:
        """
        Extract agent routing decisions from spans using OTel/AgentCore semantic conventions

        Prioritizes AWS AgentCore and AgentEval attributes over legacy custom attributes.
        """
        routings = []

        for span in spans:
            if span.span_type != SpanType.AGENT_ROUTING:
                continue

            attrs = span.attributes

            # Agent ID: prioritize AgentCore, then AgentEval, then legacy
            to_agent = (
                attrs.get(AWS_AGENTCORE_AGENT_ID)
                or attrs.get(AGENTEVAL_AGENT_ID)
                or attrs.get("agent_id")
                or attrs.get("to_agent", "unknown")
            )

            # From agent: use legacy attribute (no standard convention yet)
            from_agent = attrs.get("from_agent")

            # Routing reason: use legacy attribute
            routing_reason = attrs.get("routing_reason")

            # Add agent type context if available
            agent_type = attrs.get(AGENTEVAL_AGENT_TYPE)
            if agent_type and not routing_reason:
                routing_reason = f"Agent type: {agent_type}"

            routing = AgentRouting(
                span_id=span.span_id,
                from_agent=from_agent,
                to_agent=to_agent,
                routing_reason=routing_reason,
                latency_ms=span.duration_ms,
                success=span.error is None,
            )

            routings.append(routing)

        logger.debug(f"Extracted {len(routings)} agent routings")
        return routings

    def _extract_database_queries(self, spans: list[ParsedSpan]) -> list[DatabaseQuery]:
        """Extract database query information from spans"""
        queries = []

        for span in spans:
            if span.span_type != SpanType.DATABASE_QUERY:
                continue

            attrs = span.attributes

            query = DatabaseQuery(
                span_id=span.span_id,
                operation=attrs.get("operation", attrs.get("aws.operation", "unknown")),
                table_name=attrs.get("table_name", attrs.get("aws.table_name", "unknown")),
                latency_ms=span.duration_ms,
                consumed_capacity=attrs.get("consumed_capacity"),
                error=span.error.get("cause") if span.error else None,
            )

            queries.append(query)

        logger.debug(f"Extracted {len(queries)} database queries")
        return queries

    def _calculate_performance_metrics(
        self,
        spans: list[ParsedSpan],
        llm_calls: list[LLMCall],
        routings: list[AgentRouting],
        queries: list[DatabaseQuery],
    ) -> dict[str, Any]:
        """Calculate aggregate performance metrics"""
        metrics = {}

        # Overall metrics
        metrics["total_spans"] = len(spans)
        metrics["error_count"] = sum(1 for s in spans if s.error is not None)
        metrics["error_rate"] = metrics["error_count"] / len(spans) if spans else 0.0

        # LLM metrics
        if llm_calls:
            metrics["llm_call_count"] = len(llm_calls)
            metrics["total_tokens"] = sum(call.total_tokens for call in llm_calls)
            metrics["avg_llm_latency_ms"] = sum(call.latency_ms for call in llm_calls) / len(
                llm_calls
            )
            metrics["llm_error_count"] = sum(1 for call in llm_calls if call.error)

        # Routing metrics
        if routings:
            metrics["routing_count"] = len(routings)
            metrics["avg_routing_latency_ms"] = sum(r.latency_ms for r in routings) / len(routings)
            metrics["routing_success_rate"] = sum(1 for r in routings if r.success) / len(routings)

        # Database metrics
        if queries:
            metrics["query_count"] = len(queries)
            metrics["avg_query_latency_ms"] = sum(q.latency_ms for q in queries) / len(queries)
            metrics["query_error_count"] = sum(1 for q in queries if q.error)

        return metrics

    def _build_timeline(self, spans: list[ParsedSpan]) -> list[dict[str, Any]]:
        """
        Build chronological timeline of events

        Returns:
            Sorted list of timeline events
        """
        timeline = []

        for span in spans:
            event = {
                "timestamp": span.start_time.isoformat(),
                "span_id": span.span_id,
                "span_type": span.span_type.value,
                "name": span.name,
                "duration_ms": span.duration_ms,
                "error": span.error is not None,
            }
            timeline.append(event)

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    def _create_empty_analysis(self, trace_id: str) -> TraceAnalysis:
        """Create empty analysis result for failed traces"""
        return TraceAnalysis(
            trace_id=trace_id,
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=0.0,
            error_count=0,
            performance_metrics={},
            timeline=[],
        )

    def extract_trace_insights(self, analysis: TraceAnalysis) -> dict[str, Any]:
        """
        Extract high-level insights from trace analysis

        This prepares trace data for correlation with evaluation scores

        Args:
            analysis: Trace analysis result

        Returns:
            Dictionary of actionable insights with schema version and confidence scores
        """
        # Calculate average confidence for RCA quality metrics
        avg_confidence = 0.0
        if analysis.all_spans:
            avg_confidence = sum(span.confidence for span in analysis.all_spans) / len(
                analysis.all_spans
            )

        # Count high-confidence spans (>= 0.9)
        high_confidence_count = sum(1 for span in analysis.all_spans if span.confidence >= 0.9)
        high_confidence_rate = (
            high_confidence_count / len(analysis.all_spans) if analysis.all_spans else 0.0
        )

        insights = {
            "trace_id": analysis.trace_id,
            "schema_version": analysis.schema_version,
            "quality_metrics": {
                "avg_confidence": round(avg_confidence, 3),
                "high_confidence_rate": round(high_confidence_rate, 3),
                "high_confidence_spans": high_confidence_count,
                "total_spans": len(analysis.all_spans),
            },
            "summary": {
                "total_duration_ms": analysis.total_duration_ms,
                "operation_count": len(analysis.all_spans),
                "error_count": analysis.error_count,
                "error_rate": analysis.performance_metrics.get("error_rate", 0.0),
            },
            "llm_usage": {
                "call_count": len(analysis.llm_calls),
                "total_tokens": sum(call.total_tokens for call in analysis.llm_calls),
                "avg_latency_ms": (
                    sum(call.latency_ms for call in analysis.llm_calls) / len(analysis.llm_calls)
                    if analysis.llm_calls
                    else 0.0
                ),
                "models_used": list(set(call.model_id for call in analysis.llm_calls)),
            },
            "routing_behavior": {
                "routing_count": len(analysis.agent_routings),
                "routing_path": [r.to_agent for r in analysis.agent_routings],
                "avg_latency_ms": (
                    sum(r.latency_ms for r in analysis.agent_routings)
                    / len(analysis.agent_routings)
                    if analysis.agent_routings
                    else 0.0
                ),
            },
            "database_activity": {
                "query_count": len(analysis.database_queries),
                "avg_latency_ms": (
                    sum(q.latency_ms for q in analysis.database_queries)
                    / len(analysis.database_queries)
                    if analysis.database_queries
                    else 0.0
                ),
                "operations": [q.operation for q in analysis.database_queries],
            },
            "timeline": analysis.timeline,
        }

        logger.debug(
            f"Extracted insights for trace {analysis.trace_id}",
            extra={"avg_confidence": avg_confidence, "high_confidence_rate": high_confidence_rate},
        )

        return insights
