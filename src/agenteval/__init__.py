"""
AgentEval - Multi-Agent AI Evaluation Platform

A comprehensive evaluation framework for GenAI applications featuring:
- Persona agents for realistic user simulation
- Red team agents for security testing
- Judge agents for comprehensive evaluation
- Trace-based root cause analysis (SECRET SAUCE)
"""

__version__ = "1.0.0"
__author__ = "AgentEval Team"

# Base agent
from agenteval.agents.base import BaseAgent

# Core AWS clients
from agenteval.aws.bedrock import BedrockClient, get_bedrock_client
from agenteval.aws.dynamodb import DynamoDBClient, get_dynamodb_client
from agenteval.aws.eventbridge import EventBridgeClient, get_eventbridge_client
from agenteval.aws.s3 import S3Client, get_s3_client
from agenteval.aws.xray import XRayClient, get_xray_client
from agenteval.config import settings

# Observability
from agenteval.observability.tracer import (
    build_traceparent_header,
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    inject_trace_context,
    trace_operation,
)

__all__ = [
    # Version info
    "__version__",
    "__author__",
    # Configuration
    "settings",
    # AWS Clients
    "BedrockClient",
    "get_bedrock_client",
    "DynamoDBClient",
    "get_dynamodb_client",
    "S3Client",
    "get_s3_client",
    "XRayClient",
    "get_xray_client",
    "EventBridgeClient",
    "get_eventbridge_client",
    # Observability
    "get_tracer",
    "trace_operation",
    "get_current_trace_id",
    "get_current_span_id",
    "inject_trace_context",
    "build_traceparent_header",
    # Agents
    "BaseAgent",
]
