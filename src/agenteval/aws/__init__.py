"""AWS service clients for AgentEval"""

from agenteval.aws.bedrock import BedrockClient, get_bedrock_client
from agenteval.aws.dynamodb import DynamoDBClient, get_dynamodb_client
from agenteval.aws.eventbridge import EventBridgeClient, get_eventbridge_client
from agenteval.aws.s3 import S3Client, get_s3_client
from agenteval.aws.xray import XRayClient, get_xray_client

__all__ = [
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
]
