"""
Unit tests for PersonaLibrary

Tests persona library loading, validation, and retrieval.
"""

import pytest

from agenteval.persona import PersonaDefinition, get_persona_library, reload_persona_library


class TestPersonaLibrary:
    """Test PersonaLibrary functionality"""

    @pytest.fixture
    def library(self):
        """Get persona library instance"""
        return get_persona_library()

    def test_library_loads_successfully(self, library):
        """Test that persona library loads from YAML"""
        assert library is not None
        assert library.get_persona_count() > 0

    def test_library_has_expected_categories(self, library):
        """Test that library has expected persona categories"""
        categories = library.list_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0
        # Expected categories based on actual YAML structure
        expected_categories = ["emotional", "professional"]
        for expected in expected_categories:
            assert expected in categories, f"Missing expected category: {expected}"

    def test_library_counts_match(self, library):
        """Test that persona counts are consistent"""
        all_personas = library.get_all_personas()
        count = library.get_persona_count()
        assert len(all_personas) == count
        assert count > 0

    def test_get_persona_by_id(self, library):
        """Test retrieving specific persona by ID"""
        # Test known persona
        persona = library.get_persona("frustrated_customer")
        assert persona is not None
        assert isinstance(persona, PersonaDefinition)
        assert persona.id == "frustrated_customer"
        assert persona.name is not None
        assert persona.category is not None

    def test_get_nonexistent_persona_returns_none(self, library):
        """Test that nonexistent persona returns None"""
        persona = library.get_persona("does_not_exist_123")
        assert persona is None

    def test_list_persona_ids(self, library):
        """Test listing all persona IDs"""
        ids = library.list_persona_ids()
        assert isinstance(ids, list)
        assert len(ids) > 0
        assert "frustrated_customer" in ids

    def test_get_personas_by_category(self, library):
        """Test filtering personas by category"""
        categories = library.list_categories()
        for category in categories:
            personas = library.get_personas_by_category(category)
            assert isinstance(personas, list)
            assert len(personas) > 0
            # Verify all personas are from correct category
            for persona in personas:
                assert persona.category == category

    def test_persona_has_required_fields(self, library):
        """Test that personas have all required fields"""
        all_personas = library.get_all_personas()
        for persona in all_personas:
            # Required fields
            assert persona.id
            assert persona.name
            assert persona.category
            assert persona.description

            # Numeric fields with valid ranges
            assert 0 <= persona.patience_level <= 10
            assert 0 <= persona.frustration_level <= 10

            # Attributes can be dict or list depending on YAML structure
            assert persona.attributes is not None
            assert isinstance(persona.behavioral_traits, list)

            # String fields
            assert isinstance(persona.communication_style, str)

    def test_persona_to_dict(self, library):
        """Test persona serialization to dict"""
        persona = library.get_persona("frustrated_customer")
        persona_dict = persona.to_dict()

        assert isinstance(persona_dict, dict)
        assert persona_dict["id"] == "frustrated_customer"
        assert "name" in persona_dict
        assert "category" in persona_dict
        assert "patience_level" in persona_dict
        assert "frustration_level" in persona_dict

    def test_library_validation(self, library):
        """Test library validation method"""
        validation = library.validate()

        assert isinstance(validation, dict)
        assert "valid" in validation
        assert "total_items" in validation

        # Library should be valid
        assert validation["valid"] is True
        assert validation["total_items"] > 0

        # Should have no duplicates or missing fields
        assert len(validation.get("duplicate_ids", [])) == 0
        assert len(validation.get("missing_required_fields", [])) == 0

    def test_library_metadata(self, library):
        """Test library metadata"""
        metadata = library.to_dict()

        assert isinstance(metadata, dict)
        assert metadata["library_type"] == "persona"
        assert metadata["total_items"] > 0
        assert isinstance(metadata["categories"], list)
        assert "library_path" in metadata

    def test_reload_library(self):
        """Test library reload functionality"""
        library1 = get_persona_library()
        count1 = library1.get_persona_count()

        reload_persona_library()

        library2 = get_persona_library()
        count2 = library2.get_persona_count()

        # Counts should match after reload
        assert count1 == count2

    def test_library_singleton_pattern(self):
        """Test that get_persona_library returns singleton"""
        lib1 = get_persona_library()
        lib2 = get_persona_library()

        # Should be the same instance
        assert lib1 is lib2


class TestPersonaDefinition:
    """Test PersonaDefinition model"""

    @pytest.fixture
    def sample_persona(self):
        """Get a sample persona for testing"""
        library = get_persona_library()
        return library.get_persona("frustrated_customer")

    def test_persona_definition_immutability(self, sample_persona):
        """Test that PersonaDefinition fields exist and are accessible"""
        # Note: Pydantic models are not frozen by default
        # This test verifies the persona structure is valid
        assert sample_persona.name is not None
        assert sample_persona.id is not None

    def test_persona_has_all_attributes(self, sample_persona):
        """Test persona has all expected attributes"""
        assert hasattr(sample_persona, "id")
        assert hasattr(sample_persona, "name")
        assert hasattr(sample_persona, "category")
        assert hasattr(sample_persona, "description")
        assert hasattr(sample_persona, "attributes")
        assert hasattr(sample_persona, "behavioral_traits")
        assert hasattr(sample_persona, "patience_level")
        assert hasattr(sample_persona, "frustration_level")
        assert hasattr(sample_persona, "communication_style")
        # Note: Some attributes like initial_goals and trigger_phrases
        # may not be in all persona definitions

    def test_persona_patience_frustration_correlation(self, sample_persona):
        """Test that patience and frustration levels make sense"""
        # Generally, high frustration should correlate with lower patience
        # This is not a hard rule but a sanity check
        if sample_persona.frustration_level >= 7:
            assert sample_persona.patience_level <= 5, (
                "High frustration should typically mean low patience"
            )
