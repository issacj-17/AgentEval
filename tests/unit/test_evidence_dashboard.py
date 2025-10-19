from __future__ import annotations

import json
from pathlib import Path

import pytest

from agenteval.reporting import dashboard


@pytest.fixture
def sample_run_dir(tmp_path: Path) -> Path:
    run_dir = tmp_path / "20250101T000000"
    campaign_dir = run_dir / "cmp-123"
    (campaign_dir / "dynamodb").mkdir(parents=True, exist_ok=True)
    (campaign_dir / "s3" / "results").mkdir(parents=True, exist_ok=True)
    (campaign_dir / "s3" / "reports").mkdir(parents=True, exist_ok=True)

    (run_dir / "pull-live-reports.log").write_text("pull log")

    (campaign_dir / "dynamodb" / "campaign.json").write_text(
        json.dumps(
            {
                "campaign_id": "cmp-123",
                "campaign_type": "persona",
                "status": "completed",
                "created_at": "2025-01-01T00:00:00Z",
                "config": {
                    "persona_type": "frustrated_customer",
                    "max_turns": 3,
                },
            }
        )
    )

    (campaign_dir / "s3" / "results" / "results.json").write_text(
        json.dumps(
            {
                "results": {
                    "summary": {
                        "total_turns": 3,
                        "success_rate": 0.66,
                        "avg_response_time_ms": 900,
                    }
                }
            }
        )
    )

    (campaign_dir / "s3" / "results" / "report-latest.json").write_text(
        json.dumps(
            {
                "results": {
                    "aggregate_metrics": {
                        "overall_score": 0.72,
                        "quality_score": 0.65,
                        "safety_score": 0.93,
                        "total_turns": 3,
                        "passing_turns": 2,
                    },
                    "turn_results": [
                        {"evaluation": {"pass_fail": {"failed_metrics": ["accuracy", "relevance"]}}}
                    ],
                }
            }
        )
    )

    (campaign_dir / "s3" / "reports" / "demo-report.json").write_text("{}")

    return run_dir


def test_generate_dashboard_creates_summary(
    sample_run_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    insights = dashboard.collect_campaign_insights(sample_run_dir)

    dashboard_path = tmp_path / "dashboard.md"
    summary_path = tmp_path / "summary.md"

    result = dashboard.generate_dashboard(sample_run_dir, dashboard_path, campaigns=insights)
    summary = dashboard.generate_live_demo_summary(sample_run_dir, summary_path, campaigns=insights)

    assert result.exists()
    contents = result.read_text()
    assert "cmp-123" in contents
    assert "frustrated_customer" in contents
    assert "0.72" in contents
    assert "accuracy" in contents

    summary_contents = summary.read_text()
    assert "cmp-123" in summary_contents
    assert "frustrated_customer" in summary_contents


def test_generate_dashboard_handles_missing_reports(tmp_path: Path) -> None:
    run_dir = tmp_path / "20250102T000000"
    campaign_dir = run_dir / "cmp-empty"
    (campaign_dir / "dynamodb").mkdir(parents=True, exist_ok=True)
    (campaign_dir / "dynamodb" / "campaign.json").write_text(
        json.dumps(
            {
                "campaign_id": "cmp-empty",
                "campaign_type": "red_team",
                "status": "completed",
                "config": {"attack_categories": ["injection"]},
            }
        )
    )

    output_path = tmp_path / "dashboard-missing.md"
    result = dashboard.generate_dashboard(run_dir, output_path)

    assert result.exists()
    contents = result.read_text()
    assert "cmp-empty" in contents
    assert "red_team" in contents
