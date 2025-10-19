"""
Persona Agent Factory

Factory for creating PersonaAgent instances with proper configuration and initialization.
"""

import logging
from typing import Any

from agenteval.agents.persona_agent import PersonaAgent, PersonaType
from agenteval.factories.base import AgentFactory

logger = logging.getLogger(__name__)


class PersonaAgentFactory(AgentFactory[PersonaAgent]):
    """
    Factory for creating PersonaAgent instances

    Handles:
    - Persona type validation
    - Configuration parsing
    - Agent initialization
    - Error handling
    """

    def __init__(self):
        """Initialize persona agent factory"""
        super().__init__()

    async def create(self, config: dict[str, Any]) -> PersonaAgent:
        """
        Create and initialize a PersonaAgent

        Args:
            config: Agent configuration with keys:
                - persona_type: Persona type string (e.g., "frustrated_customer")
                - initial_goal: Optional initial goal (default: "Get help with my issue")

        Returns:
            Initialized PersonaAgent instance

        Raises:
            ValueError: If configuration is invalid or persona_type is unknown
            RuntimeError: If agent initialization fails
        """
        self._log_creation("persona", config)

        # Validate required configuration
        self._validate_config(config, ["persona_type"])

        # Extract configuration
        persona_type_str = config.get("persona_type")
        initial_goal = config.get("initial_goal", "Get help with my issue")

        # Convert persona type string to enum
        try:
            persona_type = PersonaType(persona_type_str)
        except ValueError as e:
            valid_types = [pt.value for pt in PersonaType]
            raise ValueError(
                f"Invalid persona_type '{persona_type_str}'. Valid types: {', '.join(valid_types)}"
            ) from e

        # Create agent
        try:
            agent = PersonaAgent(persona_type=persona_type, initial_goal=initial_goal)

            # Initialize agent (loads Bedrock client, sets up memory, etc.)
            await agent.initialize()

            self.logger.info(
                "PersonaAgent created successfully",
                extra={
                    "persona_type": persona_type.value,
                    "agent_id": agent.agent_id,
                    "initial_goal": initial_goal,
                },
            )

            return agent

        except Exception as e:
            self.logger.error(
                f"Failed to create PersonaAgent: {e}",
                extra={"persona_type": persona_type_str},
                exc_info=True,
            )
            raise RuntimeError(f"Failed to create PersonaAgent: {e}") from e

    def create_frustrated_customer(
        self, initial_goal: str = "Get help with my billing issue"
    ) -> PersonaAgent:
        """
        Convenience method to create a frustrated customer persona

        Args:
            initial_goal: Initial goal for the persona

        Returns:
            Initialized PersonaAgent instance
        """
        import asyncio

        return asyncio.run(
            self.create({"persona_type": "frustrated_customer", "initial_goal": initial_goal})
        )

    def create_technical_expert(
        self, initial_goal: str = "Debug and analyze the system"
    ) -> PersonaAgent:
        """
        Convenience method to create a technical expert persona

        Args:
            initial_goal: Initial goal for the persona

        Returns:
            Initialized PersonaAgent instance
        """
        import asyncio

        return asyncio.run(
            self.create({"persona_type": "technical_expert", "initial_goal": initial_goal})
        )
