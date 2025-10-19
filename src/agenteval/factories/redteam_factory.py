"""
Red Team Agent Factory

Factory for creating RedTeamAgent instances with proper configuration and initialization.
"""

import logging
import warnings
from typing import Any

from agenteval.agents.redteam_agent import RedTeamAgent
from agenteval.factories.base import AgentFactory
from agenteval.redteam.library import AttackCategory, AttackSeverity

logger = logging.getLogger(__name__)


class RedTeamAgentFactory(AgentFactory[RedTeamAgent]):
    """
    Factory for creating RedTeamAgent instances

    Handles:
    - Attack category validation
    - Severity threshold validation
    - Configuration parsing
    - Agent initialization
    - Error handling
    """

    def __init__(self):
        """Initialize red team agent factory"""
        super().__init__()

    async def create(self, config: dict[str, Any]) -> RedTeamAgent:
        """
        Create and initialize a RedTeamAgent

        Args:
            config: Agent configuration with keys:
                - attack_categories: Optional list of attack category strings
                - severity_threshold: Optional severity threshold string

        Returns:
            Initialized RedTeamAgent instance

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If agent initialization fails
        """
        self._log_creation("red_team", config)

        # Extract configuration (all optional for red team)
        attack_categories_str = config.get("attack_categories")
        severity_threshold_str = config.get("severity_threshold")
        if "use_mutations" in config:
            warnings.warn(
                "'use_mutations' is deprecated and ignored. Mutation strategy is managed by RedTeamAgent.",
                UserWarning,
                stacklevel=2,
            )

        # Convert attack categories to enums
        attack_categories = None
        if attack_categories_str:
            try:
                attack_categories = [AttackCategory(cat) for cat in attack_categories_str]
            except ValueError as e:
                valid_categories = [ac.value for ac in AttackCategory]
                raise ValueError(
                    f"Invalid attack category in {attack_categories_str}. "
                    f"Valid categories: {', '.join(valid_categories)}"
                ) from e

        # Convert severity threshold to enum
        severity_threshold = None
        if severity_threshold_str:
            try:
                severity_threshold = AttackSeverity(severity_threshold_str)
            except ValueError as e:
                valid_severities = [s.value for s in AttackSeverity]
                raise ValueError(
                    f"Invalid severity_threshold '{severity_threshold_str}'. "
                    f"Valid severities: {', '.join(valid_severities)}"
                ) from e

        # Create agent
        try:
            agent = RedTeamAgent(
                attack_categories=attack_categories, severity_threshold=severity_threshold
            )

            # Initialize agent (loads Bedrock client, attack library, etc.)
            await agent.initialize()

            self.logger.info(
                "RedTeamAgent created successfully",
                extra={
                    "agent_id": agent.agent_id,
                    "attack_categories": (
                        [c.value for c in attack_categories] if attack_categories else "all"
                    ),
                    "severity_threshold": severity_threshold.value if severity_threshold else "all",
                },
            )

            return agent

        except Exception as e:
            self.logger.error(f"Failed to create RedTeamAgent: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create RedTeamAgent: {e}") from e

    def create_injection_focused(self, severity_threshold: str = "medium") -> RedTeamAgent:
        """
        Convenience method to create agent focused on injection attacks

        Args:
            severity_threshold: Minimum severity (low, medium, high, critical)

        Returns:
            Initialized RedTeamAgent instance
        """
        import asyncio

        return asyncio.run(
            self.create(
                {"attack_categories": ["injection"], "severity_threshold": severity_threshold}
            )
        )

    def create_full_spectrum(self, severity_threshold: str = "low") -> RedTeamAgent:
        """
        Convenience method to create agent with all attack categories

        Args:
            severity_threshold: Minimum severity (low, medium, high, critical)

        Returns:
            Initialized RedTeamAgent instance
        """
        import asyncio

        return asyncio.run(self.create({"severity_threshold": severity_threshold}))
