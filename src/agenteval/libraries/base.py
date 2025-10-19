"""
Base Library System - Abstract classes and interfaces

Provides foundation for all agent libraries (Personas, Attacks, Metrics).
Ensures consistency, modularity, and extensibility.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Generic, TypeVar

import yaml

logger = logging.getLogger(__name__)


class LibraryType(str, Enum):
    """Types of libraries in AgentEval"""

    PERSONA = "persona"
    ATTACK = "attack"
    METRIC = "metric"


class LoadStrategy(str, Enum):
    """Strategy for loading library data"""

    YAML_FILE = "yaml_file"
    DATABASE = "database"
    HYBRID = "hybrid"  # YAML + Database


@dataclass
class LibraryDefinition:
    """
    Base definition for any library item

    All library items (personas, attacks, metrics) must have these fields.
    Subclasses can add additional fields.
    """

    id: str
    name: str
    category: str
    description: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "metadata": self.metadata,
        }


# Type variable for library definitions
T = TypeVar("T", bound=LibraryDefinition)


class BaseLibrary(ABC, Generic[T]):
    """
    Abstract base class for all libraries

    Provides common functionality for loading, querying, and managing
    library items (personas, attacks, metrics).

    Features:
    - YAML file loading with fallback to defaults
    - Hot-reloading capability
    - Category-based querying
    - Extensible to database backends
    - Singleton pattern support

    Type Parameters:
        T: Type of library definition (PersonaDefinition, AttackDefinition, etc.)
    """

    def __init__(
        self,
        library_type: LibraryType,
        library_path: str | None = None,
        load_strategy: LoadStrategy = LoadStrategy.YAML_FILE,
        auto_load: bool = True,
    ) -> None:
        """
        Initialize library

        Args:
            library_type: Type of library (persona, attack, metric)
            library_path: Path to YAML file (optional)
            load_strategy: Strategy for loading data
            auto_load: Whether to automatically load on initialization
        """
        self.library_type = library_type
        self.load_strategy = load_strategy
        self.items: dict[str, T] = {}

        # Determine library path
        self.library_path = library_path or self._get_default_library_path()

        # Load items if auto_load enabled
        if auto_load:
            self.load()

        logger.info(
            f"{self.library_type.value.title()}Library initialized with {len(self.items)} items",
            extra={
                "library_type": self.library_type.value,
                "item_count": len(self.items),
                "load_strategy": self.load_strategy.value,
            },
        )

    @abstractmethod
    def _get_default_library_path(self) -> str:
        """
        Get default path for library YAML file

        Returns:
            Path to default library file
        """
        pass

    @abstractmethod
    def _parse_yaml_item(self, item_data: dict[str, Any]) -> T:
        """
        Parse YAML data into library definition

        Args:
            item_data: Raw YAML data for item

        Returns:
            Parsed library definition
        """
        pass

    @abstractmethod
    def _load_default_items(self) -> None:
        """
        Load default hardcoded items as fallback

        Called when YAML file not found or fails to parse.
        Maintains backward compatibility.
        """
        pass

    def load(self) -> None:
        """
        Load items based on load strategy
        """
        if self.load_strategy == LoadStrategy.YAML_FILE:
            self._load_from_yaml()
        elif self.load_strategy == LoadStrategy.DATABASE:
            self._load_from_database()
        elif self.load_strategy == LoadStrategy.HYBRID:
            self._load_from_yaml()
            # Could also load from database and merge
        else:
            logger.warning(f"Unknown load strategy: {self.load_strategy}")
            self._load_default_items()

    def _load_from_yaml(self) -> None:
        """Load items from YAML file"""
        try:
            library_path = Path(self.library_path)

            if not library_path.exists():
                logger.warning(
                    f"{self.library_type.value.title()} library not found: {library_path}. "
                    f"Using hardcoded defaults only."
                )
                self._load_default_items()
                return

            with open(library_path) as f:
                data = yaml.safe_load(f)

            # Validate structure
            items_key = f"{self.library_type.value}s"  # personas, attacks, metrics
            if not data or items_key not in data:
                logger.error(f"Invalid library format: missing '{items_key}' key")
                self._load_default_items()
                return

            # Parse items
            loaded_count = 0
            for item_data in data[items_key]:
                try:
                    item = self._parse_yaml_item(item_data)
                    self.items[item.id] = item
                    loaded_count += 1
                except KeyError as e:
                    logger.error(
                        f"Missing required field in {self.library_type.value}: {e}",
                        extra={"item_id": item_data.get("id", "unknown")},
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to parse {self.library_type.value}: {e}",
                        extra={"item_data": item_data},
                    )

            logger.info(
                f"Loaded {loaded_count} {self.library_type.value}s from {library_path}",
                extra={"library_path": str(library_path), "item_ids": list(self.items.keys())},
            )

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML: {e}")
            self._load_default_items()
        except Exception as e:
            logger.error(f"Failed to load library: {e}", exc_info=True)
            self._load_default_items()

    def _load_from_database(self) -> None:
        """
        Load items from database

        Placeholder for future database integration.
        """
        logger.warning(
            f"Database loading not yet implemented for {self.library_type.value}. Using defaults."
        )
        self._load_default_items()

    def reload(self) -> None:
        """Reload items from source (for hot-reloading)"""
        logger.info(f"Reloading {self.library_type.value} library")
        self.items.clear()
        self.load()

    def get(self, item_id: str) -> T | None:
        """
        Get item by ID

        Args:
            item_id: Item identifier

        Returns:
            Item definition or None if not found
        """
        item = self.items.get(item_id)

        if item:
            logger.debug(f"Retrieved {self.library_type.value}: {item_id}")
        else:
            logger.warning(f"{self.library_type.value.title()} not found: {item_id}")

        return item

    def get_by_category(self, category: str) -> list[T]:
        """
        Get all items in a category

        Args:
            category: Category name

        Returns:
            List of items in category
        """
        items = [item for item in self.items.values() if item.category == category]

        logger.debug(
            f"Found {len(items)} {self.library_type.value}s in category: {category}",
            extra={"category": category, "count": len(items)},
        )

        return items

    def get_all(self) -> list[T]:
        """Get all items"""
        return list(self.items.values())

    def list_ids(self) -> list[str]:
        """Get list of all item IDs"""
        return list(self.items.keys())

    def list_categories(self) -> list[str]:
        """Get list of all categories"""
        categories = set(item.category for item in self.items.values())
        return sorted(categories)

    def count(self) -> int:
        """Get total number of items"""
        return len(self.items)

    def exists(self, item_id: str) -> bool:
        """Check if item exists"""
        return item_id in self.items

    def to_dict(self) -> dict[str, Any]:
        """Export library metadata"""
        return {
            "library_type": self.library_type.value,
            "total_items": len(self.items),
            "categories": self.list_categories(),
            "item_ids": self.list_ids(),
            "library_path": self.library_path,
            "load_strategy": self.load_strategy.value,
        }

    def validate(self) -> dict[str, Any]:
        """
        Validate library integrity

        Returns:
            Validation results with errors and warnings
        """
        errors = []
        warnings = []

        # Check for duplicate IDs (shouldn't happen with dict, but good to check)
        ids = [item.id for item in self.items.values()]
        if len(ids) != len(set(ids)):
            errors.append("Duplicate item IDs found")

        # Check for empty items
        if len(self.items) == 0:
            warnings.append("Library is empty")

        # Check for items without categories
        uncategorized = [
            item.id
            for item in self.items.values()
            if not item.category or item.category.strip() == ""
        ]
        if uncategorized:
            warnings.append(f"Uncategorized items: {uncategorized}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_items": len(self.items),
            "categories": self.list_categories(),
        }


class LibraryManager:
    """
    Central manager for all libraries

    Provides unified access to all library types and ensures
    consistent lifecycle management.
    """

    def __init__(self):
        self._libraries: dict[LibraryType, BaseLibrary] = {}
        logger.info("LibraryManager initialized")

    def register(self, library: BaseLibrary) -> None:
        """Register a library with the manager"""
        self._libraries[library.library_type] = library
        logger.info(f"Registered {library.library_type.value} library")

    def get_library(self, library_type: LibraryType) -> BaseLibrary | None:
        """Get library by type"""
        return self._libraries.get(library_type)

    def reload_all(self) -> None:
        """Reload all registered libraries"""
        logger.info("Reloading all libraries")
        for library in self._libraries.values():
            library.reload()

    def get_stats(self) -> dict[str, Any]:
        """Get statistics for all libraries"""
        return {
            library_type.value: library.to_dict()
            for library_type, library in self._libraries.items()
        }

    def validate_all(self) -> dict[str, Any]:
        """Validate all libraries"""
        return {
            library_type.value: library.validate()
            for library_type, library in self._libraries.items()
        }


# Global library manager instance
_library_manager: LibraryManager | None = None


def get_library_manager() -> LibraryManager:
    """Get global library manager instance (singleton)"""
    global _library_manager

    if _library_manager is None:
        _library_manager = LibraryManager()

    return _library_manager
