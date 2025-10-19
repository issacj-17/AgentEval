"""
Results Service - AWS Results Retrieval and Management

Handles pulling evaluation results from AWS services including:
- Campaign data from DynamoDB
- Turns and evaluations from DynamoDB
- Report files from S3
- X-Ray traces

This service follows SOLID principles:
- Single Responsibility: Only handles AWS result retrieval
- Open/Closed: Extensible via strategy pattern for different sources
- Liskov Substitution: Implements ResultsProvider protocol
- Interface Segregation: Focused public API
- Dependency Inversion: Depends on AWS client abstractions
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from agenteval.aws.dynamodb import DynamoDBClient
from agenteval.aws.s3 import S3Client
from agenteval.aws.xray import XRayClient
from agenteval.config import settings

logger = logging.getLogger(__name__)


# Protocol for extensibility (Interface Segregation Principle)
class ResultsProvider(Protocol):
    """Protocol defining interface for results providers."""

    async def pull_campaign_data(self, region: str) -> dict[str, Any]:
        """Pull campaign data."""
        ...


@dataclass
class CampaignData:
    """Structured campaign data from DynamoDB."""

    campaigns: list[dict[str, Any]] = field(default_factory=list)
    turns: list[dict[str, Any]] = field(default_factory=list)
    evaluations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def campaign_ids(self) -> list[str]:
        """Extract campaign IDs."""
        return [c.get("campaign_id", {}).get("S", "") for c in self.campaigns if "campaign_id" in c]


@dataclass
class S3Reports:
    """Structured S3 report data."""

    campaign_reports: dict[str, list[Path]] = field(default_factory=dict)
    demo_reports: dict[str, list[Path]] = field(default_factory=dict)

    @property
    def total_reports(self) -> int:
        """Count total reports."""
        campaign_count = sum(len(reports) for reports in self.campaign_reports.values())
        demo_count = sum(len(reports) for reports in self.demo_reports.values())
        return campaign_count + demo_count


@dataclass
class XRayTraces:
    """Structured X-Ray trace data."""

    trace_summaries: list[dict[str, Any]] = field(default_factory=list)
    trace_details: list[dict[str, Any]] = field(default_factory=list)

    @property
    def trace_ids(self) -> list[str]:
        """Extract trace IDs."""
        return [trace.get("Id", "") for trace in self.trace_summaries if "Id" in trace]


@dataclass
class ResultsBundle:
    """Complete results bundle from all sources."""

    campaign_data: CampaignData
    s3_reports: S3Reports
    xray_traces: XRayTraces
    pulled_at: datetime = field(default_factory=datetime.utcnow)
    region: str = "us-east-1"

    @property
    def summary_stats(self) -> dict[str, int]:
        """Generate summary statistics."""
        return {
            "campaigns": len(self.campaign_data.campaigns),
            "turns": len(self.campaign_data.turns),
            "evaluations": len(self.campaign_data.evaluations),
            "reports": self.s3_reports.total_reports,
            "traces": len(self.xray_traces.trace_summaries),
        }


class ResultsServiceError(Exception):
    """Base exception for results service errors."""

    pass


class ResultsNotFoundError(ResultsServiceError):
    """Raised when expected results are not found."""

    pass


class ResultsPullError(ResultsServiceError):
    """Raised when pulling results fails."""

    pass


class ResultsService:
    """
    Service for pulling and managing evaluation results from AWS.

    This service follows the Repository Pattern for data access and
    uses dependency injection for AWS clients (Dependency Inversion Principle).

    Example usage::

        async with DynamoDBClient() as dynamodb:
            async with S3Client() as s3:
                async with XRayClient() as xray:
                    service = ResultsService(
                        dynamodb=dynamodb,
                        s3=s3,
                        xray=xray
                    )
                    results = await service.pull_all_results(region="us-east-1")
                    print(f"Pulled {results.summary_stats}")
    """

    def __init__(
        self,
        dynamodb: DynamoDBClient,
        s3: S3Client,
        xray: XRayClient,
        output_dir: Path | None = None,
    ):
        """
        Initialize results service.

        Args:
            dynamodb: DynamoDB client for campaign data
            s3: S3 client for reports
            xray: X-Ray client for traces
            output_dir: Base directory for saving results (default: demo/evidence)
        """
        self.dynamodb = dynamodb
        self.s3 = s3
        self.xray = xray
        self.output_dir = output_dir or Path("demo/evidence")

        # Ensure output directories exist
        self.campaign_data_dir = self.output_dir / "campaign-data"
        self.pulled_reports_dir = self.output_dir / "pulled-reports"
        self.trace_reports_dir = self.output_dir / "trace-reports"

        for directory in [self.campaign_data_dir, self.pulled_reports_dir, self.trace_reports_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    async def pull_all_results(
        self,
        region: str = "us-east-1",
        campaign_ids: list[str] | None = None,
    ) -> ResultsBundle:
        """
        Pull all results from AWS services.

        This method orchestrates pulling from multiple sources concurrently
        for optimal performance (Algorithm: Parallel I/O).

        Args:
            region: AWS region
            campaign_ids: Optional list of specific campaign IDs to pull
                         If None, pulls all campaigns

        Returns:
            Complete results bundle

        Raises:
            ResultsPullError: If critical pull operations fail
        """
        logger.info(f"Pulling all results from region: {region}")

        try:
            # Pull from all sources concurrently for performance
            # (Algorithmic Efficiency: Parallel I/O reduces latency)
            campaign_data_task = asyncio.create_task(self.pull_campaign_data(region, campaign_ids))
            s3_reports_task = asyncio.create_task(self.pull_s3_reports(region, campaign_ids))
            xray_traces_task = asyncio.create_task(self.pull_xray_traces(region))

            # Wait for all pulls to complete
            campaign_data, s3_reports, xray_traces = await asyncio.gather(
                campaign_data_task,
                s3_reports_task,
                xray_traces_task,
                return_exceptions=False,
            )

            results = ResultsBundle(
                campaign_data=campaign_data,
                s3_reports=s3_reports,
                xray_traces=xray_traces,
                region=region,
            )

            logger.info(f"Successfully pulled results: {results.summary_stats}")
            return results

        except Exception as e:
            logger.error(f"Failed to pull results: {e}", exc_info=True)
            raise ResultsPullError(f"Failed to pull results from AWS: {e}") from e

    async def pull_campaign_data(
        self,
        region: str,
        campaign_ids: list[str] | None = None,
    ) -> CampaignData:
        """
        Pull campaign data from DynamoDB tables.

        Args:
            region: AWS region
            campaign_ids: Optional filter for specific campaigns

        Returns:
            Structured campaign data
        """
        logger.info("Pulling campaign data from DynamoDB...")

        try:
            # Pull from three tables concurrently
            campaigns_task = asyncio.create_task(self._scan_table("agenteval-campaigns", region))
            turns_task = asyncio.create_task(self._scan_table("agenteval-turns", region))
            evaluations_task = asyncio.create_task(
                self._scan_table("agenteval-evaluations", region)
            )

            campaigns, turns, evaluations = await asyncio.gather(
                campaigns_task,
                turns_task,
                evaluations_task,
                return_exceptions=True,  # Don't fail if one table is missing
            )

            # Handle missing tables gracefully
            campaigns = campaigns if not isinstance(campaigns, Exception) else []
            turns = turns if not isinstance(turns, Exception) else []
            evaluations = evaluations if not isinstance(evaluations, Exception) else []

            # Filter by campaign_ids if specified
            if campaign_ids:
                campaign_id_set = set(campaign_ids)
                campaigns = [
                    c for c in campaigns if c.get("campaign_id", {}).get("S", "") in campaign_id_set
                ]
                turns = [
                    t for t in turns if t.get("campaign_id", {}).get("S", "") in campaign_id_set
                ]
                evaluations = [
                    e
                    for e in evaluations
                    if e.get("campaign_id", {}).get("S", "") in campaign_id_set
                ]

            campaign_data = CampaignData(
                campaigns=campaigns,
                turns=turns,
                evaluations=evaluations,
            )

            # Save to disk
            await self._save_campaign_data(campaign_data)

            logger.info(
                f"Pulled campaign data: {len(campaigns)} campaigns, "
                f"{len(turns)} turns, {len(evaluations)} evaluations"
            )

            return campaign_data

        except Exception as e:
            logger.error(f"Failed to pull campaign data: {e}", exc_info=True)
            raise

    async def _scan_table(self, table_name: str, region: str) -> list[dict[str, Any]]:
        """Scan DynamoDB table and return all items."""
        try:
            # Use the new scan_table method from DynamoDB client
            items = await self.dynamodb.scan_table(table_name)
            return items
        except Exception as e:
            logger.warning(f"Could not scan table {table_name}: {e}")
            return []

    async def _save_campaign_data(self, data: CampaignData) -> None:
        """Save campaign data to JSON files."""
        campaigns_file = self.campaign_data_dir / "campaigns.json"
        turns_file = self.campaign_data_dir / "turns.json"
        evaluations_file = self.campaign_data_dir / "evaluations.json"

        # Save each dataset
        await asyncio.gather(
            self._write_json(campaigns_file, {"Items": data.campaigns}),
            self._write_json(turns_file, {"Items": data.turns}),
            self._write_json(evaluations_file, {"Items": data.evaluations}),
        )

    async def pull_s3_reports(
        self,
        region: str,
        campaign_ids: list[str] | None = None,
    ) -> S3Reports:
        """
        Pull reports from S3 buckets.

        Args:
            region: AWS region
            campaign_ids: Optional filter for specific campaigns

        Returns:
            Structured S3 reports
        """
        logger.info("Pulling reports from S3...")

        try:
            # Pull from both buckets concurrently
            campaign_reports_task = asyncio.create_task(
                self._pull_campaign_reports(region, campaign_ids)
            )
            demo_reports_task = asyncio.create_task(self._pull_demo_reports(region, campaign_ids))

            campaign_reports, demo_reports = await asyncio.gather(
                campaign_reports_task,
                demo_reports_task,
                return_exceptions=True,
            )

            # Handle errors gracefully
            campaign_reports = (
                campaign_reports if not isinstance(campaign_reports, Exception) else {}
            )
            demo_reports = demo_reports if not isinstance(demo_reports, Exception) else {}

            s3_reports = S3Reports(
                campaign_reports=campaign_reports,
                demo_reports=demo_reports,
            )

            logger.info(f"Pulled {s3_reports.total_reports} S3 reports")
            return s3_reports

        except Exception as e:
            logger.error(f"Failed to pull S3 reports: {e}", exc_info=True)
            raise

    async def _pull_campaign_reports(
        self,
        region: str,
        campaign_ids: list[str] | None = None,
    ) -> dict[str, list[Path]]:
        """Pull campaign reports from results bucket."""
        reports = {}
        results_bucket = settings.aws.s3_results_bucket or "agenteval-results"

        try:
            # List all campaigns in S3
            prefix = "campaigns/"
            objects = await self.s3.list_objects(results_bucket, prefix)

            # Download reports for each campaign
            for obj_key in objects:
                # Extract campaign ID from path: campaigns/{campaign_id}/...
                parts = obj_key.split("/")
                if len(parts) >= 3:
                    campaign_id = parts[1]

                    # Filter if campaign_ids specified
                    if campaign_ids and campaign_id not in campaign_ids:
                        continue

                    # Download report
                    local_path = (
                        self.pulled_reports_dir / "campaign-reports" / campaign_id / parts[-1]
                    )
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    await self.s3.download_file(results_bucket, obj_key, local_path)

                    if campaign_id not in reports:
                        reports[campaign_id] = []
                    reports[campaign_id].append(local_path)

            logger.info(f"Downloaded reports for {len(reports)} campaigns")
            return reports

        except Exception as e:
            logger.warning(f"Could not pull campaign reports: {e}")
            return {}

    async def _pull_demo_reports(
        self,
        region: str,
        campaign_ids: list[str] | None = None,
    ) -> dict[str, list[Path]]:
        """Pull demo reports from reports bucket."""
        reports = {}
        reports_bucket = settings.aws.s3_reports_bucket or "agenteval-reports"

        try:
            # List all demo reports in S3
            prefix = "reports/"
            objects = await self.s3.list_objects(reports_bucket, prefix)

            # Download reports
            for obj_key in objects:
                # Extract campaign ID from path: reports/{campaign_id}/...
                parts = obj_key.split("/")
                if len(parts) >= 3:
                    campaign_id = parts[1]

                    # Filter if campaign_ids specified
                    if campaign_ids and campaign_id not in campaign_ids:
                        continue

                    # Download report
                    local_path = self.pulled_reports_dir / "demo-reports" / campaign_id / parts[-1]
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    await self.s3.download_file(reports_bucket, obj_key, local_path)

                    if campaign_id not in reports:
                        reports[campaign_id] = []
                    reports[campaign_id].append(local_path)

            logger.info(f"Downloaded demo reports for {len(reports)} campaigns")
            return reports

        except Exception as e:
            logger.warning(f"Could not pull demo reports: {e}")
            return {}

    async def pull_xray_traces(
        self,
        region: str,
        lookback_hours: int = 2,
    ) -> XRayTraces:
        """
        Pull X-Ray traces from the specified time window.

        Args:
            region: AWS region
            lookback_hours: Hours to look back for traces

        Returns:
            Structured X-Ray traces
        """
        logger.info(f"Pulling X-Ray traces (last {lookback_hours} hours)...")

        try:
            # Calculate time window
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=lookback_hours)

            # Get trace summaries
            trace_summaries = await self.xray.get_trace_summaries(
                start_time=start_time,
                end_time=end_time,
            )

            xray_traces = XRayTraces(trace_summaries=trace_summaries)

            # Save to disk
            trace_file = (
                self.trace_reports_dir
                / f"traces-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
            )
            await self._write_json(trace_file, {"TraceSummaries": trace_summaries})

            logger.info(f"Pulled {len(trace_summaries)} X-Ray traces")
            return xray_traces

        except Exception as e:
            logger.warning(f"Could not pull X-Ray traces: {e}")
            return XRayTraces()  # Return empty on failure

    async def generate_summary(self, results: ResultsBundle) -> Path:
        """
        Generate summary markdown file.

        Args:
            results: Results bundle to summarize

        Returns:
            Path to generated summary file
        """
        summary_file = self.output_dir / "SUMMARY.md"

        # Build summary content
        content = f"""# AgentEval Results Summary

**Generated**: {results.pulled_at.strftime("%Y-%m-%d %H:%M:%S UTC")}
**Region**: {results.region}

## 📊 Statistics

| Metric | Count |
|--------|-------|
| Campaigns | {len(results.campaign_data.campaigns)} |
| Turns | {len(results.campaign_data.turns)} |
| Evaluations | {len(results.campaign_data.evaluations)} |
| Reports | {results.s3_reports.total_reports} |
| Traces | {len(results.xray_traces.trace_summaries)} |

## 📁 Data Locations

### Campaign Data (DynamoDB)
- Campaigns: `{self.campaign_data_dir}/campaigns.json`
- Turns: `{self.campaign_data_dir}/turns.json`
- Evaluations: `{self.campaign_data_dir}/evaluations.json`

### Reports (S3)
- Campaign Reports: `{self.pulled_reports_dir}/campaign-reports/`
- Demo Reports: `{self.pulled_reports_dir}/demo-reports/`

### Traces (X-Ray)
- Trace Summaries: `{self.trace_reports_dir}/`

## 🔍 Quick Analysis Commands

### View campaigns
```bash
jq '.Items[] | {{
  campaign_id: .campaign_id.S,
  type: .campaign_type.S,
  status: .status.S,
  score: .stats.M.avg_score.N
}}' {self.campaign_data_dir}/campaigns.json
```

### Check for response echoing
```bash
jq -r '.Items[] | "Turn \\(.turn_number.N): " +
  (if .user_message.S == .system_response.S
   then "ECHOING ❌"
   else "NO ECHO ✅"
   end)' {self.campaign_data_dir}/turns.json
```

### View evaluation scores
```bash
jq '.Items[] | {{
  campaign: .campaign_id.S,
  turn: .turn_number.N,
  metrics: .metrics.M | keys
}}' {self.campaign_data_dir}/evaluations.json
```

---

For detailed analysis, use the HTML dashboard:
```bash
agenteval dashboard --html
```
"""

        await self._write_text(summary_file, content)
        logger.info(f"Generated summary: {summary_file}")
        return summary_file

    async def _write_json(self, file_path: Path, data: dict[str, Any]) -> None:
        """Write JSON data to file asynchronously."""
        content = json.dumps(data, indent=2, ensure_ascii=False)
        await self._write_text(file_path, content)

    async def _write_text(self, file_path: Path, content: str) -> None:
        """Write text content to file asynchronously."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, file_path.write_text, content)


# Factory function for dependency injection (Factory Pattern)
async def create_results_service(
    output_dir: Path | None = None,
) -> ResultsService:
    """
    Factory function to create ResultsService with all dependencies.

    This implements the Factory Pattern for clean object creation
    and follows Dependency Inversion Principle by injecting dependencies.

    Args:
        output_dir: Optional output directory override

    Returns:
        Configured ResultsService instance
    """
    # Create AWS clients and connect them
    dynamodb = DynamoDBClient()
    await dynamodb.connect()

    s3 = S3Client()
    await s3.connect()

    xray = XRayClient()
    await xray.connect()

    return ResultsService(
        dynamodb=dynamodb,
        s3=s3,
        xray=xray,
        output_dir=output_dir,
    )
