"""
Unit tests for admin routes

Tests all admin API endpoints for library management and system information.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from agenteval.api.routes import admin


class TestGetSystemInfo:
    """Test /admin/info endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    @patch("agenteval.api.routes.admin.attack_library")
    @patch("agenteval.api.routes.admin.metric_registry")
    @patch("agenteval.api.routes.admin.settings")
    async def test_get_system_info_success(
        self, mock_settings, mock_metric_registry, mock_attack_library, mock_get_persona_lib
    ):
        """Test successful system info retrieval"""
        # Mock persona library
        mock_persona_lib = MagicMock()
        mock_persona_lib.list_persona_ids.return_value = ["persona1", "persona2"]
        mock_persona_lib.get_persona_count.return_value = 2
        mock_persona_lib.list_categories.return_value = ["customer", "support"]
        mock_get_persona_lib.return_value = mock_persona_lib

        # Mock attack library
        mock_attack_library.get_all_attacks.return_value = [1, 2, 3]

        # Mock metric registry
        mock_metric_registry.get_all_metrics.return_value = [1, 2, 3, 4]

        # Mock settings
        mock_settings.app.environment = "test"
        mock_settings.observability.enable_tracing = True
        mock_settings.aws.region = "us-east-1"
        mock_settings.aws.bedrock_persona_model = "claude-3"
        mock_settings.aws.bedrock_redteam_model = "claude-3"
        mock_settings.aws.bedrock_judge_model = "nova-1"

        result = await admin.get_system_info()

        assert result["version"] == "1.0.0"
        assert result["environment"] == "test"
        assert result["capabilities"]["agents"]["persona_types"] == ["persona1", "persona2"]
        assert result["capabilities"]["agents"]["attack_categories"] == 3
        assert result["aws"]["region"] == "us-east-1"


class TestListMetrics:
    """Test /admin/metrics endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.metric_registry")
    async def test_list_metrics_success(self, mock_registry):
        """Test successful metrics listing"""
        mock_metric = MagicMock()
        mock_metric.metric_type.value = "relevance"
        mock_metric.threshold = 0.7
        mock_metric.category.value = "quality"

        mock_registry.get_all_metrics.return_value = [mock_metric, mock_metric]
        mock_registry.get_quality_metrics.return_value = [mock_metric]
        mock_registry.get_safety_metrics.return_value = []
        mock_registry.get_agent_metrics.return_value = [mock_metric]

        result = await admin.list_metrics()

        assert result["total_metrics"] == 2
        assert "metrics_by_category" in result
        assert len(result["metrics_by_category"]["quality"]) == 1
        assert result["metrics_by_category"]["quality"][0]["type"] == "relevance"


class TestListAttacks:
    """Test /admin/attacks endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.attack_library")
    @patch("agenteval.api.routes.admin.AttackCategory")
    async def test_list_attacks_success(self, mock_attack_category, mock_attack_lib):
        """Test successful attacks listing"""
        # Mock attack
        mock_attack = MagicMock()
        mock_attack.name = "SQL Injection"
        mock_attack.severity.value = "high"
        mock_attack.description = "SQL injection attack"
        mock_attack.tags = ["sql", "injection"]

        # Mock category enum
        mock_attack_category.__iter__ = MagicMock(return_value=iter([MagicMock(value="injection")]))

        mock_attack_lib.get_attacks_by_category.return_value = [mock_attack]
        mock_attack_lib.get_attack_count.return_value = {
            "total": 10,
            "injection": 5,
            "jailbreak": 5,
        }

        result = await admin.list_attacks()

        assert result["total_attacks"] == 10
        assert "counts_by_category" in result
        assert "attacks_by_category" in result


class TestListPersonas:
    """Test /admin/personas endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    async def test_list_personas_success(self, mock_get_persona_lib):
        """Test successful personas listing"""
        mock_persona = MagicMock()
        mock_persona.id = "frustrated_customer"
        mock_persona.name = "Frustrated Customer"
        mock_persona.category = "customer"
        mock_persona.description = "A frustrated customer"
        mock_persona.attributes = {"patience": "low"}
        mock_persona.behavioral_traits = ["impatient"]
        mock_persona.patience_level = 1
        mock_persona.frustration_level = 5
        mock_persona.communication_style = "direct"

        mock_persona_lib = MagicMock()
        mock_persona_lib.get_all_personas.return_value = [mock_persona]
        mock_persona_lib.list_categories.return_value = ["customer"]
        mock_persona_lib.get_personas_by_category.return_value = [mock_persona]
        mock_persona_lib.get_persona_count.return_value = 1
        mock_get_persona_lib.return_value = mock_persona_lib

        result = await admin.list_personas()

        assert result["total_personas"] == 1
        assert "frustrated_customer" in result["personas"]
        assert result["personas"]["frustrated_customer"]["name"] == "Frustrated Customer"


class TestGetPersonaDetail:
    """Test /admin/personas/{persona_id} endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    async def test_get_persona_detail_success(self, mock_get_persona_lib):
        """Test successful persona detail retrieval"""
        mock_persona = MagicMock()
        mock_persona.to_dict.return_value = {"id": "test_persona", "name": "Test Persona"}

        mock_persona_lib = MagicMock()
        mock_persona_lib.get_persona.return_value = mock_persona
        mock_get_persona_lib.return_value = mock_persona_lib

        result = await admin.get_persona_detail("test_persona")

        assert result["persona"]["id"] == "test_persona"

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    async def test_get_persona_detail_not_found(self, mock_get_persona_lib):
        """Test persona not found raises 404"""
        mock_persona_lib = MagicMock()
        mock_persona_lib.get_persona.return_value = None
        mock_get_persona_lib.return_value = mock_persona_lib

        with pytest.raises(HTTPException) as exc_info:
            await admin.get_persona_detail("nonexistent")

        assert exc_info.value.status_code == 404


class TestReloadPersonaLibrary:
    """Test /admin/personas/reload endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.reload_personas")
    @patch("agenteval.api.routes.admin.get_persona_library")
    async def test_reload_persona_library_success(self, mock_get_persona_lib, mock_reload):
        """Test successful persona library reload"""
        mock_persona_lib = MagicMock()
        mock_persona_lib.get_persona_count.return_value = 5
        mock_persona_lib.list_persona_ids.return_value = ["p1", "p2"]
        mock_persona_lib.list_categories.return_value = ["customer"]
        mock_persona_lib.library_path = "/path/to/personas.yaml"
        mock_get_persona_lib.return_value = mock_persona_lib

        result = await admin.reload_persona_library_endpoint()

        assert result["message"] == "Persona library reloaded successfully"
        assert result["total_items"] == 5
        mock_reload.assert_called_once()

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.reload_personas")
    async def test_reload_persona_library_failure(self, mock_reload):
        """Test persona library reload failure"""
        mock_reload.side_effect = Exception("Reload failed")

        with pytest.raises(HTTPException) as exc_info:
            await admin.reload_persona_library_endpoint()

        assert exc_info.value.status_code == 500


class TestValidatePersonaLibrary:
    """Test /admin/personas/validate endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    async def test_validate_persona_library_success(self, mock_get_persona_lib):
        """Test successful persona library validation"""
        mock_persona_lib = MagicMock()
        mock_persona_lib.validate.return_value = {"valid": True, "errors": []}
        mock_get_persona_lib.return_value = mock_persona_lib

        result = await admin.validate_persona_library()

        assert result["library_type"] == "persona"
        assert result["validation"]["valid"] is True


class TestGetAttackDetail:
    """Test /admin/attacks/{attack_id} endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.attack_library")
    async def test_get_attack_detail_success(self, mock_attack_lib):
        """Test successful attack detail retrieval"""
        mock_attack = MagicMock()
        mock_attack.to_dict.return_value = {"name": "SQL Injection", "severity": "high"}

        mock_attack_lib.get_attack.return_value = mock_attack

        result = await admin.get_attack_detail("sql_injection")

        assert result["attack"]["name"] == "SQL Injection"

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.attack_library")
    async def test_get_attack_detail_not_found(self, mock_attack_lib):
        """Test attack not found raises 404"""
        mock_attack_lib.get_attack.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await admin.get_attack_detail("nonexistent")

        assert exc_info.value.status_code == 404


class TestReloadAttackLibrary:
    """Test /admin/attacks/reload endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.reload_attack_library")
    @patch("agenteval.api.routes.admin.get_attack_library")
    async def test_reload_attack_library_success(self, mock_get_attack_lib, mock_reload):
        """Test successful attack library reload"""
        mock_attack_lib = MagicMock()
        mock_attack_lib.count.return_value = 10
        mock_attack_lib.list_ids.return_value = ["a1", "a2"]
        mock_attack_lib.list_categories.return_value = ["injection"]
        mock_attack_lib.library_path = "/path/to/attacks.yaml"
        mock_get_attack_lib.return_value = mock_attack_lib

        result = await admin.reload_attack_library_endpoint()

        assert result["message"] == "Attack library reloaded successfully"
        assert result["total_items"] == 10
        mock_reload.assert_called_once()


class TestValidateAttackLibrary:
    """Test /admin/attacks/validate endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_attack_library")
    async def test_validate_attack_library_success(self, mock_get_attack_lib):
        """Test successful attack library validation"""
        mock_attack_lib = MagicMock()
        mock_attack_lib.validate.return_value = {"valid": True}
        mock_get_attack_lib.return_value = mock_attack_lib

        result = await admin.validate_attack_library()

        assert result["library_type"] == "attack"
        assert result["validation"]["valid"] is True


class TestGetMetricDetail:
    """Test /admin/metrics/{metric_id} endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_get_metric_detail_success(self, mock_get_metric_lib):
        """Test successful metric detail retrieval"""
        mock_metric = MagicMock()
        mock_metric.to_dict.return_value = {"type": "relevance", "threshold": 0.7}

        mock_metric_lib = MagicMock()
        mock_metric_lib.get_metric.return_value = mock_metric
        mock_get_metric_lib.return_value = mock_metric_lib

        result = await admin.get_metric_detail("relevance")

        assert result["metric"]["type"] == "relevance"

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_get_metric_detail_not_found(self, mock_get_metric_lib):
        """Test metric not found raises 404"""
        mock_metric_lib = MagicMock()
        mock_metric_lib.get_metric.return_value = None
        mock_get_metric_lib.return_value = mock_metric_lib

        with pytest.raises(HTTPException) as exc_info:
            await admin.get_metric_detail("nonexistent")

        assert exc_info.value.status_code == 404


class TestReloadMetricLibrary:
    """Test /admin/metrics/reload endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.reload_metric_library")
    @patch("agenteval.api.routes.admin.metric_registry")
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_reload_metric_library_success(
        self, mock_get_metric_lib, mock_registry, mock_reload
    ):
        """Test successful metric library reload"""
        mock_metric_lib = MagicMock()
        mock_metric_lib.count.return_value = 15
        mock_metric_lib.list_ids.return_value = ["m1", "m2"]
        mock_metric_lib.list_categories.return_value = ["quality"]
        mock_metric_lib.library_path = "/path/to/metrics.yaml"
        mock_get_metric_lib.return_value = mock_metric_lib

        result = await admin.reload_metric_library_endpoint()

        assert result["message"] == "Metric library reloaded successfully"
        assert result["total_items"] == 15
        assert result["registry_reloaded"] is True
        mock_reload.assert_called_once()
        mock_registry.reload.assert_called_once()


class TestValidateMetricLibrary:
    """Test /admin/metrics/validate endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_validate_metric_library_success(self, mock_get_metric_lib):
        """Test successful metric library validation"""
        mock_metric_lib = MagicMock()
        mock_metric_lib.validate.return_value = {"valid": True}
        mock_get_metric_lib.return_value = mock_metric_lib

        result = await admin.validate_metric_library()

        assert result["library_type"] == "metric"


class TestGetLibrariesOverview:
    """Test /admin/libraries endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    @patch("agenteval.api.routes.admin.get_attack_library")
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_get_libraries_overview_success(
        self, mock_get_metric_lib, mock_get_attack_lib, mock_get_persona_lib
    ):
        """Test successful libraries overview retrieval"""
        # Mock persona library
        mock_persona_lib = MagicMock()
        mock_persona_lib.count.return_value = 5
        mock_persona_lib.list_categories.return_value = ["customer"]
        mock_persona_lib.library_path = "/personas.yaml"
        mock_persona_lib.library_type.value = "persona"
        mock_get_persona_lib.return_value = mock_persona_lib

        # Mock attack library
        mock_attack_lib = MagicMock()
        mock_attack_lib.count.return_value = 10
        mock_attack_lib.list_categories.return_value = ["injection"]
        mock_attack_lib.library_path = "/attacks.yaml"
        mock_attack_lib.library_type.value = "attack"
        mock_get_attack_lib.return_value = mock_attack_lib

        # Mock metric library
        mock_metric_lib = MagicMock()
        mock_metric_lib.count.return_value = 15
        mock_metric_lib.list_categories.return_value = ["quality"]
        mock_metric_lib.library_path = "/metrics.yaml"
        mock_metric_lib.library_type.value = "metric"
        mock_get_metric_lib.return_value = mock_metric_lib

        result = await admin.get_libraries_overview()

        assert result["totals"]["personas"] == 5
        assert result["totals"]["attacks"] == 10
        assert result["totals"]["metrics"] == 15
        assert "libraries" in result


class TestReloadAllLibraries:
    """Test /admin/libraries/reload endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.reload_personas")
    @patch("agenteval.api.routes.admin.reload_attack_library")
    @patch("agenteval.api.routes.admin.reload_metric_library")
    @patch("agenteval.api.routes.admin.metric_registry")
    @patch("agenteval.api.routes.admin.get_persona_library")
    @patch("agenteval.api.routes.admin.get_attack_library")
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_reload_all_libraries_success(
        self,
        mock_get_metric_lib,
        mock_get_attack_lib,
        mock_get_persona_lib,
        mock_registry,
        mock_reload_metric,
        mock_reload_attack,
        mock_reload_persona,
    ):
        """Test successful reload of all libraries"""
        # Mock libraries
        mock_persona_lib = MagicMock()
        mock_persona_lib.count.return_value = 5
        mock_persona_lib.list_categories.return_value = ["customer"]

        mock_attack_lib = MagicMock()
        mock_attack_lib.count.return_value = 10
        mock_attack_lib.list_categories.return_value = ["injection"]

        mock_metric_lib = MagicMock()
        mock_metric_lib.count.return_value = 15
        mock_metric_lib.list_categories.return_value = ["quality"]

        mock_get_persona_lib.return_value = mock_persona_lib
        mock_get_attack_lib.return_value = mock_attack_lib
        mock_get_metric_lib.return_value = mock_metric_lib

        result = await admin.reload_all_libraries()

        assert result["message"] == "All libraries reloaded successfully"
        assert result["libraries_reloaded"] == ["persona", "attack", "metric"]
        mock_reload_persona.assert_called_once()
        mock_reload_attack.assert_called_once()
        mock_reload_metric.assert_called_once()
        mock_registry.reload.assert_called_once()


class TestValidateAllLibraries:
    """Test /admin/libraries/validate endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    @patch("agenteval.api.routes.admin.get_attack_library")
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_validate_all_libraries_success(
        self, mock_get_metric_lib, mock_get_attack_lib, mock_get_persona_lib
    ):
        """Test successful validation of all libraries"""
        mock_persona_lib = MagicMock()
        mock_persona_lib.validate.return_value = {"valid": True}

        mock_attack_lib = MagicMock()
        mock_attack_lib.validate.return_value = {"valid": True}

        mock_metric_lib = MagicMock()
        mock_metric_lib.validate.return_value = {"valid": True}

        mock_get_persona_lib.return_value = mock_persona_lib
        mock_get_attack_lib.return_value = mock_attack_lib
        mock_get_metric_lib.return_value = mock_metric_lib

        result = await admin.validate_all_libraries()

        assert result["all_valid"] is True
        assert result["validations"]["persona"]["valid"] is True

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    @patch("agenteval.api.routes.admin.get_attack_library")
    @patch("agenteval.api.routes.admin.get_metric_library")
    async def test_validate_all_libraries_with_invalid(
        self, mock_get_metric_lib, mock_get_attack_lib, mock_get_persona_lib
    ):
        """Test validation with one invalid library"""
        mock_persona_lib = MagicMock()
        mock_persona_lib.validate.return_value = {"valid": True}

        mock_attack_lib = MagicMock()
        mock_attack_lib.validate.return_value = {"valid": False}

        mock_metric_lib = MagicMock()
        mock_metric_lib.validate.return_value = {"valid": True}

        mock_get_persona_lib.return_value = mock_persona_lib
        mock_get_attack_lib.return_value = mock_attack_lib
        mock_get_metric_lib.return_value = mock_metric_lib

        result = await admin.validate_all_libraries()

        assert result["all_valid"] is False


class TestClearCache:
    """Test /admin/cache/clear endpoint"""

    @pytest.mark.asyncio
    async def test_clear_cache_success(self):
        """Test successful cache clearing"""
        mock_xray = MagicMock()
        mock_xray._trace_cache = MagicMock()
        mock_xray._trace_cache.clear = MagicMock()

        result = await admin.clear_cache(xray=mock_xray)

        assert result["message"] == "Caches cleared successfully"
        assert "xray_trace_cache" in result["caches_cleared"]
        mock_xray._trace_cache.clear.assert_called_once()


class TestGetSystemStats:
    """Test /admin/stats endpoint"""

    @pytest.mark.asyncio
    @patch("agenteval.api.routes.admin.get_persona_library")
    @patch("agenteval.api.routes.admin.attack_library")
    @patch("agenteval.api.routes.admin.metric_registry")
    async def test_get_system_stats_success(
        self, mock_metric_registry, mock_attack_library, mock_get_persona_lib
    ):
        """Test successful system stats retrieval"""
        mock_dynamodb = AsyncMock()
        mock_dynamodb.list_campaigns = AsyncMock(
            return_value=[
                {"campaign_id": "c1", "status": "completed", "stats": {"total_turns": 10}},
                {"campaign_id": "c2", "status": "running", "stats": {"total_turns": 5}},
                {"campaign_id": "c3", "status": "completed", "stats": {"total_turns": 8}},
            ]
        )

        mock_persona_lib = MagicMock()
        mock_persona_lib.get_persona_count.return_value = 5
        mock_get_persona_lib.return_value = mock_persona_lib

        mock_attack_library.get_all_attacks.return_value = [1, 2, 3]
        mock_metric_registry.get_all_metrics.return_value = [1, 2, 3, 4]

        result = await admin.get_system_stats(dynamodb=mock_dynamodb)

        assert result["campaigns"]["total"] == 3
        assert result["campaigns"]["completed"] == 2
        assert result["campaigns"]["running"] == 1
        assert result["turns"]["total"] == 23
        assert result["capabilities"]["total_personas"] == 5

    @pytest.mark.asyncio
    async def test_get_system_stats_error_handling(self):
        """Test system stats error handling"""
        mock_dynamodb = AsyncMock()
        mock_dynamodb.list_campaigns = AsyncMock(side_effect=Exception("DB error"))

        with pytest.raises(HTTPException) as exc_info:
            await admin.get_system_stats(dynamodb=mock_dynamodb)

        assert exc_info.value.status_code == 500
