from pathlib import Path

import yaml

from agenteval.evaluation.metrics import AccuracyMetric, MetricDefinition


def test_metric_definition_supports_optional_fields():
    definition = MetricDefinition(
        id="unit_test_metric",
        name="Unit Test Metric",
        category="quality",
        description="Synthetic metric for unit testing",
        metadata={"weight": 1.0},
        threshold=0.5,
        evaluation_criteria=["criterion 1"],
        scoring_guide={"high": "Good", "low": "Bad"},
        evaluation_prompt="Evaluate the response.",
    )

    metric = AccuracyMetric(definition=definition)

    assert metric.definition is definition
    assert metric.threshold == definition.threshold
    assert metric.evaluation_criteria == definition.evaluation_criteria
    assert metric.scoring_guide == definition.scoring_guide


def test_metric_yaml_contains_required_fields():
    yaml_path = Path("metrics") / "library.yaml"
    assert yaml_path.exists(), "metrics/library.yaml is missing"

    data = yaml.safe_load(yaml_path.read_text())
    assert isinstance(data, dict)
    assert "metrics" in data
    metrics = data["metrics"]
    assert isinstance(metrics, list) and len(metrics) > 0

    required_fields = {"id", "name", "category", "description", "threshold"}
    first_metric = metrics[0]
    assert required_fields.issubset(first_metric.keys())
