from __future__ import annotations

import sys
from unittest.mock import AsyncMock

import pytest

from agenteval.aws.s3 import (
    CSVReportRenderer,
    HTMLReportRenderer,
    JSONReportRenderer,
    PDFReportRenderer,
    ReportFormat,
    S3Client,
)


@pytest.mark.asyncio
async def test_json_report_renderer_round_trip() -> None:
    renderer = JSONReportRenderer()
    payload = {"campaign_id": "abc", "score": 0.87}

    rendered = await renderer.render(payload)
    assert rendered.decode("utf-8").strip().startswith("{")
    assert renderer.get_content_type() == "application/json"
    assert renderer.get_file_extension() == "json"


@pytest.mark.asyncio
async def test_csv_report_renderer_formats_turns_and_summary() -> None:
    renderer = CSVReportRenderer()
    payload = {
        "campaign_id": "cmp-123",
        "campaign_type": "persona",
        "status": "completed",
        "turns_completed": 2,
        "success_rate": 0.75,
        "turn_results": [
            {
                "turn_number": 1,
                "user_message": "Hello there",
                "system_response": "Hi!",
                "timestamp": "2025-10-19T00:00:00Z",
                "evaluation_result": {
                    "aggregate_scores": {
                        "overall": 0.9,
                        "helpfulness": 0.8,
                        "accuracy": 0.7,
                        "safety": 1.0,
                    }
                },
            },
            {
                "turn_number": 2,
                "user_message": "What's the weather?",
                "system_response": "Sunny",
                "timestamp": "2025-10-19T00:01:00Z",
            },
        ],
    }

    rendered = await renderer.render(payload)
    csv_text = rendered.decode("utf-8")

    assert "turn_number,user_message,system_response" in csv_text.splitlines()[0]
    assert "# Campaign Summary" in csv_text
    assert "Success Rate,75.00%" in csv_text
    assert renderer.get_content_type() == "text/csv"
    assert renderer.get_file_extension() == "csv"


@pytest.mark.asyncio
async def test_html_renderer_escapes_messages() -> None:
    renderer = HTMLReportRenderer()
    payload = {
        "campaign_id": "cmp-secure",
        "campaign_type": "persona",
        "status": "completed",
        "turns_completed": 1,
        "turn_results": [
            {
                "turn_number": 1,
                "user_message": "<script>alert('x')</script>",
                "system_response": "<div>ok</div>",
            }
        ],
    }

    rendered = await renderer.render(payload)
    html = rendered.decode("utf-8")

    assert "&lt;script&gt;" in html
    assert "&lt;div&gt;ok&lt;/div&gt;" in html
    assert renderer.get_content_type() == "text/html"
    assert renderer.get_file_extension() == "html"


@pytest.mark.asyncio
async def test_pdf_renderer_falls_back_without_weasyprint(monkeypatch: pytest.MonkeyPatch) -> None:
    async_render = AsyncMock(return_value=b"<html>fallback</html>")
    monkeypatch.setattr(HTMLReportRenderer, "render", async_render, raising=False)
    monkeypatch.delitem(sys.modules, "weasyprint", raising=False)

    renderer = PDFReportRenderer()
    payload = {"campaign_id": "cmp-pdf", "turns_completed": 0}

    rendered = await renderer.render(payload)

    assert rendered == b"<html>fallback</html>"
    async_render.assert_awaited()
    assert renderer.get_content_type() == "application/pdf"
    assert renderer.get_file_extension() == "pdf"


@pytest.mark.asyncio
async def test_store_report_uses_renderer_and_uploads(monkeypatch: pytest.MonkeyPatch) -> None:
    client = S3Client(region="us-east-1", profile=None)
    client.reports_bucket = "reports-bucket"
    client._connected = True
    client._client = object()

    upload_mock = AsyncMock(return_value="s3://reports-bucket/reports/cmp/custom-20250101.csv")
    presign_mock = AsyncMock(return_value="https://example.com/report")
    monkeypatch.setattr(client, "upload_bytes", upload_mock)
    monkeypatch.setattr(client, "generate_presigned_url", presign_mock)

    payload = {
        "campaign_id": "cmp",
        "turns_completed": 1,
        "turn_results": [{"turn_number": 1, "user_message": "Hi", "system_response": "Hello"}],
    }

    s3_uri, presigned_url = await client.store_report(
        campaign_id="cmp",
        report_data=payload,
        report_format=ReportFormat.CSV,
        filename_prefix="custom",
    )

    assert s3_uri.endswith(".csv")
    assert presigned_url == "https://example.com/report"
    upload_kwargs = upload_mock.await_args.kwargs
    assert upload_kwargs["bucket"] == "reports-bucket"
    assert upload_kwargs["content_type"] == "text/csv"
    assert upload_kwargs["key"].startswith("reports/cmp/custom-")
    presign_mock.assert_awaited_once()


def test_get_renderer_fallback_to_json() -> None:
    client = S3Client(region="us-east-1", profile=None)
    renderer = client._get_renderer(None)  # type: ignore[arg-type]

    assert isinstance(renderer, JSONReportRenderer)
