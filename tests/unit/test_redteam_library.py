"""
Unit tests for RedTeam Attack Library.

Tests attack pattern management and library operations.
"""

from unittest.mock import MagicMock, patch

from agenteval.redteam.library import AttackLibrary, AttackPattern, AttackSeverity


class TestAttackPattern:
    """Test suite for AttackPattern class"""

    def test_create_attack_pattern(self):
        """Test creating an attack pattern"""
        pattern = AttackPattern(
            id="sql_injection_001",
            name="SQL Injection Basic",
            category="injection",
            description="Basic SQL injection test",
            metadata={"version": "1.0"},
            severity="high",
            template="SELECT * FROM users WHERE id = '{input}'",
            variations=["' OR '1'='1", "admin'--"],
            success_indicators=["error", "syntax"],
            owasp_mapping=["A03:2021"],
        )

        assert pattern.id == "sql_injection_001"
        assert pattern.name == "SQL Injection Basic"
        assert pattern.category == "injection"
        assert pattern.severity == "high"
        assert pattern.severity_enum == AttackSeverity.HIGH
        assert len(pattern.variations) == 2
        assert len(pattern.success_indicators) == 2

    def test_attack_pattern_severity_enum_conversion(self):
        """Test that severity string is converted to enum"""
        pattern = AttackPattern(
            id="test",
            name="Test",
            category="injection",
            description="Test",
            metadata={},
            severity="critical",
            template="test",
            variations=[],
            success_indicators=[],
            owasp_mapping=[],
        )

        assert pattern.severity_enum == AttackSeverity.CRITICAL

    def test_attack_pattern_invalid_severity_fallback(self):
        """Test fallback for invalid severity"""
        pattern = AttackPattern(
            id="test",
            name="Test",
            category="injection",
            description="Test",
            metadata={},
            severity="invalid_severity",
            template="test",
            variations=[],
            success_indicators=[],
            owasp_mapping=[],
        )

        # Should fallback to MEDIUM
        assert pattern.severity_enum == AttackSeverity.MEDIUM

    def test_check_success_basic(self):
        """Test basic success detection"""
        pattern = AttackPattern(
            id="test",
            name="Test",
            category="injection",
            description="Test",
            metadata={},
            severity="high",
            template="test",
            variations=[],
            success_indicators=["error", "exception", "failed"],
            owasp_mapping=[],
        )

        assert pattern.check_success("An error occurred") is True
        assert pattern.check_success("Exception: Invalid input") is True
        assert pattern.check_success("Operation failed") is True
        assert pattern.check_success("Success!") is False

    def test_check_success_case_insensitive(self):
        """Test case-insensitive success detection"""
        pattern = AttackPattern(
            id="test",
            name="Test",
            category="injection",
            description="Test",
            metadata={},
            severity="high",
            template="test",
            variations=[],
            success_indicators=["ERROR", "Exception"],
            owasp_mapping=[],
        )

        assert pattern.check_success("an error happened") is True
        assert pattern.check_success("EXCEPTION: bad input") is True
        assert pattern.check_success("all good") is False

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict includes all attack-specific fields"""
        pattern = AttackPattern(
            id="test",
            name="Test Attack",
            category="injection",
            description="Test description",
            metadata={"author": "test"},
            severity="high",
            template="test template",
            variations=["var1", "var2"],
            success_indicators=["error"],
            owasp_mapping=["A03"],
        )

        result = pattern.to_dict()

        assert result["id"] == "test"
        assert result["name"] == "Test Attack"
        assert result["severity"] == "high"
        assert result["severity_enum"] == "high"
        assert result["template"] == "test template"
        assert result["variations"] == ["var1", "var2"]
        assert result["success_indicators"] == ["error"]
        assert result["owasp_mapping"] == ["A03"]


class TestAttackLibrary:
    """Test suite for AttackLibrary class"""

    @patch("agenteval.redteam.library.Path")
    def test_init_with_custom_path(self, mock_path):
        """Test initialization with custom path"""
        mock_file = MagicMock()
        mock_file.exists.return_value = False
        mock_path.return_value = mock_file

        library = AttackLibrary(library_path="custom/attacks.yaml")

        assert library.library_type.value == "attack"

    def test_backward_compatibility_attacks_attribute(self):
        """Test that .attacks attribute exists for backward compatibility"""
        with patch.object(AttackLibrary, "load", return_value=None):
            library = AttackLibrary()

            # .attacks should be an alias for .items
            assert library.attacks == library.items

    @patch("agenteval.redteam.library.AttackLibrary.load")
    def test_get_attacks_by_category(self, mock_load):
        """Test filtering attacks by category"""
        library = AttackLibrary()

        # Manually populate items for testing
        library.items = {
            "inject1": AttackPattern(
                id="inject1",
                name="SQL Injection",
                category="injection",
                description="Test",
                metadata={},
                severity="high",
                template="test",
                variations=[],
                success_indicators=[],
                owasp_mapping=[],
            ),
            "inject2": AttackPattern(
                id="inject2",
                name="Command Injection",
                category="injection",
                description="Test",
                metadata={},
                severity="high",
                template="test",
                variations=[],
                success_indicators=[],
                owasp_mapping=[],
            ),
            "jailbreak1": AttackPattern(
                id="jailbreak1",
                name="Role Reversal",
                category="jailbreak",
                description="Test",
                metadata={},
                severity="medium",
                template="test",
                variations=[],
                success_indicators=[],
                owasp_mapping=[],
            ),
        }

        # Test getting by category
        injection_attacks = library.get_attacks_by_category("injection")
        assert len(injection_attacks) == 2
        assert all(a.category == "injection" for a in injection_attacks)

        jailbreak_attacks = library.get_attacks_by_category("jailbreak")
        assert len(jailbreak_attacks) == 1
        assert jailbreak_attacks[0].id == "jailbreak1"

    @patch("agenteval.redteam.library.AttackLibrary.load")
    def test_get_all_attacks(self, mock_load):
        """Test getting all attacks"""
        library = AttackLibrary()

        library.items = {
            "attack1": AttackPattern(
                id="attack1",
                name="A1",
                category="injection",
                description="T",
                metadata={},
                severity="high",
                template="t",
                variations=[],
                success_indicators=[],
                owasp_mapping=[],
            ),
            "attack2": AttackPattern(
                id="attack2",
                name="A2",
                category="jailbreak",
                description="T",
                metadata={},
                severity="medium",
                template="t",
                variations=[],
                success_indicators=[],
                owasp_mapping=[],
            ),
        }

        all_attacks = library.get_all_attacks()
        assert len(all_attacks) == 2
        assert any(a.id == "attack1" for a in all_attacks)
        assert any(a.id == "attack2" for a in all_attacks)

    def test_get_default_library_path(self):
        """Test default library path generation"""
        library = AttackLibrary()

        path = library._get_default_library_path()

        # Should return a path ending with attacks/library.yaml
        assert "attacks" in path
        assert "library.yaml" in path
