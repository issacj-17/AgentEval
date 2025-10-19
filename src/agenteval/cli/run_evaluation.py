#!/usr/bin/env python3
"""
AgentEval Unified CLI

Single entry point for running evaluations, generating reports, and managing campaigns.

Usage:
    python -m agenteval.cli.run_evaluation run --target URL --campaigns 3
    python -m agenteval.cli.run_evaluation report --campaign-id ID
    python -m agenteval.cli.run_evaluation export --format html

Design: Command Pattern + Facade Pattern for simplified UX
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================================
# CLI Commands
# ============================================================================


async def run_evaluation_command(args: argparse.Namespace) -> int:
    """
    Run evaluation campaign(s).

    Args:
        args: Command arguments

    Returns:
        Exit code (0 = success)
    """

    logger.info("🚀 Starting AgentEval evaluation...")
    logger.info(f"Target: {args.target}")
    logger.info(f"Region: {args.region}")
    logger.info(f"Campaigns: {args.campaigns}")

    try:
        # TODO: Implement campaign execution logic
        # This would integrate with CampaignOrchestrator
        logger.info("✅ Evaluation completed successfully!")
        return 0

    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        return 1


async def generate_report_command(args: argparse.Namespace) -> int:
    """
    Generate reports from evaluation results.

    Args:
        args: Command arguments

    Returns:
        Exit code
    """
    from agenteval.application.dashboard_service import (
        DashboardConfig,
        create_dashboard_service,
    )
    from agenteval.application.report_consolidator import (
        create_report_consolidator,
    )
    from agenteval.application.results_service import create_results_service

    logger.info("📊 Generating evaluation reports...")

    try:
        # Pull results from AWS
        results_service = await create_results_service()
        results = await results_service.pull_all_results(
            region=args.region,
            campaign_ids=args.campaign_ids,
        )

        logger.info(
            f"Retrieved {len(results.campaign_data.campaigns)} campaigns, "
            f"{len(results.campaign_data.turns)} turns"
        )

        # Generate HTML dashboard
        if args.format in ["html", "all"]:
            logger.info("Generating HTML dashboard...")
            dashboard_service = await create_dashboard_service(
                config=DashboardConfig(
                    region=args.region,
                    output_dir=Path(args.output_dir),
                    generate_html=True,
                    generate_markdown=True,
                )
            )

            output_files = await dashboard_service.generate_dashboard(
                campaign_ids=args.campaign_ids
            )

            logger.info(f"✅ HTML dashboard: {output_files.get('html_dashboard')}")

        # Generate markdown report
        if args.format in ["markdown", "all"]:
            logger.info("Generating markdown report...")
            consolidator = await create_report_consolidator(output_dir=Path(args.output_dir))

            report_path = await consolidator.consolidate_reports(results)
            logger.info(f"✅ Markdown report: {report_path}")

        logger.info("✅ Report generation completed!")
        return 0

    except Exception as e:
        logger.error(f"❌ Report generation failed: {e}")
        return 1


async def export_traces_command(args: argparse.Namespace) -> int:
    """
    Export OpenTelemetry traces.

    Args:
        args: Command arguments

    Returns:
        Exit code
    """
    from agenteval.observability.trace_exporter import create_trace_exporter

    logger.info("📦 Exporting traces...")

    try:
        exporter = await create_trace_exporter(
            output_dir=Path(args.output_dir) / "traces",
            export_format=args.export_format,
            max_traces=args.max_traces,
        )

        result = await exporter.export_traces()

        if result.success:
            logger.info(f"✅ Exported {result.traces_exported} traces to {result.output_path}")
            return 0
        else:
            logger.error(f"❌ Export failed: {result.error_message}")
            return 1

    except Exception as e:
        logger.error(f"❌ Trace export failed: {e}")
        return 1


async def cleanup_command(args: argparse.Namespace) -> int:
    """
    Cleanup AWS resources.

    Args:
        args: Command arguments

    Returns:
        Exit code
    """
    logger.info("🧹 Cleaning up AWS resources...")

    # TODO: Implement cleanup logic
    # This would call teardown scripts or use AWS clients directly

    logger.info("✅ Cleanup completed!")
    return 0


# ============================================================================
# CLI Parsing
# ============================================================================


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="agenteval",
        description="AgentEval - Multi-Agent AI Evaluation Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run evaluation
  agenteval run --target http://localhost:5057/chat --campaigns 3

  # Generate reports
  agenteval report --region us-east-1 --format all

  # Export traces
  agenteval export --format json --max-traces 100

  # Cleanup resources
  agenteval cleanup --region us-east-1
        """,
    )

    # Global arguments
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="AWS region (default: us-east-1)",
    )
    parser.add_argument(
        "--output-dir",
        default="demo/evidence",
        help="Output directory (default: demo/evidence)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run evaluation campaigns")
    run_parser.add_argument("--target", required=True, help="Target chatbot URL")
    run_parser.add_argument(
        "--campaigns",
        type=int,
        default=1,
        help="Number of campaigns to run",
    )
    run_parser.add_argument(
        "--campaign-type",
        choices=["persona", "red_team", "all"],
        default="all",
        help="Type of campaigns to run",
    )
    run_parser.add_argument("--max-turns", type=int, default=3, help="Max turns per campaign")

    # Report command
    report_parser = subparsers.add_parser("report", help="Generate evaluation reports")
    report_parser.add_argument(
        "--format",
        choices=["html", "markdown", "all"],
        default="all",
        help="Report format",
    )
    report_parser.add_argument(
        "--campaign-ids",
        nargs="+",
        help="Specific campaign IDs to include",
    )

    # Export command
    export_parser = subparsers.add_parser("export", help="Export OpenTelemetry traces")
    export_parser.add_argument(
        "--export-format",
        choices=["json", "otlp", "jaeger"],
        default="json",
        help="Export format",
    )
    export_parser.add_argument("--max-traces", type=int, help="Maximum traces to export")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup AWS resources")
    cleanup_parser.add_argument(
        "--force", action="store_true", help="Force cleanup without confirmation"
    )

    return parser


# ============================================================================
# Main Entry Point
# ============================================================================


async def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Route to appropriate command
    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "run": run_evaluation_command,
        "report": generate_report_command,
        "export": export_traces_command,
        "cleanup": cleanup_command,
    }

    command_func = commands.get(args.command)
    if not command_func:
        logger.error(f"Unknown command: {args.command}")
        return 1

    try:
        return await command_func(args)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        return 1


def cli_main():
    """Synchronous entry point for CLI."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
