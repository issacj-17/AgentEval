"""
Evidence dashboard generator.

Aggregates artefacts collected under ``demo/evidence/pulled-reports``
into a human-friendly Markdown report summarising every campaign in
the latest run (or a specific run supplied via CLI arguments).

Usage::

    python -m agenteval.reporting.dashboard --latest
    python -m agenteval.reporting.dashboard --run-dir demo/evidence/pulled-reports/20251019T032317
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

__all__ = [
    "CampaignInsight",
    "collect_campaign_insights",
    "generate_dashboard",
    "generate_live_demo_summary",
]


PULLED_REPORTS_ROOT = Path("demo/evidence/pulled-reports")
DEFAULT_OUTPUT_PATH = Path("demo/evidence/dashboard.md")


@dataclass
class CampaignInsight:
    """Structured summary of a single evaluation campaign."""

    campaign_id: str
    campaign_type: str
    focus: str
    status: str
    created_at: str | None
    overall_score: float | None
    quality_score: float | None
    safety_score: float | None
    success_rate: float | None
    total_turns: int | None
    passing_turns: int | None
    failing_metrics: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    artifacts: dict[str, Path] = field(default_factory=dict)

    @property
    def failure_summary(self) -> str:
        """Return a short description of failing metrics."""
        if not self.failing_metrics:
            return "—"
        unique_metrics = list(dict.fromkeys(self.failing_metrics))
        return ", ".join(unique_metrics[:5]) + ("…" if len(unique_metrics) > 5 else "")

    def evidence_links(self, relative_to: Path) -> str:
        """Build Markdown links for evidence artefacts."""
        if not self.artifacts:
            return "—"
        links: list[str] = []
        for label, path in self.artifacts.items():
            try:
                rel_path = path.relative_to(relative_to)
            except ValueError:
                rel_path = path
            links.append(f"[{label}]({rel_path.as_posix()})")
        return "<br>".join(links)


def _load_json(path: Path) -> dict | None:
    """Safely load JSON from a file, returning None on failure."""
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None


def _latest_run_dir(root: Path) -> Path | None:
    """Locate the most recent evidence pull directory."""
    if not root.exists():
        return None
    candidates = [p for p in root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def collect_campaign_insights(run_dir: Path) -> list[CampaignInsight]:
    campaigns: list[CampaignInsight] = []
    for campaign_dir in sorted(run_dir.iterdir()):
        if not campaign_dir.is_dir():
            continue
        campaign_json = _load_json(campaign_dir / "dynamodb" / "campaign.json")
        if not campaign_json:
            continue

        campaign_id = campaign_json.get("campaign_id", campaign_dir.name)
        campaign_type = campaign_json.get("campaign_type", "unknown")
        status = campaign_json.get("status", "unknown")
        created_at = campaign_json.get("created_at")

        focus = _derive_focus_label(campaign_type, campaign_json.get("config", {}))

        aggregate_metrics = _load_latest_report_metrics(campaign_dir)
        results_summary = _load_results_summary(campaign_dir)
        failing_metrics = _collect_failing_metrics(campaign_dir)

        overall = aggregate_metrics.get("overall_score") if aggregate_metrics else None
        quality = aggregate_metrics.get("quality_score") if aggregate_metrics else None
        safety = aggregate_metrics.get("safety_score") if aggregate_metrics else None
        total_turns = aggregate_metrics.get("total_turns") if aggregate_metrics else None
        passing_turns = aggregate_metrics.get("passing_turns") if aggregate_metrics else None

        success_rate = results_summary.get("success_rate") if results_summary else None
        if success_rate is None and aggregate_metrics and total_turns:
            passing = aggregate_metrics.get("passing_turns")
            if passing is not None:
                success_rate = passing / total_turns if total_turns else None

        notes: list[str] = []
        if results_summary and results_summary.get("avg_response_time_ms"):
            notes.append(f"Avg response latency: {int(results_summary['avg_response_time_ms'])} ms")
        if not failing_metrics:
            notes.append("All metrics passed across evaluated turns.")

        artifacts = _discover_artifacts(campaign_dir)

        campaigns.append(
            CampaignInsight(
                campaign_id=campaign_id,
                campaign_type=campaign_type,
                focus=focus,
                status=status,
                created_at=created_at,
                overall_score=_safe_float(overall),
                quality_score=_safe_float(quality),
                safety_score=_safe_float(safety),
                success_rate=_safe_float(success_rate),
                total_turns=_safe_int(total_turns),
                passing_turns=_safe_int(passing_turns),
                failing_metrics=failing_metrics,
                notes=notes,
                artifacts=artifacts,
            )
        )

    return campaigns


def _derive_focus_label(campaign_type: str, config: dict) -> str:
    if campaign_type == "persona":
        return config.get("persona_type", "persona")
    if campaign_type == "red_team":
        categories = config.get("attack_categories")
        if isinstance(categories, (list, tuple)):
            return ", ".join(categories)
    if campaign_type == "combined":
        persona = config.get("persona_type", "persona")
        attacks = ", ".join(config.get("attack_categories", []))
        return f"{persona} + {attacks}" if attacks else persona
    return config.get("target_url", "n/a")


def _load_latest_report_metrics(campaign_dir: Path) -> dict[str, float]:
    results_dir = campaign_dir / "s3" / "results"
    if not results_dir.exists():
        return {}
    report_files = sorted(results_dir.glob("report-*.json"))
    for path in reversed(report_files):
        json_data = _load_json(path)
        if not json_data:
            continue
        metrics = (
            json_data.get("results", {}).get("aggregate_metrics")
            if "results" in json_data
            else json_data.get("aggregate_metrics")
        )
        if metrics:
            return metrics
    return {}


def _load_results_summary(campaign_dir: Path) -> dict[str, float]:
    summary_path = campaign_dir / "s3" / "results" / "results.json"
    json_data = _load_json(summary_path)
    if not json_data:
        return {}
    return json_data.get("results", {}).get("summary", {})


def _collect_failing_metrics(campaign_dir: Path) -> list[str]:
    failures: list[str] = []
    report_files = sorted((campaign_dir / "s3" / "results").glob("report-*.json"))
    for path in report_files:
        json_data = _load_json(path)
        if not json_data:
            continue
        turn_results = (
            json_data.get("results", {}).get("turn_results", [])
            if "results" in json_data
            else json_data.get("turn_results", [])
        )
        for turn in turn_results:
            evaluation = turn.get("evaluation") or turn.get("evaluation_result")
            if not evaluation:
                continue
            pass_fail = evaluation.get("pass_fail") or {}
            failed = pass_fail.get("failed_metrics") or []
            if isinstance(failed, dict):
                failed = list(failed.keys())
            failures.extend(str(metric) for metric in failed)
    return failures


def _discover_artifacts(campaign_dir: Path) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    results_json = campaign_dir / "s3" / "results" / "results.json"
    if results_json.exists():
        artifacts["results"] = results_json
    for path in sorted((campaign_dir / "s3" / "results").glob("report-*.json")):
        artifacts.setdefault("aggregate_report", path)
        break
    for path in sorted((campaign_dir / "s3" / "reports").glob("*.json")):
        artifacts.setdefault("formatted_report", path)
        break
    log_path = campaign_dir / "pull-live-reports.log"
    if log_path.exists():
        artifacts["pull_log"] = log_path
    return artifacts


def _safe_float(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: float | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _format_score(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def _render_markdown(run_dir: Path, campaigns: Sequence[CampaignInsight]) -> str:
    generated_at = datetime.utcnow().isoformat(timespec="seconds")
    live_summary = Path("demo/evidence/live-demo-latest.md")
    run_pull_log = run_dir / "pull-live-reports.log"

    header = [
        "# AgentEval Evidence Dashboard",
        "",
        f"- Generated: `{generated_at}` UTC",
        f"- Source run: `{run_dir.name}`",
        f"- Campaigns analysed: {len(campaigns)}",
        "",
    ]

    global_links: list[str] = []
    if live_summary.exists():
        global_links.append(f"[Live demo snapshot]({live_summary.as_posix()})")
    if run_pull_log.exists():
        global_links.append(f"[Run log]({run_pull_log.as_posix()})")
    if global_links:
        header.append("- Global artefacts: " + ", ".join(global_links))
        header.append("")

    if campaigns:
        avg_overall = (
            statistics.fmean(c.overall_score for c in campaigns if c.overall_score is not None)
            if any(c.overall_score is not None for c in campaigns)
            else None
        )
        avg_success = (
            statistics.fmean(c.success_rate for c in campaigns if c.success_rate is not None)
            if any(c.success_rate is not None for c in campaigns)
            else None
        )

        header.extend(
            [
                "## Portfolio Snapshot",
                "",
                f"- Average overall score: `{_format_score(avg_overall)}`",
                f"- Average success rate: `{_format_percent(avg_success)}`",
                "",
                "| Campaign | Type | Focus | Overall | Success | Failing Metrics | Evidence |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )

        for c in campaigns:
            header.append(
                f"| `{c.campaign_id[:8]}` | {c.campaign_type} | {c.focus} | "
                f"{_format_score(c.overall_score)} | {_format_percent(c.success_rate)} | "
                f"{c.failure_summary} | {c.evidence_links(Path('.'))} |"
            )
        header.append("")

    for c in campaigns:
        header.extend(_render_campaign_detail(c))

    if not campaigns:
        header.append("_No campaign artefacts were discovered in the selected run._")

    return "\n".join(header)


def _render_campaign_detail(c: CampaignInsight) -> list[str]:
    lines = [
        f"## Campaign `{c.campaign_id}`",
        "",
        f"- **Type:** {c.campaign_type}",
        f"- **Focus:** {c.focus}",
        f"- **Status:** {c.status}",
        f"- **Created:** {c.created_at or 'n/a'}",
        f"- **Overall score:** {_format_score(c.overall_score)}",
        f"- **Quality score:** {_format_score(c.quality_score)}",
        f"- **Safety score:** {_format_score(c.safety_score)}",
        f"- **Success rate:** {_format_percent(c.success_rate)}",
        f"- **Turns:** {c.passing_turns or 0}/{c.total_turns or 0} passing",
        "",
    ]

    if c.failing_metrics:
        lines.append("**Top failing metrics:**")
        lines.append("")
        for metric in list(dict.fromkeys(c.failing_metrics))[:10]:
            lines.append(f"- {metric}")
        lines.append("")
    else:
        lines.append("_All evaluated metrics passed._")
        lines.append("")

    if c.notes:
        lines.append("**Notable observations:**")
        lines.append("")
        for note in c.notes:
            lines.append(f"- {note}")
        lines.append("")

    if c.artifacts:
        lines.append("**Evidence artefacts:**")
        lines.append("")
        for label, path in c.artifacts.items():
            lines.append(f"- [{label}]({path.as_posix()})")
        lines.append("")

    return lines


def generate_dashboard(
    run_dir: Path,
    output_path: Path,
    campaigns: Sequence[CampaignInsight] | None = None,
) -> Path:
    """Generate the dashboard markdown for a specific run directory."""
    insights = list(campaigns) if campaigns is not None else collect_campaign_insights(run_dir)
    markdown = _render_markdown(run_dir, insights)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown)
    return output_path


def generate_live_demo_summary(
    run_dir: Path,
    output_path: Path,
    campaigns: Sequence[CampaignInsight] | None = None,
) -> Path:
    """Generate a compact summary table similar to the legacy live demo report."""
    insights = list(campaigns) if campaigns is not None else collect_campaign_insights(run_dir)

    lines = [
        "# AgentEval Live Demo Summary",
        "",
        f"*Latest pull:* `{run_dir.name}`",
        "",
        "| Campaign ID | Type | Focus | Status | Turns (completed/total) | Success Rate |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    if not insights:
        lines.append("| _n/a_ | _n/a_ | _n/a_ | _n/a_ | _n/a_ | _n/a_ |")
    else:
        for insight in insights:
            total_turns = insight.total_turns or 0
            passing_turns = insight.passing_turns or 0
            lines.append(
                f"| `{insight.campaign_id}` | {insight.campaign_type} | {insight.focus} | "
                f"{insight.status} | {passing_turns}/{total_turns} | {_format_percent(insight.success_rate)} |"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n")
    return output_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate AgentEval evidence dashboard.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--latest",
        action="store_true",
        help="Use the most recent directory under demo/evidence/pulled-reports.",
    )
    group.add_argument(
        "--run-dir",
        type=Path,
        help="Explicit pulled-reports directory to process.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Destination markdown file (default: {DEFAULT_OUTPUT_PATH}).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.run_dir:
        run_dir = args.run_dir
    else:
        run_dir = _latest_run_dir(PULLED_REPORTS_ROOT)

    if not run_dir or not run_dir.exists():
        raise SystemExit("No evidence runs found. Please execute a live demo first.")

    output_path = args.output
    generated = generate_dashboard(run_dir, output_path)
    print(f"Dashboard generated: {generated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
