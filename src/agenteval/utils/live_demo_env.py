"""
Utilities for working with the live demo environment configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

__all__ = ["bootstrap_live_demo_env", "refresh_settings"]

_DEFAULT_ENV_FILENAME = ".env.live-demo"
_LEGACY_ENV_MAP: dict[str, str] = {
    "DYNAMODB_CAMPAIGNS_TABLE": "AWS_DYNAMODB_CAMPAIGNS_TABLE",
    "DYNAMODB_TURNS_TABLE": "AWS_DYNAMODB_TURNS_TABLE",
    "DYNAMODB_EVALUATIONS_TABLE": "AWS_DYNAMODB_EVALUATIONS_TABLE",
    "DYNAMODB_KNOWLEDGE_BASE_TABLE": "AWS_DYNAMODB_KNOWLEDGE_BASE_TABLE",
    "S3_RESULTS_BUCKET": "AWS_S3_RESULTS_BUCKET",
    "S3_REPORTS_BUCKET": "AWS_S3_REPORTS_BUCKET",
    "EVENTBRIDGE_BUS_NAME": "AWS_EVENTBRIDGE_BUS_NAME",
    "BEDROCK_PERSONA_MODEL": "AWS_BEDROCK_PERSONA_MODEL",
    "BEDROCK_REDTEAM_MODEL": "AWS_BEDROCK_REDTEAM_MODEL",
    "BEDROCK_JUDGE_MODEL": "AWS_BEDROCK_JUDGE_MODEL",
}


def _default_repo_root() -> Path:
    """Resolve the repository root based on this utility module."""
    return Path(__file__).resolve().parents[3]


def bootstrap_live_demo_env(
    env_path: Path | None = None,
    *,
    apply_prefix_map: bool = True,
) -> bool:
    """
    Load the live demo environment file and normalise expected environment keys.

    Args:
        env_path: Optional path to the `.env.live-demo` file. If omitted the
            repository root is assumed.
        apply_prefix_map: When true, mirror legacy variable names (without the
            `AWS_` prefix) into the modern prefixed variants so the settings
            system can discover them. A deprecation warning is emitted.

    Returns:
        True if the environment file was found and loaded, otherwise False.
    """
    root = _default_repo_root()
    path = env_path or (root / _DEFAULT_ENV_FILENAME)

    if not path.exists():
        return False

    load_dotenv(path)

    if apply_prefix_map:
        applied = []
        for legacy_name, prefixed_name in _LEGACY_ENV_MAP.items():
            if legacy_name in os.environ and prefixed_name not in os.environ:
                os.environ[prefixed_name] = os.environ[legacy_name]
                applied.append((legacy_name, prefixed_name))

        if applied:
            legacy_list = ", ".join(old for old, _ in applied)
            print(
                f"⚠ Detected legacy environment variables ({legacy_list}). "
                "Please update .env.live-demo to use AWS_* prefixed names."
            )

    if "ENABLE_XRAY_TRACING" in os.environ and "ENABLE_TRACING" not in os.environ:
        os.environ["ENABLE_TRACING"] = os.environ["ENABLE_XRAY_TRACING"]

    return True


def refresh_settings():
    """
    Re-instantiate the global settings object after environment changes.

    Returns:
        The refreshed `Settings` instance.
    """
    from agenteval import config as config_module  # Local import to avoid cycles

    config_module.settings = config_module.Settings()
    return config_module.settings
