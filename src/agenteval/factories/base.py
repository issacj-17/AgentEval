"""
Base Agent Factory

Provides abstract base class for agent factories following the Factory Method pattern.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

# Type variable for agent types
T = TypeVar("T")


class AgentFactory(ABC, Generic[T]):
    """
    Abstract base class for agent factories

    Factories encapsulate agent creation logic, handling:
    - Configuration validation
    - Dependency injection
    - Agent initialization
    - Error handling

    This follows the Factory Method pattern and enables:
    - Testability: Factories can be mocked
    - Flexibility: Easy to swap implementations
    - Separation of Concerns: Creation logic separate from usage
    """

    def __init__(self):
        """Initialize factory"""
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def create(self, config: dict[str, Any]) -> T:
        """
        Create and initialize an agent from configuration

        Args:
            config: Agent configuration dictionary

        Returns:
            Initialized agent instance

        Raises:
            ValueError: If configuration is invalid
            RuntimeError: If agent creation fails
        """
        pass

    def _validate_config(self, config: dict[str, Any], required_keys: list) -> None:
        """
        Validate configuration has required keys

        Args:
            config: Configuration dictionary
            required_keys: List of required key names

        Raises:
            ValueError: If required keys are missing
        """
        missing_keys = [key for key in required_keys if key not in config]
        if missing_keys:
            raise ValueError(
                f"{self.__class__.__name__}: Missing required configuration keys: {missing_keys}"
            )

    def _log_creation(self, agent_type: str, config: dict[str, Any]) -> None:
        """
        Log agent creation

        Args:
            agent_type: Type of agent being created
            config: Agent configuration
        """
        self.logger.info(
            f"Creating {agent_type} agent",
            extra={"agent_type": agent_type, "config_keys": list(config.keys())},
        )
