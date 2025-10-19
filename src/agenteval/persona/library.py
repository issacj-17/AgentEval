"""
Persona Library - YAML-based configurable persona management

Provides flexible, swappable personas for testing without code changes.
Supports both file-based (YAML) and potential database storage.

Extends BaseLibrary for consistency across all agent libraries.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agenteval.libraries.base import BaseLibrary, LibraryDefinition, LibraryType

logger = logging.getLogger(__name__)


@dataclass
class PersonaDefinition(LibraryDefinition):
    """
    Definition of a persona loaded from YAML or database

    Extends LibraryDefinition with persona-specific fields.

    Attributes:
        (Inherited from LibraryDefinition)
        id: Unique persona identifier
        name: Display name
        category: Persona category (emotional, professional, etc.)
        description: Brief description
        metadata: General metadata dict

        (Persona-specific)
        attributes: Behavioral attributes (patience, frustration, etc.)
        preferences: User preferences (response speed, detail level)
        behavioral_traits: List of trait descriptions
        system_prompt: Prompt template for LLM
    """

    attributes: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    behavioral_traits: list[str] = field(default_factory=list)
    system_prompt: str = ""

    # Computed fields for convenience
    patience_level: int = field(init=False)
    frustration_level: int = field(init=False)
    communication_style: str = field(init=False)

    def __post_init__(self):
        """Extract common attributes for easy access"""
        super().__post_init__() if hasattr(super(), "__post_init__") else None

        self.patience_level = self.attributes.get("patience_level", 5)
        self.frustration_level = self.attributes.get("frustration_level", 0)
        self.communication_style = self.attributes.get("communication_style", "casual")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation"""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "attributes": self.attributes,
                "preferences": self.preferences,
                "behavioral_traits": self.behavioral_traits,
                "system_prompt": self.system_prompt,
                "patience_level": self.patience_level,
                "frustration_level": self.frustration_level,
                "communication_style": self.communication_style,
            }
        )
        return base_dict


class PersonaLibrary(BaseLibrary[PersonaDefinition]):
    """
    Manages persona definitions from YAML files or database

    Extends BaseLibrary to provide consistent interface across all libraries.

    Supports:
    - Loading personas from YAML
    - Querying by ID or category
    - Hot-reloading (optional)
    - Future: Database backend for dynamic personas
    """

    def __init__(self, library_path: str | None = None):
        """
        Initialize persona library

        Args:
            library_path: Path to YAML file (default: personas/library.yaml)
        """
        # Initialize base library
        super().__init__(
            library_type=LibraryType.PERSONA, library_path=library_path, auto_load=True
        )

        # Maintain backward compatibility with .personas attribute
        self.personas = self.items

    def _get_default_library_path(self) -> str:
        """Get default library path (relative to project root)"""
        # Try to find personas/library.yaml relative to project root
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent  # Go up to project root
        default_path = project_root / "personas" / "library.yaml"

        if default_path.exists():
            return str(default_path)

        # Fallback: try relative to current directory
        fallback_path = Path("personas/library.yaml")
        if fallback_path.exists():
            return str(fallback_path)

        logger.warning(f"Persona library not found at {default_path}")
        return str(default_path)  # Return default even if doesn't exist

    def _parse_yaml_item(self, item_data: dict[str, Any]) -> PersonaDefinition:
        """
        Parse YAML data into PersonaDefinition

        Args:
            item_data: Raw YAML data for persona

        Returns:
            PersonaDefinition instance
        """
        return PersonaDefinition(
            id=item_data["id"],
            name=item_data["name"],
            category=item_data["category"],
            description=item_data["description"],
            metadata=item_data.get("metadata", {}),
            attributes=item_data["attributes"],
            preferences=item_data["preferences"],
            behavioral_traits=item_data["behavioral_traits"],
            system_prompt=item_data["system_prompt"],
        )

    def _load_default_items(self) -> None:
        """
        Load default hardcoded personas as fallback

        Maintains backwards compatibility with original 4 personas.
        Implements abstract method from BaseLibrary.
        """
        logger.info("Loading default hardcoded personas")

        # Minimal default personas (backwards compatible)
        self.items = {
            "frustrated_customer": PersonaDefinition(
                id="frustrated_customer",
                name="Frustrated Customer",
                category="emotional",
                description="Impatient user who escalates quickly",
                metadata={},
                attributes={
                    "patience_level": 3,
                    "frustration_level": 5,
                    "communication_style": "casual",
                },
                preferences={},
                behavioral_traits=["Impatient", "Direct", "Escalates quickly"],
                system_prompt="You are a frustrated customer. Be direct and impatient.",
            ),
            "technical_expert": PersonaDefinition(
                id="technical_expert",
                name="Technical Expert",
                category="professional",
                description="Technical user who expects accuracy",
                metadata={},
                attributes={
                    "patience_level": 7,
                    "frustration_level": 0,
                    "communication_style": "technical",
                },
                preferences={},
                behavioral_traits=["Technical", "Precise", "Detail-oriented"],
                system_prompt="You are a technical expert. Ask detailed questions.",
            ),
            "elderly_user": PersonaDefinition(
                id="elderly_user",
                name="Elderly User",
                category="accessibility",
                description="User who needs simple explanations",
                metadata={},
                attributes={
                    "patience_level": 9,
                    "frustration_level": 0,
                    "communication_style": "simple",
                },
                preferences={},
                behavioral_traits=["Patient", "Confused by jargon", "Polite"],
                system_prompt="You are an elderly user. Need simple explanations.",
            ),
            "adversarial_user": PersonaDefinition(
                id="adversarial_user",
                name="Adversarial User",
                category="testing",
                description="User who tests boundaries",
                metadata={},
                attributes={
                    "patience_level": 6,
                    "frustration_level": 0,
                    "communication_style": "challenging",
                },
                preferences={},
                behavioral_traits=["Tests limits", "Creative", "Persistent"],
                system_prompt="You are testing system boundaries. Be creative.",
            ),
        }

        # Maintain backward compatibility
        self.personas = self.items

    def reload(self) -> None:
        """
        Reload personas from file (for hot-reloading)

        Overrides BaseLibrary.reload() to maintain backward compatibility.
        """
        super().reload()
        self.personas = self.items

    # ========================================================================
    # Backward Compatibility Methods
    # These wrap BaseLibrary methods to maintain existing API
    # ========================================================================

    def get_persona(self, persona_id: str) -> PersonaDefinition | None:
        """
        Get persona by ID (backward compatible wrapper)

        Args:
            persona_id: Persona identifier

        Returns:
            PersonaDefinition or None if not found
        """
        return self.get(persona_id)

    def get_personas_by_category(self, category: str) -> list[PersonaDefinition]:
        """
        Get all personas in a category (backward compatible wrapper)

        Args:
            category: Category name (emotional, professional, etc.)

        Returns:
            List of PersonaDefinitions
        """
        return self.get_by_category(category)

    def get_all_personas(self) -> list[PersonaDefinition]:
        """Get all available personas (backward compatible wrapper)"""
        return self.get_all()

    def list_persona_ids(self) -> list[str]:
        """Get list of all persona IDs (backward compatible wrapper)"""
        return self.list_ids()

    def get_persona_count(self) -> int:
        """Get total number of personas (backward compatible wrapper)"""
        return self.count()

    # Future: Database integration methods
    # These would be implemented when migrating to DynamoDB

    # async def load_from_database(self, dynamodb_client) -> None:
    #     """Load personas from DynamoDB"""
    #     pass

    # async def save_to_database(self, persona: PersonaDefinition, dynamodb_client) -> None:
    #     """Save persona to DynamoDB"""
    #     pass

    # async def sync_to_database(self, dynamodb_client) -> None:
    #     """Sync YAML personas to DynamoDB"""
    #     pass


# Global persona library instance
_persona_library: PersonaLibrary | None = None


def get_persona_library(library_path: str | None = None) -> PersonaLibrary:
    """
    Get global persona library instance (singleton)

    Args:
        library_path: Optional path to YAML file

    Returns:
        PersonaLibrary instance
    """
    global _persona_library

    if _persona_library is None:
        _persona_library = PersonaLibrary(library_path=library_path)

    return _persona_library


def reload_persona_library() -> None:
    """Reload global persona library"""
    global _persona_library

    if _persona_library:
        _persona_library.reload()
    else:
        _persona_library = PersonaLibrary()
