"""
Unit tests for TraceAnalyzer - X-Ray trace parsing and analysis.

Tests span parsing, classification, and metric extraction for root cause analysis.
"""

import json
from datetime import datetime

from agenteval.analysis.trace_analyzer import (
    AGENTEVAL_AGENT_ID,
    AGENTEVAL_AGENT_TYPE,
    AWS_AGENTCORE_AGENT_ID,
    OTEL_GENAI_OPERATION_NAME,
    OTEL_GENAI_REQUEST_MODEL,
    OTEL_GENAI_REQUEST_TEMPERATURE,
    OTEL_GENAI_SYSTEM,
    OTEL_GENAI_USAGE_INPUT_TOKENS,
    OTEL_GENAI_USAGE_OUTPUT_TOKENS,
    AgentRouting,
    LLMCall,
    ParsedSpan,
    SpanType,
    TraceAnalysis,
    TraceAnalyzer,
)


class TestSpanTypeEnum:
    """Test suite for SpanType enum"""

    def test_span_type_values(self):
        """Test SpanType enum values"""
        assert SpanType.LLM_CALL.value == "llm_call"
        assert SpanType.AGENT_ROUTING.value == "agent_routing"
        assert SpanType.DATABASE_QUERY.value == "database_query"
        assert SpanType.TOOL_INVOCATION.value == "tool_invocation"
        assert SpanType.HTTP_REQUEST.value == "http_request"
        assert SpanType.UNKNOWN.value == "unknown"


class TestTraceAnalyzerInitialization:
    """Test suite for TraceAnalyzer initialization"""

    def test_init(self):
        """Test TraceAnalyzer initialization"""
        analyzer = TraceAnalyzer()
        assert analyzer is not None


class TestDetermineSpanType:
    """Test suite for span type determination with confidence scoring"""

    def test_determine_span_type_otel_genai_operation(self):
        """Test OTel GenAI operation name detection (confidence: 1.0)"""
        analyzer = TraceAnalyzer()

        span_type, confidence = analyzer._determine_span_type(
            name="llm_operation", attributes={OTEL_GENAI_OPERATION_NAME: "chat"}
        )

        assert span_type == SpanType.LLM_CALL
        assert confidence == 1.0

    def test_determine_span_type_otel_genai_system(self):
        """Test OTel GenAI system detection (confidence: 1.0)"""
        analyzer = TraceAnalyzer()

        span_type, confidence = analyzer._determine_span_type(
            name="bedrock_call", attributes={OTEL_GENAI_SYSTEM: "bedrock"}
        )

        assert span_type == SpanType.LLM_CALL
        assert confidence == 1.0

    def test_determine_span_type_agentcore_attribute(self):
        """Test AWS AgentCore attribute detection (confidence: 0.95)"""
        analyzer = TraceAnalyzer()

        span_type, confidence = analyzer._determine_span_type(
            name="agent_span", attributes={AWS_AGENTCORE_AGENT_ID: "agent-123"}
        )

        assert span_type == SpanType.AGENT_ROUTING
        assert confidence == 0.95

    def test_determine_span_type_agenteval_attribute(self):
        """Test AgentEval custom attribute detection (confidence: 0.9)"""
        analyzer = TraceAnalyzer()

        span_type, confidence = analyzer._determine_span_type(
            name="agent_span",
            attributes={AGENTEVAL_AGENT_ID: "persona-1", AGENTEVAL_AGENT_TYPE: "persona"},
        )

        assert span_type == SpanType.AGENT_ROUTING
        assert confidence == 0.9

    def test_determine_span_type_name_heuristic_llm(self):
        """Test name-based LLM detection (confidence: 0.7)"""
        analyzer = TraceAnalyzer()

        span_type, confidence = analyzer._determine_span_type(
            name="bedrock_invoke_model", attributes={}
        )

        assert span_type == SpanType.LLM_CALL
        assert confidence == 0.7

    def test_determine_span_type_name_heuristic_database(self):
        """Test name-based database detection (confidence: 0.7)"""
        analyzer = TraceAnalyzer()

        span_type, confidence = analyzer._determine_span_type(
            name="dynamodb_get_item", attributes={}
        )

        assert span_type == SpanType.DATABASE_QUERY
        assert confidence == 0.7

    def test_determine_span_type_unknown(self):
        """Test unknown span type (confidence: 0.3)"""
        analyzer = TraceAnalyzer()

        span_type, confidence = analyzer._determine_span_type(
            name="random_operation", attributes={}
        )

        assert span_type == SpanType.UNKNOWN
        assert confidence == 0.3


class TestParseSpanData:
    """Test suite for parsing span data from X-Ray format"""

    def test_parse_span_data_basic(self):
        """Test basic span parsing"""
        analyzer = TraceAnalyzer()

        span_data = {
            "id": "span-123",
            "name": "test_span",
            "start_time": 1000.0,
            "end_time": 1002.5,
            "annotations": {"key1": "value1"},
            "metadata": {"key2": "value2"},
        }

        parsed = analyzer._parse_span_data(span_data, parent_id=None)

        assert parsed.span_id == "span-123"
        assert parsed.name == "test_span"
        assert parsed.parent_id is None
        assert parsed.duration_ms == 2500.0  # (1002.5 - 1000.0) * 1000
        assert parsed.attributes["key1"] == "value1"
        assert parsed.attributes["key2"] == "value2"

    def test_parse_span_data_with_error(self):
        """Test span parsing with error information"""
        analyzer = TraceAnalyzer()

        span_data = {
            "id": "span-error",
            "name": "failed_span",
            "start_time": 1000.0,
            "end_time": 1001.0,
            "error": True,
            "fault": False,
            "cause": "Connection timeout",
        }

        parsed = analyzer._parse_span_data(span_data, parent_id="parent-1")

        assert parsed.span_id == "span-error"
        assert parsed.parent_id == "parent-1"
        assert parsed.error is not None
        assert parsed.error["error"] is True
        assert parsed.error["fault"] is False
        assert parsed.error["cause"] == "Connection timeout"

    def test_parse_span_data_with_fault(self):
        """Test span parsing with fault"""
        analyzer = TraceAnalyzer()

        span_data = {
            "id": "span-fault",
            "name": "fault_span",
            "start_time": 1000.0,
            "end_time": 1001.0,
            "error": False,
            "fault": True,
        }

        parsed = analyzer._parse_span_data(span_data, parent_id=None)

        assert parsed.error is not None
        assert parsed.error["fault"] is True


class TestExtractLLMCalls:
    """Test suite for LLM call extraction with OTel conventions"""

    def test_extract_llm_calls_with_otel_attributes(self):
        """Test LLM extraction using OTel semantic conventions"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="llm-1",
                parent_id=None,
                span_type=SpanType.LLM_CALL,
                name="bedrock_chat",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=1500.0,
                attributes={
                    OTEL_GENAI_REQUEST_MODEL: "anthropic.claude-3-sonnet",
                    OTEL_GENAI_USAGE_INPUT_TOKENS: 100,
                    OTEL_GENAI_USAGE_OUTPUT_TOKENS: 50,
                    OTEL_GENAI_REQUEST_TEMPERATURE: 0.7,
                },
            )
        ]

        llm_calls = analyzer._extract_llm_calls(spans)

        assert len(llm_calls) == 1
        assert llm_calls[0].model_id == "anthropic.claude-3-sonnet"
        assert llm_calls[0].prompt_tokens == 100
        assert llm_calls[0].completion_tokens == 50
        assert llm_calls[0].total_tokens == 150
        assert llm_calls[0].temperature == 0.7
        assert llm_calls[0].latency_ms == 1500.0

    def test_extract_llm_calls_with_legacy_attributes(self):
        """Test LLM extraction using legacy attributes"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="llm-2",
                parent_id=None,
                span_type=SpanType.LLM_CALL,
                name="llm_call",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=2000.0,
                attributes={
                    "model_id": "claude-v2",
                    "llm.input_tokens": 200,
                    "llm.output_tokens": 100,
                    "temperature": 0.5,
                },
            )
        ]

        llm_calls = analyzer._extract_llm_calls(spans)

        assert len(llm_calls) == 1
        assert llm_calls[0].model_id == "claude-v2"
        assert llm_calls[0].prompt_tokens == 200
        assert llm_calls[0].completion_tokens == 100
        assert llm_calls[0].total_tokens == 300

    def test_extract_llm_calls_with_error(self):
        """Test LLM extraction with error information"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="llm-error",
                parent_id=None,
                span_type=SpanType.LLM_CALL,
                name="failed_llm",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=500.0,
                attributes={
                    OTEL_GENAI_REQUEST_MODEL: "claude-3",
                    OTEL_GENAI_USAGE_INPUT_TOKENS: 50,
                    OTEL_GENAI_USAGE_OUTPUT_TOKENS: 0,
                },
                error={"cause": "Rate limit exceeded"},
            )
        ]

        llm_calls = analyzer._extract_llm_calls(spans)

        assert len(llm_calls) == 1
        assert llm_calls[0].error == "Rate limit exceeded"

    def test_extract_llm_calls_filters_non_llm_spans(self):
        """Test that only LLM_CALL spans are extracted"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="routing-1",
                parent_id=None,
                span_type=SpanType.AGENT_ROUTING,
                name="agent_routing",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=100.0,
                attributes={},
            )
        ]

        llm_calls = analyzer._extract_llm_calls(spans)

        assert len(llm_calls) == 0


class TestExtractAgentRoutings:
    """Test suite for agent routing extraction"""

    def test_extract_agent_routings_with_agentcore_attributes(self):
        """Test routing extraction using AWS AgentCore attributes"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="routing-1",
                parent_id=None,
                span_type=SpanType.AGENT_ROUTING,
                name="agent_routing",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=250.0,
                attributes={AWS_AGENTCORE_AGENT_ID: "agent-123", "from_agent": "orchestrator"},
            )
        ]

        routings = analyzer._extract_agent_routings(spans)

        assert len(routings) == 1
        assert routings[0].to_agent == "agent-123"
        assert routings[0].from_agent == "orchestrator"
        assert routings[0].latency_ms == 250.0
        assert routings[0].success is True

    def test_extract_agent_routings_with_agenteval_attributes(self):
        """Test routing extraction using AgentEval attributes"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="routing-2",
                parent_id=None,
                span_type=SpanType.AGENT_ROUTING,
                name="persona_routing",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=150.0,
                attributes={
                    AGENTEVAL_AGENT_ID: "persona-frustrated",
                    AGENTEVAL_AGENT_TYPE: "persona",
                },
            )
        ]

        routings = analyzer._extract_agent_routings(spans)

        assert len(routings) == 1
        assert routings[0].to_agent == "persona-frustrated"
        assert routings[0].routing_reason == "Agent type: persona"

    def test_extract_agent_routings_with_error(self):
        """Test routing extraction with error"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="routing-error",
                parent_id=None,
                span_type=SpanType.AGENT_ROUTING,
                name="failed_routing",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=100.0,
                attributes={AGENTEVAL_AGENT_ID: "agent-fail"},
                error={"cause": "Agent not found"},
            )
        ]

        routings = analyzer._extract_agent_routings(spans)

        assert len(routings) == 1
        assert routings[0].success is False


class TestExtractDatabaseQueries:
    """Test suite for database query extraction"""

    def test_extract_database_queries_basic(self):
        """Test basic database query extraction"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="db-1",
                parent_id=None,
                span_type=SpanType.DATABASE_QUERY,
                name="dynamodb_query",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=75.0,
                attributes={
                    "operation": "GetItem",
                    "table_name": "campaigns",
                    "consumed_capacity": {"read": 1.0},
                },
            )
        ]

        queries = analyzer._extract_database_queries(spans)

        assert len(queries) == 1
        assert queries[0].operation == "GetItem"
        assert queries[0].table_name == "campaigns"
        assert queries[0].latency_ms == 75.0
        assert queries[0].consumed_capacity == {"read": 1.0}

    def test_extract_database_queries_with_aws_attributes(self):
        """Test query extraction using AWS-prefixed attributes"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="db-2",
                parent_id=None,
                span_type=SpanType.DATABASE_QUERY,
                name="db_query",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=50.0,
                attributes={"aws.operation": "PutItem", "aws.table_name": "turns"},
            )
        ]

        queries = analyzer._extract_database_queries(spans)

        assert len(queries) == 1
        assert queries[0].operation == "PutItem"
        assert queries[0].table_name == "turns"

    def test_extract_database_queries_with_error(self):
        """Test query extraction with error"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="db-error",
                parent_id=None,
                span_type=SpanType.DATABASE_QUERY,
                name="failed_query",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=200.0,
                attributes={"operation": "Query", "table_name": "evaluations"},
                error={"cause": "ProvisionedThroughputExceededException"},
            )
        ]

        queries = analyzer._extract_database_queries(spans)

        assert len(queries) == 1
        assert queries[0].error == "ProvisionedThroughputExceededException"


class TestCalculatePerformanceMetrics:
    """Test suite for performance metrics calculation"""

    def test_calculate_performance_metrics_basic(self):
        """Test basic performance metrics calculation"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="span-1",
                parent_id=None,
                span_type=SpanType.LLM_CALL,
                name="llm",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=1000.0,
            ),
            ParsedSpan(
                span_id="span-2",
                parent_id=None,
                span_type=SpanType.AGENT_ROUTING,
                name="routing",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=100.0,
                error={"cause": "Error"},
            ),
        ]

        llm_calls = [
            LLMCall(
                span_id="span-1",
                model_id="claude-3",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                latency_ms=1000.0,
            )
        ]

        routings = [
            AgentRouting(
                span_id="routing-1",
                from_agent="a",
                to_agent="b",
                routing_reason=None,
                latency_ms=100.0,
                success=True,
            )
        ]

        queries = []

        metrics = analyzer._calculate_performance_metrics(spans, llm_calls, routings, queries)

        assert metrics["total_spans"] == 2
        assert metrics["error_count"] == 1
        assert metrics["error_rate"] == 0.5
        assert metrics["llm_call_count"] == 1
        assert metrics["total_tokens"] == 150
        assert metrics["routing_count"] == 1

    def test_calculate_performance_metrics_empty(self):
        """Test metrics calculation with no data"""
        analyzer = TraceAnalyzer()

        metrics = analyzer._calculate_performance_metrics([], [], [], [])

        assert metrics["total_spans"] == 0
        assert metrics["error_count"] == 0
        assert metrics["error_rate"] == 0.0


class TestBuildTimeline:
    """Test suite for timeline building"""

    def test_build_timeline(self):
        """Test chronological timeline building"""
        analyzer = TraceAnalyzer()

        spans = [
            ParsedSpan(
                span_id="span-2",
                parent_id=None,
                span_type=SpanType.LLM_CALL,
                name="second",
                start_time=datetime(2024, 1, 1, 12, 0, 2),
                end_time=datetime(2024, 1, 1, 12, 0, 3),
                duration_ms=1000.0,
            ),
            ParsedSpan(
                span_id="span-1",
                parent_id=None,
                span_type=SpanType.AGENT_ROUTING,
                name="first",
                start_time=datetime(2024, 1, 1, 12, 0, 0),
                end_time=datetime(2024, 1, 1, 12, 0, 1),
                duration_ms=1000.0,
            ),
        ]

        timeline = analyzer._build_timeline(spans)

        assert len(timeline) == 2
        # Should be sorted chronologically
        assert timeline[0]["span_id"] == "span-1"
        assert timeline[1]["span_id"] == "span-2"
        assert timeline[0]["name"] == "first"
        assert timeline[1]["name"] == "second"


class TestAnalyzeTrace:
    """Test suite for complete trace analysis"""

    def test_analyze_trace_basic(self):
        """Test basic trace analysis"""
        analyzer = TraceAnalyzer()

        trace_data = {
            "Id": "trace-123",
            "Segments": [
                {
                    "Document": json.dumps(
                        {
                            "id": "segment-1",
                            "name": "bedrock_invoke",
                            "start_time": 1000.0,
                            "end_time": 1002.0,
                            "annotations": {
                                OTEL_GENAI_SYSTEM: "bedrock",
                                OTEL_GENAI_REQUEST_MODEL: "claude-3",
                                OTEL_GENAI_USAGE_INPUT_TOKENS: 100,
                                OTEL_GENAI_USAGE_OUTPUT_TOKENS: 50,
                            },
                        }
                    )
                }
            ],
        }

        analysis = analyzer.analyze_trace(trace_data)

        assert analysis.trace_id == "trace-123"
        assert len(analysis.all_spans) == 1
        assert len(analysis.llm_calls) == 1
        assert analysis.llm_calls[0].model_id == "claude-3"
        assert analysis.error_count == 0

    def test_analyze_trace_with_subsegments(self):
        """Test trace analysis with nested subsegments"""
        analyzer = TraceAnalyzer()

        trace_data = {
            "Id": "trace-nested",
            "Segments": [
                {
                    "Document": json.dumps(
                        {
                            "id": "root",
                            "name": "root_span",
                            "start_time": 1000.0,
                            "end_time": 1005.0,
                            "subsegments": [
                                {
                                    "id": "sub-1",
                                    "name": "dynamodb_query",
                                    "start_time": 1001.0,
                                    "end_time": 1002.0,
                                    "annotations": {
                                        "operation": "GetItem",
                                        "table_name": "test_table",
                                    },
                                }
                            ],
                        }
                    )
                }
            ],
        }

        analysis = analyzer.analyze_trace(trace_data)

        assert len(analysis.all_spans) == 2  # root + 1 subsegment
        assert analysis.root_span.span_id == "root"
        assert len(analysis.root_span.subsegments) == 1

    def test_analyze_trace_empty_segments(self):
        """Test trace analysis with no segments"""
        analyzer = TraceAnalyzer()

        trace_data = {"Id": "trace-empty", "Segments": []}

        analysis = analyzer.analyze_trace(trace_data)

        assert analysis.trace_id == "trace-empty"
        assert len(analysis.all_spans) == 0
        assert len(analysis.llm_calls) == 0
        assert analysis.total_duration_ms == 0.0

    def test_analyze_trace_error_handling(self):
        """Test trace analysis error handling"""
        analyzer = TraceAnalyzer()

        # Invalid trace data
        trace_data = {"Id": "trace-invalid", "Segments": ["invalid json"]}

        analysis = analyzer.analyze_trace(trace_data)

        # Should return empty analysis
        assert analysis.trace_id == "trace-invalid"
        assert len(analysis.all_spans) == 0


class TestExtractTraceInsights:
    """Test suite for trace insights extraction"""

    def test_extract_trace_insights_basic(self):
        """Test basic trace insights extraction"""
        analyzer = TraceAnalyzer()

        analysis = TraceAnalysis(
            trace_id="trace-insights",
            root_span=ParsedSpan(
                span_id="root",
                parent_id=None,
                span_type=SpanType.AGENT_ROUTING,
                name="root",
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration_ms=5000.0,
                confidence=0.95,
            ),
            all_spans=[
                ParsedSpan(
                    span_id="span-1",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name="llm",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=1000.0,
                    confidence=1.0,
                )
            ],
            llm_calls=[
                LLMCall(
                    span_id="span-1",
                    model_id="claude-3",
                    prompt_tokens=100,
                    completion_tokens=50,
                    total_tokens=150,
                    latency_ms=1000.0,
                )
            ],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=5000.0,
            error_count=0,
        )

        insights = analyzer.extract_trace_insights(analysis)

        assert insights["trace_id"] == "trace-insights"
        assert insights["summary"]["total_duration_ms"] == 5000.0
        assert insights["summary"]["operation_count"] == 1
        assert insights["llm_usage"]["call_count"] == 1
        assert insights["llm_usage"]["total_tokens"] == 150
        assert insights["llm_usage"]["models_used"] == ["claude-3"]

    def test_extract_trace_insights_with_confidence_metrics(self):
        """Test insights extraction includes confidence quality metrics"""
        analyzer = TraceAnalyzer()

        analysis = TraceAnalysis(
            trace_id="trace-quality",
            root_span=None,
            all_spans=[
                ParsedSpan(
                    span_id="span-1",
                    parent_id=None,
                    span_type=SpanType.LLM_CALL,
                    name="llm",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=1000.0,
                    confidence=1.0,
                ),
                ParsedSpan(
                    span_id="span-2",
                    parent_id=None,
                    span_type=SpanType.AGENT_ROUTING,
                    name="routing",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=500.0,
                    confidence=0.95,
                ),
                ParsedSpan(
                    span_id="span-3",
                    parent_id=None,
                    span_type=SpanType.UNKNOWN,
                    name="unknown",
                    start_time=datetime.now(),
                    end_time=datetime.now(),
                    duration_ms=100.0,
                    confidence=0.3,
                ),
            ],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=1600.0,
            error_count=0,
        )

        insights = analyzer.extract_trace_insights(analysis)

        # Check quality metrics
        assert "quality_metrics" in insights
        assert insights["quality_metrics"]["total_spans"] == 3
        assert insights["quality_metrics"]["high_confidence_spans"] == 2  # >= 0.9
        assert insights["quality_metrics"]["high_confidence_rate"] == round(2 / 3, 3)
        # Average confidence: (1.0 + 0.95 + 0.3) / 3 = 0.75
        assert insights["quality_metrics"]["avg_confidence"] == round(0.75, 3)

    def test_extract_trace_insights_empty_analysis(self):
        """Test insights extraction with empty analysis"""
        analyzer = TraceAnalyzer()

        analysis = TraceAnalysis(
            trace_id="trace-empty",
            root_span=None,
            all_spans=[],
            llm_calls=[],
            agent_routings=[],
            database_queries=[],
            total_duration_ms=0.0,
            error_count=0,
        )

        insights = analyzer.extract_trace_insights(analysis)

        assert insights["trace_id"] == "trace-empty"
        assert insights["llm_usage"]["call_count"] == 0
        assert insights["llm_usage"]["total_tokens"] == 0
        assert insights["llm_usage"]["avg_latency_ms"] == 0.0


class TestCreateEmptyAnalysis:
    """Test suite for empty analysis creation"""

    def test_create_empty_analysis(self):
        """Test creation of empty analysis result"""
        analyzer = TraceAnalyzer()

        analysis = analyzer._create_empty_analysis("trace-fail")

        assert analysis.trace_id == "trace-fail"
        assert analysis.root_span is None
        assert len(analysis.all_spans) == 0
        assert len(analysis.llm_calls) == 0
        assert analysis.total_duration_ms == 0.0
        assert analysis.error_count == 0
