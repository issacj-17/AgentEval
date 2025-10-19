"""
Unit tests for AgentEval CLI.

Tests the unified CLI entry point with all commands.
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agenteval.application.results_service import (
    CampaignData,
    ResultsBundle,
    S3Reports,
    XRayTraces,
)
from agenteval.cli.run_evaluation import (
    cleanup_command,
    cli_main,
    create_parser,
    export_traces_command,
    generate_report_command,
    main,
    run_evaluation_command,
)
from agenteval.observability.trace_exporter import ExportResult


@pytest.fixture
def sample_results_bundle():
    """Sample results bundle for testing."""
    campaigns = [
        {
            "campaign_id": "campaign-1",
            "campaign_type": "persona",
            "status": "completed",
            "created_at": "2025-01-01T00:00:00Z",
        },
    ]

    turns = [
        {
            "campaign_id": "campaign-1",
            "turn_number": 1,
            "status": "completed",
        },
    ]

    evaluations = [
        {
            "campaign_id": "campaign-1",
            "turn_number": 1,
            "score": 0.85,
        },
    ]

    campaign_data = CampaignData(
        campaigns=campaigns,
        turns=turns,
        evaluations=evaluations,
    )

    return ResultsBundle(
        campaign_data=campaign_data,
        s3_reports=S3Reports(campaign_reports={}, demo_reports={}),
        xray_traces=XRayTraces(trace_summaries=[], trace_details=[]),
        region="us-east-1",
    )


class TestRunEvaluationCommand:
    """Test suite for run evaluation command."""

    @pytest.mark.asyncio
    async def test_run_evaluation_success(self):
        """Test successful evaluation run."""
        args = argparse.Namespace(
            target="http://localhost:5057/chat",
            region="us-east-1",
            campaigns=3,
            campaign_type="all",
            max_turns=3,
        )

        # Execute
        exit_code = await run_evaluation_command(args)

        # Verify
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_run_evaluation_success_multiple_campaigns(self):
        """Test evaluation run with multiple campaigns."""
        args = argparse.Namespace(
            target="http://localhost:5057/chat",
            region="us-west-2",
            campaigns=10,
            campaign_type="persona",
            max_turns=5,
        )

        # Execute
        exit_code = await run_evaluation_command(args)

        # Verify - should succeed even with different parameters
        assert exit_code == 0


class TestGenerateReportCommand:
    """Test suite for report generation command."""

    @pytest.mark.asyncio
    async def test_generate_report_html(self, sample_results_bundle, tmp_path):
        """Test HTML report generation."""
        args = argparse.Namespace(
            region="us-east-1",
            format="html",
            output_dir=str(tmp_path),
            campaign_ids=None,
        )

        # Mock services
        mock_results_service = MagicMock()
        mock_results_service.pull_all_results = AsyncMock(return_value=sample_results_bundle)

        mock_dashboard_service = MagicMock()
        mock_dashboard_service.generate_dashboard = AsyncMock(
            return_value={
                "html_dashboard": tmp_path / "dashboard.html",
                "html_summary": tmp_path / "summary.html",
            }
        )

        with patch(
            "agenteval.application.results_service.create_results_service",
            return_value=mock_results_service,
        ), patch(
            "agenteval.application.dashboard_service.create_dashboard_service",
            return_value=mock_dashboard_service,
        ):
            # Execute
            exit_code = await generate_report_command(args)

            # Verify
            assert exit_code == 0
            mock_results_service.pull_all_results.assert_called_once()
            mock_dashboard_service.generate_dashboard.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_report_markdown(self, sample_results_bundle, tmp_path):
        """Test markdown report generation."""
        args = argparse.Namespace(
            region="us-east-1",
            format="markdown",
            output_dir=str(tmp_path),
            campaign_ids=None,
        )

        # Mock services
        mock_results_service = MagicMock()
        mock_results_service.pull_all_results = AsyncMock(return_value=sample_results_bundle)

        mock_consolidator = MagicMock()
        mock_consolidator.consolidate_reports = AsyncMock(return_value=tmp_path / "REPORT.md")

        with patch(
            "agenteval.application.results_service.create_results_service",
            return_value=mock_results_service,
        ), patch(
            "agenteval.application.report_consolidator.create_report_consolidator",
            return_value=mock_consolidator,
        ):
            # Execute
            exit_code = await generate_report_command(args)

            # Verify
            assert exit_code == 0
            mock_results_service.pull_all_results.assert_called_once()
            mock_consolidator.consolidate_reports.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_report_all_formats(self, sample_results_bundle, tmp_path):
        """Test report generation with all formats."""
        args = argparse.Namespace(
            region="us-east-1",
            format="all",
            output_dir=str(tmp_path),
            campaign_ids=["campaign-1"],
        )

        # Mock services
        mock_results_service = MagicMock()
        mock_results_service.pull_all_results = AsyncMock(return_value=sample_results_bundle)

        mock_dashboard_service = MagicMock()
        mock_dashboard_service.generate_dashboard = AsyncMock(
            return_value={"html_dashboard": tmp_path / "dashboard.html"}
        )

        mock_consolidator = MagicMock()
        mock_consolidator.consolidate_reports = AsyncMock(return_value=tmp_path / "REPORT.md")

        with patch(
            "agenteval.application.results_service.create_results_service",
            return_value=mock_results_service,
        ), patch(
            "agenteval.application.dashboard_service.create_dashboard_service",
            return_value=mock_dashboard_service,
        ), patch(
            "agenteval.application.report_consolidator.create_report_consolidator",
            return_value=mock_consolidator,
        ):
            # Execute
            exit_code = await generate_report_command(args)

            # Verify
            assert exit_code == 0
            mock_dashboard_service.generate_dashboard.assert_called_once()
            mock_consolidator.consolidate_reports.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_report_failure(self):
        """Test report generation failure."""
        args = argparse.Namespace(
            region="us-east-1",
            format="html",
            output_dir="demo/evidence",
            campaign_ids=None,
        )

        # Mock service to raise exception
        with patch(
            "agenteval.application.results_service.create_results_service",
            side_effect=Exception("Service creation failed"),
        ):
            # Execute
            exit_code = await generate_report_command(args)

            # Verify
            assert exit_code == 1


class TestExportTracesCommand:
    """Test suite for trace export command."""

    @pytest.mark.asyncio
    async def test_export_traces_success(self, tmp_path):
        """Test successful trace export."""
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            export_format="json",
            max_traces=100,
        )

        # Mock exporter
        mock_exporter = MagicMock()
        mock_exporter.export_traces = AsyncMock(
            return_value=ExportResult(
                success=True,
                output_path=tmp_path / "traces.json",
                traces_exported=10,
                error_message=None,
            )
        )

        with patch(
            "agenteval.observability.trace_exporter.create_trace_exporter",
            return_value=mock_exporter,
        ):
            # Execute
            exit_code = await export_traces_command(args)

            # Verify
            assert exit_code == 0
            mock_exporter.export_traces.assert_called_once()

    @pytest.mark.asyncio
    async def test_export_traces_failure(self, tmp_path):
        """Test trace export failure."""
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            export_format="otlp",
            max_traces=None,
        )

        # Mock exporter to return failure
        mock_exporter = MagicMock()
        mock_exporter.export_traces = AsyncMock(
            return_value=ExportResult(
                success=False,
                output_path=None,
                traces_exported=0,
                error_message="Export failed",
            )
        )

        with patch(
            "agenteval.observability.trace_exporter.create_trace_exporter",
            return_value=mock_exporter,
        ):
            # Execute
            exit_code = await export_traces_command(args)

            # Verify
            assert exit_code == 1

    @pytest.mark.asyncio
    async def test_export_traces_exception(self, tmp_path):
        """Test trace export with exception."""
        args = argparse.Namespace(
            output_dir=str(tmp_path),
            export_format="jaeger",
            max_traces=50,
        )

        # Mock to raise exception
        with patch(
            "agenteval.observability.trace_exporter.create_trace_exporter",
            side_effect=Exception("Exporter creation failed"),
        ):
            # Execute
            exit_code = await export_traces_command(args)

            # Verify
            assert exit_code == 1


class TestCleanupCommand:
    """Test suite for cleanup command."""

    @pytest.mark.asyncio
    async def test_cleanup_success(self):
        """Test successful cleanup."""
        args = argparse.Namespace(
            region="us-east-1",
            force=False,
        )

        # Execute
        exit_code = await cleanup_command(args)

        # Verify
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_cleanup_with_force(self):
        """Test cleanup with force flag."""
        args = argparse.Namespace(
            region="us-east-1",
            force=True,
        )

        # Execute
        exit_code = await cleanup_command(args)

        # Verify
        assert exit_code == 0


class TestCreateParser:
    """Test suite for argument parser creation."""

    def test_create_parser(self):
        """Test parser creation."""
        parser = create_parser()

        # Verify parser was created
        assert parser is not None
        assert parser.prog == "agenteval"

    def test_parse_run_command(self):
        """Test parsing run command."""
        parser = create_parser()

        # Note: Required argument --target must be provided
        args = parser.parse_args(
            [
                "--region",
                "us-west-2",
                "run",
                "--target",
                "http://localhost:5057/chat",
                "--campaigns",
                "5",
            ]
        )

        # Verify
        assert args.command == "run"
        assert args.target == "http://localhost:5057/chat"
        assert args.campaigns == 5
        assert args.region == "us-west-2"

    def test_parse_report_command(self):
        """Test parsing report command."""
        parser = create_parser()

        args = parser.parse_args(["report", "--format", "html", "--campaign-ids", "c1", "c2"])

        # Verify
        assert args.command == "report"
        assert args.format == "html"
        assert args.campaign_ids == ["c1", "c2"]

    def test_parse_export_command(self):
        """Test parsing export command."""
        parser = create_parser()

        args = parser.parse_args(["export", "--export-format", "otlp", "--max-traces", "200"])

        # Verify
        assert args.command == "export"
        assert args.export_format == "otlp"
        assert args.max_traces == 200

    def test_parse_cleanup_command(self):
        """Test parsing cleanup command."""
        parser = create_parser()

        args = parser.parse_args(["cleanup", "--force"])

        # Verify
        assert args.command == "cleanup"
        assert args.force is True

    def test_parse_global_args(self):
        """Test parsing global arguments."""
        parser = create_parser()

        # Global args before subcommand
        args = parser.parse_args(["--verbose", "--output-dir", "/tmp", "run", "--target", "url"])

        # Verify
        assert args.verbose is True
        assert args.output_dir == "/tmp"
        assert args.command == "run"
        assert args.target == "url"


class TestMainEntryPoint:
    """Test suite for main entry point."""

    @pytest.mark.asyncio
    async def test_main_no_command(self):
        """Test main with no command."""
        with patch("sys.argv", ["agenteval"]):
            with patch("agenteval.cli.run_evaluation.create_parser") as mock_parser_factory:
                mock_parser = MagicMock()
                mock_parser.parse_args.return_value = argparse.Namespace(
                    command=None, verbose=False
                )
                mock_parser_factory.return_value = mock_parser

                # Execute
                exit_code = await main()

                # Verify
                assert exit_code == 1
                mock_parser.print_help.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_run_command(self):
        """Test main with run command."""
        with patch("sys.argv", ["agenteval", "run", "--target", "url"]):
            with patch("agenteval.cli.run_evaluation.create_parser") as mock_parser_factory:
                mock_parser = MagicMock()
                mock_parser.parse_args.return_value = argparse.Namespace(
                    command="run",
                    target="url",
                    region="us-east-1",
                    campaigns=1,
                    verbose=False,
                )
                mock_parser_factory.return_value = mock_parser

                with patch(
                    "agenteval.cli.run_evaluation.run_evaluation_command",
                    return_value=0,
                ) as mock_command:
                    # Execute
                    exit_code = await main()

                    # Verify
                    assert exit_code == 0
                    mock_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_with_verbose(self):
        """Test main with verbose logging."""
        with patch("sys.argv", ["agenteval", "cleanup", "--verbose"]):
            with patch("agenteval.cli.run_evaluation.create_parser") as mock_parser_factory:
                mock_parser = MagicMock()
                mock_parser.parse_args.return_value = argparse.Namespace(
                    command="cleanup", region="us-east-1", verbose=True
                )
                mock_parser_factory.return_value = mock_parser

                with patch("logging.getLogger") as mock_get_logger:
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger

                    with patch(
                        "agenteval.cli.run_evaluation.cleanup_command",
                        return_value=0,
                    ):
                        # Execute
                        await main()

                        # Verify verbose logging was enabled
                        mock_logger.setLevel.assert_called()

    @pytest.mark.asyncio
    async def test_main_keyboard_interrupt(self):
        """Test main with keyboard interrupt."""
        with patch("sys.argv", ["agenteval", "run", "--target", "url"]):
            with patch("agenteval.cli.run_evaluation.create_parser") as mock_parser_factory:
                mock_parser = MagicMock()
                mock_parser.parse_args.return_value = argparse.Namespace(
                    command="run",
                    target="url",
                    region="us-east-1",
                    campaigns=1,
                    verbose=False,
                )
                mock_parser_factory.return_value = mock_parser

                with patch(
                    "agenteval.cli.run_evaluation.run_evaluation_command",
                    side_effect=KeyboardInterrupt(),
                ):
                    # Execute
                    exit_code = await main()

                    # Verify
                    assert exit_code == 130  # Standard exit code for SIGINT

    @pytest.mark.asyncio
    async def test_main_unexpected_exception(self):
        """Test main with unexpected exception."""
        with patch("sys.argv", ["agenteval", "run", "--target", "url"]):
            with patch("agenteval.cli.run_evaluation.create_parser") as mock_parser_factory:
                mock_parser = MagicMock()
                mock_parser.parse_args.return_value = argparse.Namespace(
                    command="run",
                    target="url",
                    region="us-east-1",
                    campaigns=1,
                    verbose=False,
                )
                mock_parser_factory.return_value = mock_parser

                with patch(
                    "agenteval.cli.run_evaluation.run_evaluation_command",
                    side_effect=Exception("Unexpected error"),
                ):
                    # Execute
                    exit_code = await main()

                    # Verify
                    assert exit_code == 1

    def test_cli_main(self):
        """Test synchronous CLI entry point."""
        with patch("asyncio.run", return_value=0) as mock_asyncio_run:
            with patch("sys.exit") as mock_exit:
                # Execute
                cli_main()

                # Verify
                mock_asyncio_run.assert_called_once()
                mock_exit.assert_called_once_with(0)
