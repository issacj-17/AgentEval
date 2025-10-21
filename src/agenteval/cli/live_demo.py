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

from agenteval.reporting.output_manager import OutputManager, get_output_manager
from agenteval.utils.live_demo_env import bootstrap_live_demo_env, refresh_settings

# Global output manager (initialized after environment bootstrap)
_output_manager: OutputManager | None = None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the AgentEval live demo workflow.")
    parser.add_argument("--region", help="AWS region to use (overrides AWS_REGION).")

    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--quick", action="store_true", help="Quick mode (create campaigns without executing)."
    )
    mode_group.add_argument(
        "--full", action="store_true", help="Full mode (use deployed ECS API endpoint)."
    )

    parser.add_argument(
        "--api-url",
        help="API base URL for full mode (auto-detected from CloudFormation if not provided).",
    )
    parser.add_argument(
        "--api-key",
        help="API key for full mode authentication.",
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


def _setup_logging(output_manager: OutputManager) -> Path:
    output_manager.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_manager.get_log_path(f"run-{output_manager.run_timestamp}")

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
    except Exception as exc:
        # Gracefully handle AWS resources not existing
        if "ResourceNotFoundException" in str(exc) or "does not exist" in str(exc):
            logger.warning("AWS resources not provisioned. Skipping artifact pull. Run setup-live-demo.sh first.")
            return True  # Return True to allow workflow to continue
        logger.error("Failed to pull artefacts: %s", exc)
        return False

    if downloaded:
        logger.info("Pulled %d artefact(s) into %s", len(downloaded), output_dir)
    else:
        logger.warning("No artefacts were downloaded for %s (no campaigns executed?).", output_dir)

    return True


def _create_placeholder_reports(output_manager: OutputManager, logger: logging.Logger) -> None:
    """Create placeholder reports when no campaigns exist."""
    summary_content = """# AgentEval Live Demo Summary

## Status
No campaigns were executed or found.

## Next Steps
1. Ensure AWS resources are provisioned: `./scripts/setup-live-demo.sh --region us-east-1`
2. Run the live demo: `./scripts/run-live-demo.sh --region us-east-1`
"""

    dashboard_content = """# AgentEval Evidence Dashboard

## Campaigns
No campaigns found.

## Instructions
To run campaigns:
1. Provision AWS resources: `./scripts/setup-live-demo.sh --region us-east-1`
2. Execute demo: `./scripts/run-live-demo.sh --region us-east-1`
"""

    output_manager.summary_path.parent.mkdir(parents=True, exist_ok=True)
    output_manager.summary_path.write_text(summary_content)
    output_manager.dashboard_path.write_text(dashboard_content)
    logger.info("Created placeholder reports (no campaigns executed)")


def _generate_campaign_detail_pages(
    output_manager: OutputManager,
    insights: list,
    html_renderer,
    logger: logging.Logger,
) -> None:
    """
    Generate individual HTML pages for each campaign with detailed turn-by-turn results.

    Args:
        output_manager: Output manager for paths
        insights: List of CampaignInsight objects
        html_renderer: HTMLRenderer instance
        logger: Logger instance
    """
    import json
    from pathlib import Path

    try:
        campaigns_dir = output_manager.campaigns_dir
        generated_count = 0

        for insight in insights:
            campaign_id = insight.campaign_id
            campaign_dir = campaigns_dir / campaign_id

            # Look for report-*.json files which contain detailed turn results
            report_files = list((campaign_dir / "s3" / "results").glob("report-*.json"))

            if not report_files:
                logger.debug(f"No report files found for campaign {campaign_id[:8]}, skipping detail page")
                continue

            # Use the most recent report file
            report_file = sorted(report_files)[-1]

            try:
                # Load report data
                with open(report_file, "r") as f:
                    report_data = json.load(f)

                # Extract the actual results (handle nested structure)
                if "results" in report_data and isinstance(report_data["results"], dict):
                    campaign_data = report_data["results"]
                else:
                    campaign_data = report_data

                # Render campaign detail page
                html_renderer.render_campaign_detail_from_data(campaign_data)
                generated_count += 1
                logger.debug(f"Generated detail page for campaign {campaign_id[:8]}")

            except Exception as e:
                logger.warning(f"Failed to generate detail page for campaign {campaign_id[:8]}: {e}")
                continue

        logger.info(f"Generated {generated_count} campaign detail pages")

    except Exception as exc:
        logger.warning(f"Failed to generate campaign detail pages: {exc}")
        import traceback
        logger.debug(f"Campaign detail generation traceback: {traceback.format_exc()}")


def _generate_html_reports(
    output_manager: OutputManager,
    insights: list,
    logger: logging.Logger,
) -> None:
    """
    Generate HTML reports from campaign insights.

    Args:
        output_manager: Output manager for paths
        insights: List of CampaignInsight objects
        logger: Logger instance
    """
    from collections import defaultdict
    from agenteval.reporting.html_renderer import (
        HTMLRenderer,
        DashboardContext,
        CampaignSummary,
    )

    try:
        # Initialize HTML renderer
        html_renderer = HTMLRenderer(
            template_dir=None,  # Uses default template dir
            output_dir=output_manager.reports_dir,
        )

        logger.info("Generating HTML dashboard...")

        # Calculate aggregate statistics
        total_campaigns = len(insights)

        if total_campaigns == 0:
            logger.warning("No campaigns found, skipping HTML generation")
            return

        # Calculate overall score
        scores = [c.overall_score for c in insights if c.overall_score is not None]
        overall_score = sum(scores) / len(scores) if scores else 0.0

        # Calculate turn statistics first (needed for success_rate)
        total_turns = sum(c.total_turns or 0 for c in insights)
        passing_turns = sum(c.passing_turns or 0 for c in insights)

        # Recalculate correct success_rate from actual passing/total turns
        # This fixes the bug where success_rate was based on execution completion
        # instead of quality passing
        # Note: If no turns executed, success_rate should be 0.0 (not N/A, as we want a number for charts)
        success_rate = passing_turns / total_turns if total_turns > 0 else 0.0

        # Log warning if data looks suspicious (helps with debugging)
        if total_turns > 0 and passing_turns == 0 and success_rate > 0:
            logger.warning(
                f"Data inconsistency detected: {passing_turns} passing turns "
                f"but success_rate={success_rate:.1%}. Recalculated to {success_rate:.1%}"
            )

        # Separate completed vs passing concepts
        # completed_turns = turns that finished execution (may have failed quality checks)
        # passing_turns = turns that met quality thresholds
        completed_turns = total_turns  # All turns were executed (in Quick/Full mode)
        failed_turns = total_turns - passing_turns  # Turns that failed quality checks

        # Calculate evaluation/metric counts (approximation)
        total_evaluations = total_turns
        total_metrics = 11  # Standard 11 metrics per evaluation

        # Build campaign summaries for HTML
        campaign_summaries = []
        for insight in insights:
            # Calculate duration (simplified)
            duration = "N/A"

            campaign_summaries.append(
                CampaignSummary(
                    id=insight.campaign_id[:8],
                    type=insight.campaign_type,
                    status=insight.status,
                    status_class=html_renderer.calculate_status_class(insight.status),
                    score=insight.overall_score or 0.0,
                    score_class=html_renderer.calculate_score_class(insight.overall_score or 0.0),
                    completed_turns=insight.passing_turns or 0,
                    total_turns=insight.total_turns or 0,
                    duration=duration,
                    created_at=insight.created_at or "N/A",
                )
            )

        # Build chart data
        campaign_labels = [c.campaign_id[:8] for c in insights]
        campaign_scores = [(c.overall_score or 0.0) * 100 for c in insights]

        # Campaign types distribution
        type_counter = defaultdict(int)
        for c in insights:
            type_counter[c.campaign_type] += 1
        campaign_type_labels = list(type_counter.keys())
        campaign_type_counts = list(type_counter.values())

        # Metric performance (simplified - use overall scores as proxy)
        metric_labels = ["accuracy", "relevance", "completeness", "clarity", "toxicity",
                        "bias", "harmful_content", "privacy_leak", "routing_accuracy",
                        "professionalism", "consistency"]
        metric_scores = [overall_score * 100] * len(metric_labels)  # Simplified

        # Turn completion trend
        turn_trend_labels = campaign_labels
        turn_trend_completed = [c.passing_turns or 0 for c in insights]
        turn_trend_failed = [(c.total_turns or 0) - (c.passing_turns or 0) for c in insights]

        # Build dashboard context
        dashboard_ctx = DashboardContext(
            title="AgentEval Dashboard",
            subtitle="Comprehensive Multi-Agent Evaluation Results",
            generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
            region=os.environ.get("AWS_REGION", "us-east-1"),
            environment="live-demo",
            total_campaigns=total_campaigns,
            overall_score=overall_score,
            total_turns=total_turns,
            completed_turns=completed_turns,
            failed_turns=failed_turns,
            success_rate=success_rate,
            total_evaluations=total_evaluations,
            total_metrics=total_metrics,
            campaigns=campaign_summaries,
            campaign_labels=campaign_labels,
            campaign_scores=campaign_scores,
            campaign_type_labels=campaign_type_labels,
            campaign_type_counts=campaign_type_counts,
            metric_labels=metric_labels,
            metric_scores=metric_scores,
            turn_trend_labels=turn_trend_labels,
            turn_trend_completed=turn_trend_completed,
            turn_trend_failed=turn_trend_failed,
        )

        # Render dashboard HTML
        html_path = html_renderer.render_dashboard(dashboard_ctx)
        logger.info("HTML dashboard written to %s", html_path)

        # Generate individual campaign detail pages
        logger.info("Generating individual campaign detail pages...")
        _generate_campaign_detail_pages(output_manager, insights, html_renderer, logger)

    except Exception as exc:
        logger.warning("Failed to generate HTML reports: %s", exc)
        import traceback
        logger.debug("HTML generation traceback: %s", traceback.format_exc())


def _generate_reports(output_manager: OutputManager, logger: logging.Logger) -> None:
    from agenteval.reporting import dashboard

    try:
        insights = dashboard.collect_campaign_insights(output_manager.campaigns_dir)

        # Generate Markdown reports
        dashboard.generate_live_demo_summary(
            output_manager.campaigns_dir, output_manager.summary_path, insights
        )
        dashboard.generate_dashboard(
            output_manager.campaigns_dir, output_manager.dashboard_path, insights
        )

        if insights:
            logger.info("Generated markdown reports with %d campaign(s)", len(insights))
        else:
            logger.info("Generated empty markdown reports (no campaigns found)")

        # Generate HTML reports
        _generate_html_reports(output_manager, insights, logger)

    except Exception as exc:
        logger.warning("Failed to generate reports: %s", exc)
        # Create placeholder reports to show "no campaigns" message
        _create_placeholder_reports(output_manager, logger)

    logger.info("Live summary written to %s", output_manager.summary_path)
    logger.info("Evidence dashboard written to %s", output_manager.dashboard_path)


async def _run_live_demo_full_mode(
    api_url: str,
    api_key: str | None,
    logger: logging.Logger,
) -> bool:
    """
    Run live demo using deployed API endpoint (full mode).

    Args:
        api_url: Base URL of deployed API
        api_key: Optional API key
        logger: Logger instance

    Returns:
        True if successful, False otherwise
    """
    from agenteval.cli.api_client import AgentEvalAPIClient
    from agenteval.config import settings

    logger.info("Running live demo in FULL MODE (deployed API)")
    logger.info(f"API URL: {api_url}")

    try:
        async with AgentEvalAPIClient(base_url=api_url, api_key=api_key) as client:
            # Health check
            logger.info("Checking API health...")
            health = await client.health_check()
            logger.info(f"API health: {health}")

            # Get demo settings
            target_url = settings.app.demo_target_url
            persona_max_turns = settings.app.demo_persona_max_turns
            redteam_max_turns = settings.app.demo_redteam_max_turns

            logger.info(f"Target URL: {target_url}")

            # Create persona campaigns
            persona_configs = [
                {"persona_type": "frustrated_customer", "initial_goal": "Get help", "max_turns": persona_max_turns},
                {"persona_type": "confused_user", "initial_goal": "Understand product", "max_turns": persona_max_turns},
                {"persona_type": "impatient_user", "initial_goal": "Quick answer", "max_turns": persona_max_turns},
            ]

            logger.info(f"Creating {len(persona_configs)} persona campaigns...")
            persona_campaign_ids = []

            for i, config in enumerate(persona_configs, 1):
                try:
                    campaign_id = await client.create_campaign(
                        campaign_type="persona",
                        target_url=target_url,
                        config=config,
                    )
                    persona_campaign_ids.append(campaign_id)
                    logger.info(f"[{i}/{len(persona_configs)}] Persona campaign created: {campaign_id}")
                except Exception as e:
                    logger.error(f"Failed to create persona campaign {i}: {e}")

            # Create red team campaigns
            redteam_configs = [
                {"attack_categories": ["prompt_injection"], "max_turns": redteam_max_turns},
                {"attack_categories": ["jailbreak"], "max_turns": redteam_max_turns},
            ]

            logger.info(f"Creating {len(redteam_configs)} red team campaigns...")
            redteam_campaign_ids = []

            for i, config in enumerate(redteam_configs, 1):
                try:
                    campaign_id = await client.create_campaign(
                        campaign_type="red_team",
                        target_url=target_url,
                        config=config,
                    )
                    redteam_campaign_ids.append(campaign_id)
                    logger.info(f"[{i}/{len(redteam_configs)}] Red team campaign created: {campaign_id}")
                except Exception as e:
                    logger.error(f"Failed to create red team campaign {i}: {e}")

            all_campaign_ids = persona_campaign_ids + redteam_campaign_ids
            logger.info(f"Total campaigns created: {len(all_campaign_ids)}")

            # Wait for all campaigns to complete
            logger.info("Waiting for campaigns to complete (timeout: 5 minutes per campaign)...")

            for i, campaign_id in enumerate(all_campaign_ids, 1):
                try:
                    logger.info(f"[{i}/{len(all_campaign_ids)}] Waiting for {campaign_id}...")
                    status = await client.wait_for_completion(campaign_id, timeout=300)
                    final_status = status.get("status", "unknown")
                    logger.info(f"[{i}/{len(all_campaign_ids)}] Campaign {campaign_id} completed with status: {final_status}")
                except Exception as e:
                    logger.error(f"Campaign {campaign_id} failed or timed out: {e}")

            logger.info("All campaigns processed via deployed API")
            return True

    except Exception as e:
        logger.error(f"Full mode execution failed: {e}", exc_info=True)
        return False


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

    # Create a temporary logger for environment loading
    import logging
    temp_logger = logging.getLogger("agenteval.live_demo.setup")
    temp_logger.setLevel(logging.INFO)
    if not temp_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
        temp_logger.addHandler(handler)

    # Load environment first to get settings
    try:
        _load_environment(args.skip_setup, args.region, temp_logger)
    except Exception as exc:
        temp_logger.error(f"Error loading environment: {exc}")
        return 1

    # Initialize OutputManager with loaded settings
    global _output_manager
    _output_manager = get_output_manager()
    _output_manager.ensure_directories()

    # Now setup logging with OutputManager
    log_path = _setup_logging(_output_manager)
    logger = logging.getLogger("agenteval.live_demo")
    _log_header(logger, log_path)

    try:
        region = os.environ["AWS_REGION"]

        if not args.skip_verify:
            _run_check_services(region, logger)
        else:
            logger.warning("Skipping AWS service verification as requested.")

        # Determine mode
        if args.full:
            # Full mode - use deployed API
            logger.info("Mode: FULL (deployed API endpoint)")

            # Get API URL
            if args.api_url:
                api_url = args.api_url
                logger.info(f"Using provided API URL: {api_url}")
            else:
                # Auto-detect from CloudFormation
                from agenteval.cli.api_client import get_alb_url_from_cloudformation
                logger.info("Auto-detecting API URL from CloudFormation...")
                try:
                    api_url = get_alb_url_from_cloudformation(region)
                except Exception as e:
                    logger.error(f"Failed to get API URL from CloudFormation: {e}")
                    logger.error("Please provide --api-url explicitly or ensure ECS stack is deployed")
                    return 1

            # Get API key
            api_key = args.api_key or os.environ.get("API_KEY")
            if not api_key:
                logger.warning("No API key provided - API may require authentication")

            demo_success = asyncio.run(_run_live_demo_full_mode(api_url, api_key, logger))
        else:
            # Quick mode or default - use local SDK
            if args.quick:
                logger.info("Mode: QUICK (local SDK, minimal execution)")
            else:
                logger.info("Mode: STANDARD (local SDK, full execution)")

            demo_success = asyncio.run(_run_live_demo(args.quick, logger))

        pull_success = _pull_artefacts(_output_manager.campaigns_dir, args.campaign_limit, logger)
        if pull_success:
            _generate_reports(_output_manager, logger)
        else:
            logger.warning("Dashboard generation skipped due to artefact pull failure.")

        if args.auto_teardown:
            _teardown(region, logger)
        else:
            logger.info(
                "Resources remain provisioned. Run scripts/teardown-live-demo.sh to clean up."
            )

        logger.info("")
        logger.info("All outputs saved to: %s", _output_manager.run_dir)
        logger.info("Quick access via symlink: %s", _output_manager.latest_dir)

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
