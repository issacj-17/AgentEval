"""
Amazon S3 Client for Results and Report Storage

Supports multiple report formats: JSON, CSV, PDF, HTML
"""

import csv
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from agenteval.config import settings

logger = logging.getLogger(__name__)


class ReportFormat(str, Enum):
    """Supported report formats"""

    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"


class ReportRenderer(ABC):
    """Abstract base class for report renderers"""

    @abstractmethod
    async def render(self, report_data: dict[str, Any]) -> bytes:
        """
        Render report data to bytes

        Args:
            report_data: Report data dictionary

        Returns:
            Rendered report as bytes
        """
        pass

    @abstractmethod
    def get_content_type(self) -> str:
        """Get MIME content type for this format"""
        pass

    @abstractmethod
    def get_file_extension(self) -> str:
        """Get file extension for this format"""
        pass


class JSONReportRenderer(ReportRenderer):
    """Renders reports as JSON"""

    async def render(self, report_data: dict[str, Any]) -> bytes:
        """Render as formatted JSON"""
        json_str = json.dumps(report_data, indent=2, default=str)
        return json_str.encode("utf-8")

    def get_content_type(self) -> str:
        return "application/json"

    def get_file_extension(self) -> str:
        return "json"


class CSVReportRenderer(ReportRenderer):
    """Renders reports as CSV"""

    async def render(self, report_data: dict[str, Any]) -> bytes:
        """Render as CSV with flattened structure"""
        output = StringIO()

        # Extract turn results for tabular format
        if "turn_results" in report_data:
            turns = report_data["turn_results"]
            if turns:
                # Get fieldnames from first turn (flattened)
                fieldnames = self._get_csv_fieldnames(turns[0])

                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()

                for turn in turns:
                    flattened = self._flatten_turn(turn)
                    writer.writerow(flattened)

        # Add summary section
        output.write("\n\n# Campaign Summary\n")
        summary_data = {
            "Campaign ID": report_data.get("campaign_id", "N/A"),
            "Campaign Type": report_data.get("campaign_type", "N/A"),
            "Status": report_data.get("status", "N/A"),
            "Turns Completed": report_data.get("turns_completed", 0),
            "Success Rate": (
                f"{report_data.get('success_rate', 0):.2%}"
                if "success_rate" in report_data
                else "N/A"
            ),
            "Created At": report_data.get("created_at", "N/A"),
            "Completed At": report_data.get("completed_at", "N/A"),
        }

        for key, value in summary_data.items():
            output.write(f"{key},{value}\n")

        return output.getvalue().encode("utf-8")

    def _get_csv_fieldnames(self, turn: dict[str, Any]) -> list[str]:
        """Get CSV field names from turn structure"""
        base_fields = [
            "turn_number",
            "user_message",
            "system_response",
            "overall_score",
            "helpfulness_score",
            "accuracy_score",
            "safety_score",
            "timestamp",
        ]

        # Add any additional top-level fields
        for key in turn:
            if key not in base_fields and not isinstance(turn[key], (dict, list)):
                base_fields.append(key)

        return base_fields

    def _flatten_turn(self, turn: dict[str, Any]) -> dict[str, Any]:
        """Flatten nested turn structure for CSV"""
        flattened = {
            "turn_number": turn.get("turn_number", ""),
            "user_message": turn.get("user_message", "")[:200],  # Truncate long messages
            "system_response": turn.get("system_response", "")[:200],
            "timestamp": turn.get("timestamp", ""),
        }

        # Extract scores from evaluation_result if present
        if "evaluation_result" in turn:
            eval_result = turn["evaluation_result"]
            if "aggregate_scores" in eval_result:
                scores = eval_result["aggregate_scores"]
                flattened["overall_score"] = scores.get("overall", "")
                flattened["helpfulness_score"] = scores.get("helpfulness", "")
                flattened["accuracy_score"] = scores.get("accuracy", "")
                flattened["safety_score"] = scores.get("safety", "")

        # Add any other simple fields
        for key, value in turn.items():
            if key not in flattened and not isinstance(value, (dict, list)):
                flattened[key] = value

        return flattened

    def get_content_type(self) -> str:
        return "text/csv"

    def get_file_extension(self) -> str:
        return "csv"


class HTMLReportRenderer(ReportRenderer):
    """Renders reports as HTML"""

    async def render(self, report_data: dict[str, Any]) -> bytes:
        """Render as HTML with basic styling"""
        html = self._build_html(report_data)
        return html.encode("utf-8")

    def _build_html(self, report_data: dict[str, Any]) -> str:
        """Build HTML report"""
        campaign_id = report_data.get("campaign_id", "N/A")
        campaign_type = report_data.get("campaign_type", "N/A")
        status = report_data.get("status", "N/A")
        turns_completed = report_data.get("turns_completed", 0)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AgentEval Report - {campaign_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .summary {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .summary-item {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .summary-item label {{
            font-weight: 600;
            color: #666;
            font-size: 0.9em;
        }}
        .summary-item value {{
            display: block;
            font-size: 1.2em;
            color: #333;
            margin-top: 5px;
        }}
        .turn {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .turn-header {{
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .message {{
            margin: 10px 0;
            padding: 10px;
            border-radius: 5px;
        }}
        .user-message {{
            background: #e3f2fd;
            border-left: 4px solid #2196f3;
        }}
        .system-response {{
            background: #f3e5f5;
            border-left: 4px solid #9c27b0;
        }}
        .scores {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin-top: 10px;
        }}
        .score {{
            padding: 8px 15px;
            background: #4caf50;
            color: white;
            border-radius: 20px;
            font-size: 0.9em;
        }}
        .score.low {{
            background: #f44336;
        }}
        .score.medium {{
            background: #ff9800;
        }}
        footer {{
            text-align: center;
            margin-top: 40px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AgentEval Campaign Report</h1>
        <p>Campaign ID: {campaign_id}</p>
    </div>

    <div class="summary">
        <h2>Campaign Summary</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <label>Campaign Type</label>
                <value>{campaign_type}</value>
            </div>
            <div class="summary-item">
                <label>Status</label>
                <value>{status}</value>
            </div>
            <div class="summary-item">
                <label>Turns Completed</label>
                <value>{turns_completed}</value>
            </div>
"""

        # Add success rate if available
        if "success_rate" in report_data:
            success_rate = report_data["success_rate"]
            html += f"""
            <div class="summary-item">
                <label>Success Rate</label>
                <value>{success_rate:.1%}</value>
            </div>
"""

        html += """
        </div>
    </div>

    <h2>Turn-by-Turn Results</h2>
"""

        # Add turns
        if "turn_results" in report_data:
            for turn in report_data["turn_results"]:
                turn_num = turn.get("turn_number", "N/A")
                user_msg = turn.get("user_message", "N/A")
                sys_resp = turn.get("system_response", "N/A")

                html += f"""
    <div class="turn">
        <div class="turn-header">
            <h3>Turn {turn_num}</h3>
        </div>
        <div class="message user-message">
            <strong>User:</strong><br>
            {self._escape_html(user_msg)}
        </div>
        <div class="message system-response">
            <strong>System:</strong><br>
            {self._escape_html(sys_resp)}
        </div>
"""

                # Add scores if available
                if "evaluation_result" in turn:
                    eval_result = turn["evaluation_result"]
                    if "aggregate_scores" in eval_result:
                        scores = eval_result["aggregate_scores"]
                        html += '        <div class="scores">\n'
                        for score_name, score_value in scores.items():
                            if isinstance(score_value, (int, float)):
                                score_class = (
                                    "low"
                                    if score_value < 0.5
                                    else "medium"
                                    if score_value < 0.8
                                    else ""
                                )
                                html += f'            <span class="score {score_class}">{score_name}: {score_value:.2f}</span>\n'
                        html += "        </div>\n"

                html += "    </div>\n"

        html += (
            """
    <footer>
        <p>Generated by AgentEval - Multi-Agent AI Evaluation Platform</p>
        <p>Report generated at """
            + datetime.now().isoformat()
            + """</p>
    </footer>
</body>
</html>
"""
        )

        return html

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )

    def get_content_type(self) -> str:
        return "text/html"

    def get_file_extension(self) -> str:
        return "html"


class PDFReportRenderer(ReportRenderer):
    """Renders reports as PDF (requires weasyprint)"""

    async def render(self, report_data: dict[str, Any]) -> bytes:
        """Render as PDF using HTML intermediate"""
        try:
            # Try to import weasyprint
            from weasyprint import CSS
            from weasyprint import HTML as WeasyHTML

            # Use HTML renderer as base
            html_renderer = HTMLReportRenderer()
            html_content = await html_renderer.render(report_data)
            html_str = html_content.decode("utf-8")

            # Convert HTML to PDF
            pdf_bytes = WeasyHTML(string=html_str).write_pdf()
            return pdf_bytes

        except ImportError:
            logger.warning("WeasyPrint not installed, falling back to HTML")
            # Fallback to HTML if weasyprint not available
            html_renderer = HTMLReportRenderer()
            return await html_renderer.render(report_data)
        except Exception as e:
            logger.error(f"PDF generation failed: {e}, falling back to HTML")
            # Fallback to HTML on any error
            html_renderer = HTMLReportRenderer()
            return await html_renderer.render(report_data)

    def get_content_type(self) -> str:
        return "application/pdf"

    def get_file_extension(self) -> str:
        return "pdf"


class S3Client:
    """
    Async client for Amazon S3 operations

    Supports dependency injection of configuration parameters.
    Falls back to global settings if not provided.
    """

    def __init__(
        self,
        region: str | None = None,
        profile: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        results_bucket: str | None = None,
        reports_bucket: str | None = None,
    ) -> None:
        """
        Initialize S3 client

        Args:
            region: AWS region (defaults to settings.aws.region)
            profile: AWS profile name (defaults to settings.aws.profile)
            access_key_id: AWS access key ID (defaults to settings.aws.access_key_id)
            secret_access_key: AWS secret access key (defaults to settings.aws.secret_access_key)
            results_bucket: Results bucket name (defaults to settings.aws.s3_results_bucket)
            reports_bucket: Reports bucket name (defaults to settings.aws.s3_reports_bucket)
        """
        # Use provided config or fall back to settings (backward compatibility)
        self.region = region or settings.aws.region
        self.profile = profile or settings.aws.profile
        self.access_key_id = access_key_id or settings.aws.access_key_id
        self.secret_access_key = secret_access_key or settings.aws.secret_access_key

        # Bucket names
        self.results_bucket = results_bucket or settings.aws.s3_results_bucket
        self.reports_bucket = reports_bucket or settings.aws.s3_reports_bucket

        self.session = aioboto3.Session(
            region_name=self.region,
            profile_name=self.profile,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        self._client: Any | None = None
        self._connected: bool = False

        logger.debug(
            "S3Client initialized",
            extra={"region": self.region, "profile": self.profile or "default"},
        )

    async def connect(self) -> None:
        """Initialize S3 client connection"""
        if not self._connected:
            self._client = await self.session.client("s3").__aenter__()
            self._connected = True
            logger.info("S3 client connected")

    async def close(self) -> None:
        """Close S3 client connection"""
        if self._connected and self._client:
            await self._client.__aexit__(None, None, None)
            self._connected = False
            logger.info("S3 client closed")

    async def __aenter__(self) -> "S3Client":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    def _ensure_connected(self) -> None:
        """Ensure client is connected before operations"""
        if not self._connected or not self._client:
            raise RuntimeError("S3 client not connected. Call connect() first.")

    async def upload_json(self, bucket: str, key: str, data: dict[str, Any]) -> str:
        """Upload JSON data to S3"""
        self._ensure_connected()
        try:
            json_bytes = json.dumps(data, indent=2).encode("utf-8")
            await self._client.put_object(
                Bucket=bucket, Key=key, Body=json_bytes, ContentType="application/json"
            )
            logger.info(f"Uploaded JSON to s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"
        except ClientError as e:
            logger.error(f"Failed to upload JSON: {e}")
            raise

    async def download_json(self, bucket: str, key: str) -> dict[str, Any]:
        """Download and parse JSON from S3"""
        self._ensure_connected()
        try:
            response = await self._client.get_object(Bucket=bucket, Key=key)
            body = await response["Body"].read()
            response["Body"].close()
            return json.loads(body.decode("utf-8"))
        except ClientError as e:
            logger.error(f"Failed to download JSON: {e}")
            raise

    async def list_objects(
        self, bucket: str | None = None, prefix: str | None = None
    ) -> list[dict[str, Any]]:
        """
        List objects in an S3 bucket.

        Args:
            bucket: Override bucket name (defaults to results bucket).
            prefix: Optional key prefix to filter results.

        Returns:
            A list of object metadata dictionaries.
        """
        self._ensure_connected()
        target_bucket = bucket or self.results_bucket
        paginator = self._client.get_paginator("list_objects_v2")
        operation_kwargs: dict[str, Any] = {"Bucket": target_bucket}
        if prefix:
            operation_kwargs["Prefix"] = prefix

        objects: list[dict[str, Any]] = []

        try:
            async for page in paginator.paginate(**operation_kwargs):
                for obj in page.get("Contents", []):
                    objects.append(
                        {
                            "key": obj["Key"],
                            "size": obj.get("Size", 0),
                            "last_modified": obj.get("LastModified"),
                        }
                    )
        except ClientError as e:
            logger.error(f"Failed to list S3 objects: {e}")
            raise

        return objects

    async def download_object(self, bucket: str, key: str, destination: Path) -> Path:
        """
        Download an arbitrary object from S3 to a local path.

        Args:
            bucket: Bucket name.
            key: Object key.
            destination: Local filesystem path to write.

        Returns:
            Path to the downloaded file.
        """
        self._ensure_connected()
        try:
            response = await self._client.get_object(Bucket=bucket, Key=key)
            body = await response["Body"].read()
            response["Body"].close()

            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)

            logger.info(f"Downloaded s3://{bucket}/{key} -> {destination}")
            return destination
        except ClientError as e:
            logger.error(f"Failed to download object: {e}")
            raise

    async def upload_bytes(
        self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes to S3"""
        self._ensure_connected()
        try:
            await self._client.put_object(
                Bucket=bucket, Key=key, Body=data, ContentType=content_type
            )
            logger.info(f"Uploaded bytes to s3://{bucket}/{key}")
            return f"s3://{bucket}/{key}"
        except ClientError as e:
            logger.error(f"Failed to upload bytes: {e}")
            raise

    async def generate_presigned_url(self, bucket: str, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL for download"""
        self._ensure_connected()
        try:
            url = await self._client.generate_presigned_url(
                "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    async def store_results(
        self, campaign_id: str, results_data: dict[str, Any], object_key: str
    ) -> str:
        """
        Store campaign results to S3 (raw data bucket)

        This is a convenience wrapper around upload_json that uses
        the configured results bucket and formats the payload.

        Args:
            campaign_id: Campaign identifier
            results_data: Results data to store
            object_key: S3 object key

        Returns:
            S3 URI of stored results
        """
        self._ensure_connected()
        target_bucket = self.results_bucket
        payload = {"campaign_id": campaign_id, "results": results_data}

        return await self.upload_json(target_bucket, object_key, payload)

    async def store_report(
        self,
        campaign_id: str,
        report_data: dict[str, Any],
        report_format: ReportFormat = ReportFormat.JSON,
        filename_prefix: str | None = None,
    ) -> tuple[str, str]:
        """
        Store formatted campaign report to S3 (reports bucket)

        Uses report renderers to generate formatted reports in multiple formats.
        Routes to the reports bucket (separate from raw results).

        Args:
            campaign_id: Campaign identifier
            report_data: Report data to render
            report_format: Desired report format (JSON, CSV, PDF, HTML)
            filename_prefix: Optional filename prefix (default: "report-{campaign_id}")

        Returns:
            Tuple of (s3_uri, presigned_url) for download
        """
        self._ensure_connected()

        # Select appropriate renderer
        renderer = self._get_renderer(report_format)

        # Render report
        logger.info(f"Rendering report in {report_format.value} format")
        rendered_bytes = await renderer.render(report_data)

        # Build object key
        prefix = filename_prefix or f"report-{campaign_id}"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_ext = renderer.get_file_extension()
        object_key = f"reports/{campaign_id}/{prefix}-{timestamp}.{file_ext}"

        # Upload to reports bucket
        target_bucket = self.reports_bucket
        content_type = renderer.get_content_type()

        s3_uri = await self.upload_bytes(
            bucket=target_bucket, key=object_key, data=rendered_bytes, content_type=content_type
        )

        # Generate presigned URL for easy download
        presigned_url = await self.generate_presigned_url(
            bucket=target_bucket,
            key=object_key,
            expiration=3600 * 24,  # 24 hours
        )

        logger.info(
            "Report stored successfully",
            extra={
                "campaign_id": campaign_id,
                "format": report_format.value,
                "s3_uri": s3_uri,
                "size_bytes": len(rendered_bytes),
            },
        )

        return s3_uri, presigned_url

    def _get_renderer(self, report_format: ReportFormat) -> ReportRenderer:
        """Get appropriate renderer for format"""
        renderers = {
            ReportFormat.JSON: JSONReportRenderer(),
            ReportFormat.CSV: CSVReportRenderer(),
            ReportFormat.HTML: HTMLReportRenderer(),
            ReportFormat.PDF: PDFReportRenderer(),
        }

        renderer = renderers.get(report_format)
        if not renderer:
            logger.warning(f"Unknown format {report_format}, using JSON")
            return JSONReportRenderer()

        return renderer


async def get_s3_client() -> S3Client:
    """Dependency injection for S3 client"""
    return S3Client()
