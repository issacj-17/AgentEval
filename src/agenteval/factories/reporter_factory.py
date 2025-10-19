"""
Reporter Agent Factory

Factory for creating ReporterAgent instances with proper configuration and initialization.
"""

import logging
from typing import Any

from agenteval.agents.reporter_agent import ReporterAgent
from agenteval.factories.base import AgentFactory

logger = logging.getLogger(__name__)


class ReporterAgentFactory(AgentFactory[ReporterAgent]):
    """
    Factory for creating ReporterAgent instances.

    Handles:
    - Configuration parsing
    - Model selection
    - Agent initialization
    - Error handling
    """

    def __init__(self):
        """Initialize reporter agent factory."""
        super().__init__()

    async def create(self, config: dict[str, Any]) -> ReporterAgent:
        """
        Create and initialize a ReporterAgent.

        Args:
            config: Agent configuration with keys:
                - model_id: Optional Bedrock model ID (default: Claude Haiku)
                - max_tokens: Optional max tokens (default: 4000)
                - temperature: Optional temperature (default: 0.3)
                - report_type: Optional report type (default: "comprehensive")

        Returns:
            Initialized ReporterAgent instance

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If agent initialization fails
        """
        self._log_creation("reporter", config)

        # Extract configuration with defaults
        model_id = config.get("model_id", "anthropic.claude-haiku-4-5-20251001-v1:0")
        max_tokens = config.get("max_tokens", 4000)
        temperature = config.get("temperature", 0.3)

        # Validate configuration
        if max_tokens < 1000:
            raise ValueError(f"max_tokens must be >= 1000 for report generation, got {max_tokens}")

        if not (0.0 <= temperature <= 1.0):
            raise ValueError(f"temperature must be between 0.0 and 1.0, got {temperature}")

        # Create agent
        try:
            agent = ReporterAgent(
                model_id=model_id,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Initialize agent (loads Bedrock client, etc.)
            await agent.initialize()

            self.logger.info(
                "ReporterAgent created successfully",
                extra={
                    "agent_id": agent.agent_id,
                    "model_id": model_id,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
            )

            return agent

        except Exception as e:
            self.logger.error(
                f"Failed to create ReporterAgent: {e}",
                extra={"config": config},
            )
            raise RuntimeError(f"Reporter agent creation failed: {e}") from e

    def get_default_config(self) -> dict[str, Any]:
        """
        Get default configuration for Reporter Agent.

        Returns:
            Default configuration dictionary
        """
        return {
            "model_id": "anthropic.claude-haiku-4-5-20251001-v1:0",
            "max_tokens": 4000,
            "temperature": 0.3,
            "report_type": "comprehensive",
        }

    def validate_model_id(self, model_id: str) -> bool:
        """
        Validate if model_id is suitable for report generation.

        Args:
            model_id: Bedrock model identifier

        Returns:
            True if model is valid for reporting
        """
        # Reporter agent works best with Claude models for analysis
        valid_prefixes = [
            "anthropic.claude",
            "amazon.nova",
        ]

        return any(model_id.startswith(prefix) for prefix in valid_prefixes)
