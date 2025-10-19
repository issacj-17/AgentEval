"""
Unit tests for MetricLibrary

Tests metric library loading, validation, and retrieval.
"""

import pytest

from agenteval.evaluation.metrics import (
    MetricCategory,
    MetricRegistry,
    MetricType,
    get_metric_library,
    reload_metric_library,
)


class TestMetricLibrary:
    """Test MetricLibrary functionality"""

    @pytest.fixture
    def library(self):
        """Get metric library instance"""
        return get_metric_library()

    def test_library_loads_successfully(self, library):
        """Test that metric library loads from YAML"""
        assert library is not None
        assert library.count() > 0

    def test_library_has_expected_categories(self, library):
        """Test that library has expected metric categories"""
        categories = library.list_categories()
        assert isinstance(categories, list)
        assert len(categories) > 0

        # Expected categories
        expected_categories = ["quality", "safety", "agent_specific"]
        for expected in expected_categories:
            assert expected in categories, f"Missing expected category: {expected}"

    def test_get_metric_by_id(self, library):
        """Test retrieving specific metric by ID"""
        metric = library.get("accuracy")
        assert metric is not None
        assert metric.id == "accuracy"
        assert metric.name is not None
        assert metric.category is not None

    def test_get_nonexistent_metric_returns_none(self, library):
        """Test that nonexistent metric returns None"""
        metric = library.get("does_not_exist_123")
        assert metric is None

    def test_list_metric_ids(self, library):
        """Test listing all metric IDs"""
        ids = library.list_ids()
        assert isinstance(ids, list)
        assert len(ids) > 0
        assert "accuracy" in ids
        assert "relevance" in ids

    def test_get_metrics_by_category(self, library):
        """Test filtering metrics by category"""
        # Quality metrics
        quality_metrics = library.get_by_category("quality")
        assert len(quality_metrics) > 0
        for metric in quality_metrics:
            assert metric.category == "quality"

        # Safety metrics
        safety_metrics = library.get_by_category("safety")
        assert len(safety_metrics) > 0
        for metric in safety_metrics:
            assert metric.category == "safety"

    def test_metric_has_required_fields(self, library):
        """Test that metrics have all required fields"""
        all_metrics = library.get_all_metrics()
        for metric in all_metrics:
            # Required fields
            assert metric.id
            assert metric.name
            assert metric.category
            assert metric.description
            assert isinstance(metric.threshold, (int, float))
            assert 0.0 <= metric.threshold <= 1.0

            # List fields
            assert isinstance(metric.evaluation_criteria, list)
            assert len(metric.evaluation_criteria) > 0

    def test_backward_compatibility_methods(self, library):
        """Test backward compatibility wrapper methods"""
        # get_metric wrapper
        metric = library.get_metric("relevance")
        assert metric is not None
        assert metric.id == "relevance"

        # get_all_metrics
        all_metrics = library.get_all_metrics()
        assert len(all_metrics) > 0

        # get_quality_metrics
        quality = library.get_quality_metrics()
        assert len(quality) > 0
        for m in quality:
            assert m.category == "quality"

        # get_safety_metrics
        safety = library.get_safety_metrics()
        assert len(safety) > 0
        for m in safety:
            assert m.category == "safety"

        # get_agent_metrics
        agent = library.get_agent_metrics()
        assert len(agent) > 0
        for m in agent:
            assert m.category == "agent_specific"

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
        assert metadata["library_type"] == "metric"
        assert metadata["total_items"] > 0
        assert isinstance(metadata["categories"], list)
        assert "library_path" in metadata

    def test_reload_library(self):
        """Test library reload functionality"""
        library1 = get_metric_library()
        count1 = library1.count()

        reload_metric_library()

        library2 = get_metric_library()
        count2 = library2.count()

        # Counts should match after reload
        assert count1 == count2

    def test_library_singleton_pattern(self):
        """Test that get_metric_library returns singleton"""
        lib1 = get_metric_library()
        lib2 = get_metric_library()

        # Should be the same instance
        assert lib1 is lib2

    def test_exists_method(self, library):
        """Test exists() method for checking metric presence"""
        assert library.exists("accuracy") is True
        assert library.exists("does_not_exist") is False


class TestMetricRegistry:
    """Test MetricRegistry integration with MetricLibrary"""

    @pytest.fixture
    def registry(self):
        """Get metric registry instance"""
        return MetricRegistry()

    def test_registry_initializes_with_library(self, registry):
        """Test that registry loads metrics from library"""
        all_metrics = registry.get_all_metrics()
        assert len(all_metrics) > 0

    def test_registry_get_metric_by_type(self, registry):
        """Test retrieving metric by MetricType enum"""
        accuracy = registry.get_metric(MetricType.ACCURACY)
        assert accuracy is not None
        assert accuracy.metric_type == MetricType.ACCURACY

    def test_metric_instances_have_definitions(self, registry):
        """Test that metric instances have YAML definitions loaded"""
        accuracy = registry.get_metric(MetricType.ACCURACY)

        assert accuracy.definition is not None
        assert accuracy.definition.name is not None
        assert accuracy.threshold > 0
        assert len(accuracy.evaluation_criteria) > 0

    def test_registry_category_methods(self, registry):
        """Test registry methods for filtering by category"""
        quality = registry.get_quality_metrics()
        assert len(quality) > 0
        for m in quality:
            assert m.category == MetricCategory.QUALITY

        safety = registry.get_safety_metrics()
        assert len(safety) > 0
        for m in safety:
            assert m.category == MetricCategory.SAFETY

        agent = registry.get_agent_metrics()
        assert len(agent) > 0
        for m in agent:
            assert m.category == MetricCategory.AGENT_SPECIFIC

    def test_registry_reload(self, registry):
        """Test registry reload functionality"""
        count_before = len(registry.get_all_metrics())

        registry.reload()

        count_after = len(registry.get_all_metrics())
        assert count_before == count_after
