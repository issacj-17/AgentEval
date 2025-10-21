"""
Utilities for pulling live demo artefacts from AWS into the local workspace.

These helpers are shared between the standalone CLI (`scripts/pull-live-reports.py`)
and the orchestrated live-demo workflow (`agenteval.cli.live_demo`).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

from agenteval.utils.live_demo_env import bootstrap_live_demo_env, refresh_settings

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_AVAILABLE = bootstrap_live_demo_env(REPO_ROOT / ".env.live-demo")
refresh_settings()

from agenteval.container import Container, reset_container


def _ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))


async def pull_campaign_data(
    container: Container,
    output_dir: Path,
    campaign_id: str | None,
    limit: int,
) -> list[Path]:
    """Download artefacts for matching campaigns into the specified directory."""
    dynamodb = container.dynamodb()
    s3_client = container.s3()
    await dynamodb.connect()
    await s3_client.connect()
    downloaded_files: list[Path] = []

    try:
        if campaign_id:
            campaign = await dynamodb.get_campaign(campaign_id)
            campaigns = [campaign] if campaign else []
        else:
            campaigns = await dynamodb.list_campaigns(limit=limit, offset=0)
    except Exception as e:
        # Handle case where AWS resources don't exist yet
        if "ResourceNotFoundException" in str(e) or "does not exist" in str(e):
            # Resources not provisioned yet - return empty list gracefully
            return downloaded_files
        # Re-raise other exceptions
        raise

    if not campaigns:
        return downloaded_files

    for campaign in campaigns:
        if not campaign:
            continue

        cid = campaign.get("campaign_id")
        if not cid:
            continue

        campaign_dir = output_dir / cid
        dynamo_dir = _ensure_directory(campaign_dir / "dynamodb")
        results_dir = _ensure_directory(campaign_dir / "s3" / "results")
        reports_dir = _ensure_directory(campaign_dir / "s3" / "reports")

        _write_json(dynamo_dir / "campaign.json", campaign)

        turns = await dynamodb.get_turns(cid)
        _write_json(dynamo_dir / "turns.json", turns)

        evaluations = await dynamodb.get_evaluations(cid)
        _write_json(dynamo_dir / "evaluations.json", evaluations)

        # Download results payloads
        result_objects = await s3_client.list_objects(
            bucket=s3_client.results_bucket,
            prefix=f"campaigns/{cid}/",
        )
        for obj in result_objects:
            key = obj["key"]
            try:
                relative = Path(key).relative_to(Path("campaigns") / cid)
            except ValueError:
                relative = Path(key).name
            destination = results_dir / relative
            downloaded = await s3_client.download_object(
                bucket=s3_client.results_bucket,
                key=key,
                destination=destination,
            )
            downloaded_files.append(downloaded)

        # Download rendered reports
        report_objects = await s3_client.list_objects(
            bucket=s3_client.reports_bucket,
            prefix=f"reports/{cid}/",
        )
        for obj in report_objects:
            key = obj["key"]
            try:
                relative = Path(key).relative_to(Path("reports") / cid)
            except ValueError:
                relative = Path(key).name
            destination = reports_dir / relative
            downloaded = await s3_client.download_object(
                bucket=s3_client.reports_bucket,
                key=key,
                destination=destination,
            )
            downloaded_files.append(downloaded)

    return downloaded_files


async def pull_live_reports_async(
    output_dir: Path,
    *,
    campaign_id: str | None = None,
    limit: int = 200,
) -> list[Path]:
    """Async helper that orchestrates container lifecycle while pulling artefacts."""
    if not ENV_AVAILABLE:
        raise RuntimeError(".env.live-demo not found. Run setup before pulling reports.")

    output_dir = Path(output_dir).resolve()
    _ensure_directory(output_dir)

    reset_container()
    container = Container()
    await container.connect()

    try:
        downloaded = await pull_campaign_data(
            container=container,
            output_dir=output_dir,
            campaign_id=campaign_id,
            limit=limit,
        )
    finally:
        await container.close()

    return downloaded


def pull_live_reports(
    output_dir: Path,
    *,
    campaign_id: str | None = None,
    limit: int = 200,
) -> list[Path]:
    """Synchronous wrapper for pulling live demo artefacts."""
    return asyncio.run(
        pull_live_reports_async(
            output_dir=output_dir,
            campaign_id=campaign_id,
            limit=limit,
        )
    )


# CLI helpers -----------------------------------------------------------------


def parse_args(argv: Sequence[str]):
    import argparse

    from agenteval.config import settings

    parser = argparse.ArgumentParser(description="Download live demo artefacts for offline review.")
    parser.add_argument(
        "--campaign-id",
        help="Specific campaign ID to pull. Defaults to all available campaigns.",
    )
    parser.add_argument(
        "--output",
        help="Destination directory for downloaded artefacts. If not specified, uses OutputManager to determine path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Maximum number of campaigns to scan when pulling all results.",
    )
    return parser.parse_args(argv)


def cli(argv: Sequence[str] | None = None) -> int:
    from agenteval.reporting.output_manager import get_output_manager

    args = parse_args(argv or [])

    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        # Use OutputManager to get campaigns directory
        output_manager = get_output_manager()
        output_manager.ensure_directories()
        output_dir = output_manager.campaigns_dir
        print(f"Using OutputManager campaigns directory: {output_dir}")

    try:
        downloaded = pull_live_reports(
            output_dir,
            campaign_id=args.campaign_id,
            limit=args.limit,
        )
    except KeyboardInterrupt:
        print("\n⚠ Pull cancelled by user.")
        return 130
    except RuntimeError as exc:
        print(f"✗ {exc}")
        return 1

    if downloaded:
        print(f"✓ Pulled {len(downloaded)} S3 artefact(s) into {output_dir}")
    else:
        print("⚠ No campaigns or artefacts found for the specified criteria.")

    return 0
