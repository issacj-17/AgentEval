"""
Judge Agent Factory

Factory for creating JudgeAgent instances with proper configuration and initialization.
"""

import logging
from typing import Any

from agenteval.agents.judge_agent import JudgeAgent
from agenteval.factories.base import AgentFactory

logger = logging.getLogger(__name__)


class JudgeAgentFactory(AgentFactory[JudgeAgent]):
    """
    Factory for creating JudgeAgent instances

    Handles:
    - Configuration parsing
    - Agent initialization
    - Error handling

    Note: JudgeAgent typically has minimal configuration needs
    """

    def __init__(self):
        """Initialize judge agent factory"""
        super().__init__()

    async def create(self, config: dict[str, Any] = None) -> JudgeAgent:
        """
        Create and initialize a JudgeAgent

        Args:
            config: Optional agent configuration (currently unused but allows future extension)

        Returns:
            Initialized JudgeAgent instance

        Raises:
            RuntimeError: If agent initialization fails
        """
        if config is None:
            config = {}

        self._log_creation("judge", config)

        # Create agent
        try:
            agent = JudgeAgent()

            # Initialize agent (loads Bedrock client, metrics registry, etc.)
            await agent.initialize()

            self.logger.info("JudgeAgent created successfully", extra={"agent_id": agent.agent_id})

            return agent

        except Exception as e:
            self.logger.error(f"Failed to create JudgeAgent: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create JudgeAgent: {e}") from e

    def create_sync(self) -> JudgeAgent:
        """
        Convenience method to create a JudgeAgent synchronously

        Returns:
            Initialized JudgeAgent instance
        """
        import asyncio

        return asyncio.run(self.create())
