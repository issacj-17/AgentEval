"""
Complete live demo workflow orchestrator.

This CLI replaces the legacy bash script and ensures the workflow order:
1. (Optional) Verify AWS environment
2. Execute the live demo (persona + red team campaigns)
3. Pull DynamoDB/S3 artefacts locally
4. Generate summary/dashboard markdown
5. (Optional) Teardown AWS resources
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from agenteval.utils.live_demo_env import bootstrap_live_demo_env, refresh_settings

EVIDENCE_ROOT = REPO_ROOT / "demo" / "evidence"
LOG_DIR = EVIDENCE_ROOT / "live-demo-logs"
SUMMARY_PATH = EVIDENCE_ROOT / "live-demo-latest.md"
DASHBOARD_PATH = EVIDENCE_ROOT / "dashboard.md"
PULLED_ROOT = EVIDENCE_ROOT / "pulled-reports"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AgentEval live demo workflow.")
    parser.add_argument("--region", help="AWS region to use (overrides AWS_REGION).")
    parser.add_argument(
        "--quick", action="store_true", help="Quick mode (create campaigns without executing)."
    )
    parser.add_argument(
        "--auto-teardown",
        action="store_true",
        help="Teardown AWS resources after artefacts are pulled.",
    )
    parser.add_argument(
        "--skip-setup", action="store_true", help="Skip .env.live-demo existence check."
    )
    parser.add_argument(
        "--skip-verify", action="store_true", help="Skip AWS service verification step."
    )
    parser.add_argument(
        "--campaign-limit",
        type=int,
        default=200,
        help="Max campaigns to pull when gathering artefacts.",
    )
    return parser.parse_args(argv)


def _setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    log_path = LOG_DIR / f"run-{timestamp}.log"

    logger = logging.getLogger("agenteval.live_demo")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    return log_path


def _log_header(logger: logging.Logger, log_path: Path) -> None:
    separator = "=" * 48
    logger.info(separator)
    logger.info("AgentEval Live Demo Runner")
    logger.info(separator)
    logger.info("Log file: %s", log_path)


def _load_environment(
    skip_setup: bool, region_override: str | None, logger: logging.Logger
) -> None:
    env_path = REPO_ROOT / ".env.live-demo"
    if not env_path.exists():
        if skip_setup:
            logger.warning(
                ".env.live-demo not found but --skip-setup supplied; continuing with ambient environment."
            )
        else:
            raise RuntimeError(
                ".env.live-demo not found. Run scripts/setup-live-demo.sh first or use --skip-setup."
            )
    else:
        bootstrap_live_demo_env(env_path)
        logger.info("Loaded configuration from %s", env_path)

    if region_override:
        os.environ["AWS_REGION"] = region_override
        logger.info("Using AWS region override: %s", region_override)
    elif "AWS_REGION" not in os.environ:
        os.environ["AWS_REGION"] = "us-east-1"
        logger.info("AWS region defaulting to us-east-1")

    refresh_settings()


def _run_check_services(region: str, logger: logging.Logger) -> None:
    logger.info("Verifying AWS service readiness...")
    result = subprocess.run(
        ["scripts/check-aws-services.sh", "--region", region, "--quiet"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
    )
    if result.returncode != 0:
        raise RuntimeError(
            "AWS service verification failed. Review scripts/check-aws-services.sh output."
        )
    logger.info("AWS services verified.")


async def _run_live_demo(quick_mode: bool, logger: logging.Logger) -> bool:
    # Import after environment bootstrap so the module sees updated settings.
    from demo.agenteval_live_demo import LiveDemoRunner

    logger.info("Starting live demo (quick=%s)...", quick_mode)
    runner = LiveDemoRunner(quick_mode=quick_mode)
    success = await runner.run()
    if success:
        logger.info("Live demo completed successfully.")
    else:
        logger.error("Live demo encountered errors.")
    return success


def _pull_artefacts(
    output_dir: Path,
    campaign_limit: int,
    logger: logging.Logger,
) -> bool:
    from agenteval.reporting import pull

    try:
        downloaded = pull.pull_live_reports(
            output_dir,
            limit=campaign_limit,
        )
    except RuntimeError as exc:
        logger.error("Failed to pull artefacts: %s", exc)
        return False

    if downloaded:
        logger.info("Pulled %d artefact(s) into %s", len(downloaded), output_dir)
    else:
        logger.warning("No artefacts were downloaded for %s (no campaigns?).", output_dir)

    return True


def _generate_reports(run_dir: Path, logger: logging.Logger) -> None:
    from agenteval.reporting import dashboard

    insights = dashboard.collect_campaign_insights(run_dir)
    dashboard.generate_live_demo_summary(run_dir, SUMMARY_PATH, insights)
    dashboard.generate_dashboard(run_dir, DASHBOARD_PATH, insights)
    logger.info("Live summary written to %s", SUMMARY_PATH)
    logger.info("Evidence dashboard written to %s", DASHBOARD_PATH)


def _teardown(region: str, logger: logging.Logger) -> None:
    logger.warning("Auto-teardown enabled. Cleaning up AWS resources...")
    result = subprocess.run(
        ["scripts/teardown-live-demo.sh", "--region", region, "--force"],
        cwd=REPO_ROOT,
        env=os.environ.copy(),
    )
    if result.returncode == 0:
        logger.info("Teardown completed successfully.")
    else:
        logger.error(
            "Teardown script returned non-zero exit code (%s). Manual cleanup may be required.",
            result.returncode,
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    log_path = _setup_logging()
    logger = logging.getLogger("agenteval.live_demo")
    _log_header(logger, log_path)

    try:
        _load_environment(args.skip_setup, args.region, logger)
        region = os.environ["AWS_REGION"]

        if not args.skip_verify:
            _run_check_services(region, logger)
        else:
            logger.warning("Skipping AWS service verification as requested.")

        demo_success = asyncio.run(_run_live_demo(args.quick, logger))

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        run_dir = PULLED_ROOT / timestamp
        run_dir.mkdir(parents=True, exist_ok=True)

        pull_success = _pull_artefacts(run_dir, args.campaign_limit, logger)
        if pull_success:
            _generate_reports(run_dir, logger)
        else:
            logger.warning("Dashboard generation skipped due to artefact pull failure.")

        if args.auto_teardown:
            _teardown(region, logger)
        else:
            logger.info(
                "Resources remain provisioned. Run scripts/teardown-live-demo.sh to clean up."
            )

        if not demo_success:
            logger.error("Live demo reported failures. Inspect logs for details.")
            return 1
        if not pull_success:
            logger.warning("Run completed but artefact pull failed.")
            return 2
        return 0

    except Exception as exc:  # pragma: no cover - defensive catch
        logger.exception("Fatal error during live demo workflow: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
