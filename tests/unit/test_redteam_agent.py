"""
Unit tests for RedTeamAgent (targeted key methods).

Tests initialization, validation, async attack execution, and utility methods.
"""

from unittest.mock import MagicMock, patch

from agenteval.agents.redteam_agent import RedTeamAgent
from agenteval.redteam.library import AttackCategory, AttackSeverity


class TestRedTeamAgentInitialization:
    """Test suite for RedTeamAgent initialization"""

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_init_default_values(self, mock_lib):
        """Test initialization with default values"""
        mock_lib.list_attack_ids.return_value = ["attack1", "attack2"]

        agent = RedTeamAgent()

        assert agent.agent_id is not None
        assert agent.agent_type == "redteam"
        # Default is list of all AttackCategory enum values
        assert isinstance(agent.attack_categories, list)
        assert len(agent.attack_categories) > 0
        assert agent.severity_threshold is None  # Default is None (all severities)
        assert len(agent.attacks_attempted) == 0
        assert len(agent.attacks_successful) == 0

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_init_custom_agent_id(self, mock_lib):
        """Test initialization with custom agent_id"""
        mock_lib.list_attack_ids.return_value = []

        agent = RedTeamAgent(agent_id="redteam-123")

        assert agent.agent_id == "redteam-123"

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_init_specific_attack_categories(self, mock_lib):
        """Test initialization with specific attack categories"""
        mock_lib.list_attack_ids.return_value = []

        categories = [AttackCategory.INJECTION, AttackCategory.JAILBREAK]
        agent = RedTeamAgent(attack_categories=categories)

        assert agent.attack_categories == categories

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_init_custom_severity_threshold(self, mock_lib):
        """Test initialization with custom severity threshold"""
        mock_lib.list_attack_ids.return_value = []

        agent = RedTeamAgent(severity_threshold=AttackSeverity.HIGH)

        assert agent.severity_threshold == AttackSeverity.HIGH

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_init_custom_success_evaluator(self, mock_lib):
        """Test initialization with custom success evaluator"""
        mock_lib.list_attack_ids.return_value = []

        mock_evaluator = MagicMock()
        agent = RedTeamAgent(success_evaluator=mock_evaluator)

        assert agent.success_evaluator == mock_evaluator


class TestGetDefaultModel:
    """Test suite for default model selection"""

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_get_default_model(self, mock_lib):
        """Test that default model is from settings"""
        mock_lib.list_attack_ids.return_value = []

        agent = RedTeamAgent()

        model = agent._get_default_model()

        # Should return bedrock redteam model from settings
        assert model is not None
        assert isinstance(model, str)


class TestRedTeamAgentMetadata:
    """Test suite for redteam agent metadata"""

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_agent_type_is_redteam(self, mock_lib):
        """Test that agent type is set to redteam"""
        mock_lib.list_attack_ids.return_value = []

        agent = RedTeamAgent()

        assert agent.agent_type == "redteam"

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_get_agent_info(self, mock_lib):
        """Test getting agent information"""
        mock_lib.list_attack_ids.return_value = []

        agent = RedTeamAgent(agent_id="test-redteam")

        info = agent.get_agent_info()

        assert info["agent_id"] == "test-redteam"
        assert info["agent_type"] == "redteam"

    @patch("agenteval.agents.redteam_agent.attack_library")
    def test_attack_tracking_initialized(self, mock_lib):
        """Test that attack tracking lists are initialized"""
        mock_lib.list_attack_ids.return_value = ["attack1", "attack2", "attack3"]

        agent = RedTeamAgent()

        # Verify attack tracking lists are initialized
        assert hasattr(agent, "attacks_attempted")
        assert hasattr(agent, "attacks_successful")
        assert hasattr(agent, "attack_results")
        assert isinstance(agent.attacks_attempted, list)
        assert isinstance(agent.attacks_successful, list)
        assert isinstance(agent.attack_results, list)
