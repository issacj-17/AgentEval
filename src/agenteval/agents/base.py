"""
BaseAgent - Abstract base class for all agent types

Provides common functionality: tracing, Bedrock LLM, interaction logging.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

from opentelemetry import trace

from agenteval.aws.bedrock import BedrockClient
from agenteval.observability.tracer import get_tracer, trace_operation

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all AgentEval agents

    Provides:
    - Distributed tracing integration
    - Bedrock LLM access
    - Interaction logging
    - Common lifecycle methods
    """

    def __init__(self, agent_id: str | None = None, agent_type: str | None = None) -> None:
        """
        Initialize base agent

        Args:
            agent_id: Unique agent identifier (auto-generated if not provided)
            agent_type: Type of agent (persona, redteam, judge)
        """
        self.agent_id = agent_id or str(uuid4())
        self.agent_type = agent_type or self.__class__.__name__
        self.tracer = get_tracer()
        self.bedrock: BedrockClient | None = None

        logger.info(
            "Agent initialized", extra={"agent_id": self.agent_id, "agent_type": self.agent_type}
        )

    async def initialize(self) -> None:
        """Initialize agent (setup Bedrock client, etc.)"""
        self.bedrock = BedrockClient()
        await self.bedrock.__aenter__()
        logger.debug(f"Agent {self.agent_id} initialized Bedrock client")

    async def cleanup(self) -> None:
        """Cleanup agent resources"""
        if self.bedrock:
            await self.bedrock.__aexit__(None, None, None)
            logger.debug(f"Agent {self.agent_id} cleaned up Bedrock client")

    async def __aenter__(self) -> "BaseAgent":
        """Async context manager entry"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.cleanup()

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """
        Execute agent's primary function

        Must be implemented by subclasses.

        Returns:
            Dict containing execution results
        """
        pass

    async def invoke_llm(
        self,
        prompt: str,
        model_id: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Invoke LLM via Bedrock with tracing

        Args:
            prompt: User prompt
            model_id: Bedrock model ID
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system_prompt: Optional system prompt

        Returns:
            LLM response dict
        """
        if not self.bedrock:
            raise RuntimeError("Bedrock client not initialized. Call initialize() first.")

        with trace_operation(
            "llm_invocation",
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            model_id=model_id or "default",
        ) as span:
            try:
                response = await self.bedrock.invoke_model(
                    prompt=prompt,
                    model_id=model_id or self._get_default_model(),
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt,
                )

                # Add response metadata to span
                usage = self._normalize_usage(response.get("usage"))
                response["usage"] = usage
                output_tokens = self._extract_output_tokens(usage)
                if "output_tokens" not in usage and output_tokens:
                    usage["output_tokens"] = output_tokens

                stop_reason = self._derive_stop_reason(response)
                response.setdefault("stop_reason", stop_reason)

                span.set_attribute("llm.output_tokens", output_tokens)
                span.set_attribute("llm.stop_reason", stop_reason)

                logger.debug(
                    "LLM invocation successful",
                    extra={"agent_id": self.agent_id, "output_tokens": output_tokens},
                )

                return response

            except Exception as e:
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                span.record_exception(e)
                logger.error(f"LLM invocation failed: {e}", extra={"agent_id": self.agent_id})
                raise

    @abstractmethod
    def _get_default_model(self) -> str:
        """Get default Bedrock model ID for this agent type"""
        pass

    def get_agent_info(self) -> dict[str, Any]:
        """Get agent information"""
        return {"agent_id": self.agent_id, "agent_type": self.agent_type}

    @staticmethod
    def _normalize_usage(raw_usage: Any) -> dict[str, Any]:
        """Ensure usage metadata is always a dictionary for downstream consumers."""
        if isinstance(raw_usage, dict):
            return raw_usage.copy()
        if raw_usage is None:
            return {}
        if isinstance(raw_usage, (int, float)):
            return {"total_tokens": int(raw_usage)}
        if isinstance(raw_usage, list) and raw_usage:
            # Some providers return a singleton list with usage details.
            head_value = raw_usage[0]
            if isinstance(head_value, dict):
                return head_value.copy()
            if isinstance(head_value, (int, float)):
                return {"total_tokens": int(head_value)}
        return {"value": raw_usage}

    @classmethod
    def _extract_output_tokens(cls, usage: Any) -> int:
        """Best-effort extraction of output token counts from heterogeneous payloads."""
        if not isinstance(usage, dict):
            coerced = cls._coerce_token_value(usage)
            return coerced if coerced is not None else 0

        direct_keys = [
            "output_tokens",
            "outputTokens",
            "output_token_count",
            "completion_tokens",
            "completionTokens",
            "generated_tokens",
            "generatedTokens",
        ]
        for key in direct_keys:
            coerced = cls._coerce_token_value(usage.get(key))
            if coerced is not None:
                return coerced

        token_count = usage.get("tokenCount") or usage.get("token_count")
        if isinstance(token_count, dict):
            nested_keys = (
                "outputTokenCount",
                "generatedTokenCount",
                "textTokenCount",
                "totalTokenCount",
                "output_tokens",
            )
            for nested_key in nested_keys:
                coerced = cls._coerce_token_value(token_count.get(nested_key))
                if coerced is not None:
                    return coerced

        total_tokens = cls._coerce_token_value(
            usage.get("total_tokens") or usage.get("totalTokens")
        )
        if total_tokens is not None:
            return total_tokens

        return 0

    @staticmethod
    def _coerce_token_value(value: Any) -> int | None:
        """Normalize disparate token count formats into integers when possible."""
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, list) and value:
            head = value[0]
            if isinstance(head, (int, float)):
                return int(head)
            if isinstance(head, dict):
                return BaseAgent._coerce_token_value(head)
        if isinstance(value, dict):
            for key in ("value", "total", "count", "tokens", "outputTokenCount"):
                nested = value.get(key)
                if isinstance(nested, (int, float)):
                    return int(nested)
        return None

    @staticmethod
    def _derive_stop_reason(response: dict[str, Any]) -> str:
        """Extract a human-friendly stop reason from varied provider payloads."""
        for key in (
            "stop_reason",
            "stopReason",
            "completion_reason",
            "completionReason",
        ):
            value = response.get(key)
            if isinstance(value, str) and value:
                return value

        metadata = response.get("metadata")
        if isinstance(metadata, dict):
            for key in ("finish_reason", "finishReason"):
                value = metadata.get(key)
                if isinstance(value, str) and value:
                    return value

        return "unknown"
