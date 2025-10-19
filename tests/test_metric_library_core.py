from agenteval.evaluation.metrics import (
    MetricCategory,
    MetricLibrary,
    MetricRegistry,
    MetricType,
)


def test_metric_library_loads_from_yaml():
    lib = MetricLibrary()

    assert lib.count() > 0
    categories = lib.list_categories()
    assert "quality" in categories
    assert "safety" in categories

    accuracy = lib.get("accuracy")
    assert accuracy is not None
    assert accuracy.category == "quality"
    assert accuracy.threshold > 0


def test_metric_library_backwards_compatibility_wrappers():
    lib = MetricLibrary()

    assert lib.get_metric("relevance") is not None
    assert len(lib.get_quality_metrics()) == len(lib.get_by_category(MetricCategory.QUALITY.value))
    assert lib.exists("accuracy")


def test_metric_registry_provides_metric_definitions():
    registry = MetricRegistry()
    metrics = registry.get_all_metrics()

    assert len(metrics) >= 11

    accuracy_metric = registry.get_metric(MetricType.ACCURACY)
    assert accuracy_metric.definition is not None
    assert accuracy_metric.definition.id == "accuracy"
    assert accuracy_metric.definition.category == MetricCategory.QUALITY.value
