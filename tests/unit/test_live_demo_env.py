from __future__ import annotations

import os
from pathlib import Path

import pytest

from agenteval.utils.live_demo_env import (
    bootstrap_live_demo_env,
    refresh_settings,
)


def test_bootstrap_returns_false_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.live-demo"
    monkeypatch.delenv("DYNAMODB_CAMPAIGNS_TABLE", raising=False)
    monkeypatch.delenv("AWS_DYNAMODB_CAMPAIGNS_TABLE", raising=False)

    assert bootstrap_live_demo_env(env_path=env_file) is False


def test_bootstrap_applies_legacy_prefix_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = tmp_path / ".env.live-demo"
    env_file.write_text("DYNAMODB_CAMPAIGNS_TABLE=legacy-table\nENABLE_XRAY_TRACING=true\n")

    monkeypatch.delenv("DYNAMODB_CAMPAIGNS_TABLE", raising=False)
    monkeypatch.delenv("AWS_DYNAMODB_CAMPAIGNS_TABLE", raising=False)
    monkeypatch.delenv("ENABLE_TRACING", raising=False)
    monkeypatch.delenv("ENABLE_XRAY_TRACING", raising=False)

    assert bootstrap_live_demo_env(env_path=env_file) is True
    out = capsys.readouterr().out
    assert "legacy environment variables" in out
    assert os.environ["DYNAMODB_CAMPAIGNS_TABLE"] == "legacy-table"
    assert os.environ["AWS_DYNAMODB_CAMPAIGNS_TABLE"] == "legacy-table"
    assert os.environ["ENABLE_TRACING"] == "true"


def test_bootstrap_skips_prefix_map_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env.live-demo"
    env_file.write_text("DYNAMODB_EVALUATIONS_TABLE=legacy-evals\n")

    monkeypatch.delenv("DYNAMODB_EVALUATIONS_TABLE", raising=False)
    monkeypatch.delenv("AWS_DYNAMODB_EVALUATIONS_TABLE", raising=False)

    assert bootstrap_live_demo_env(env_path=env_file, apply_prefix_map=False) is True
    assert os.environ["DYNAMODB_EVALUATIONS_TABLE"] == "legacy-evals"
    assert "AWS_DYNAMODB_EVALUATIONS_TABLE" not in os.environ


def test_refresh_settings_reinstantiates_global(monkeypatch: pytest.MonkeyPatch) -> None:
    from agenteval import config as config_module

    sentinel = object()
    original_settings = config_module.settings
    monkeypatch.setattr(config_module, "settings", sentinel, raising=True)

    refreshed = refresh_settings()

    assert refreshed is config_module.settings
    assert refreshed is not sentinel
    assert refreshed is not original_settings
