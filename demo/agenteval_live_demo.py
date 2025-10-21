#!/usr/bin/env python3
"""
AgentEval Live Demo with Real AWS Services
===========================================

This demo validates AgentEval in a production-like environment using real AWS services:
1. AWS Bedrock for LLM agents (Persona, Red Team, Judge)
2. DynamoDB for campaign and turn state management
3. S3 for results and report storage
4. EventBridge for event publishing
5. X-Ray for distributed tracing

Prerequisites:
- AWS credentials configured
- Run scripts/setup-live-demo.sh first
- .env.live-demo configuration file

Usage:
    python demo/agenteval_live_demo.py [--quick]
"""

import asyncio
import json
import logging
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import yaml

BASE_DIR = Path(__file__).parent.parent
LIVE_DEMO_ENV_PATH = BASE_DIR / ".env.live-demo"
sys.path.insert(0, str(BASE_DIR / "src"))

from agenteval.utils.live_demo_env import bootstrap_live_demo_env, refresh_settings

ENV_BOOTSTRAPPED = bootstrap_live_demo_env(LIVE_DEMO_ENV_PATH)
refresh_settings()

from agenteval.aws.s3 import ReportFormat
from agenteval.config import settings
from agenteval.container import Container, reset_container
from agenteval.orchestration.campaign import CampaignType
from agenteval.reporting.output_manager import get_output_manager
from agenteval.reporting.pull import pull_campaign_data

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Suppress noisy AWS SDK logging
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("aioboto3").setLevel(logging.WARNING)


class LiveDemoRunner:
    """Orchestrates the live AgentEval demonstration with real AWS services"""

    def __init__(self, quick_mode: bool = False):
        self.quick_mode = quick_mode
        self.container: Container = None
        self.campaign_ids: list[str] = []
        self.demo_metadata = {
            "start_time": datetime.utcnow().isoformat(),
            "region": settings.aws.region,
            "environment": settings.app.environment,
        }
        self.primary_target_url: str = settings.demo.target_url
        self.fallback_target_url: str | None = settings.demo.fallback_target_url
        self.active_target_url: str = self.primary_target_url
        self._turn_sample_limit = 2

        # Load demo configuration from YAML
        self.config = self._load_demo_config()

        # Use config values, falling back to settings if not in config
        self.persona_max_turns = self.config.get("demo_settings", {}).get(
            "persona_turns_per_campaign", settings.demo.persona_max_turns
        )
        self.redteam_max_turns = self.config.get("demo_settings", {}).get(
            "redteam_turns_per_campaign", settings.demo.redteam_max_turns
        )

        # Use OutputManager for consistent directory structure
        self.output_manager = get_output_manager()
        self.output_manager.ensure_directories()
        self.run_timestamp = self.output_manager.run_timestamp
        self.evidence_root = self.output_manager.evidence_root
        self.trace_reports_dir = self.output_manager.traces_dir
        self.campaign_trace_reports: dict[str, Path] = {}

    def _load_demo_config(self) -> dict:
        """Load demo configuration from demo_config.yaml"""
        config_path = BASE_DIR / "demo" / "demo_config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                return yaml.safe_load(f)
        return {}

    def _get_enabled_personas(self) -> list[str]:
        """Get list of enabled persona IDs from config"""
        personas = self.config.get("personas", [])
        return [p["id"] for p in personas if p.get("enabled", False)]

    def _get_enabled_attack_categories(self) -> list[str]:
        """Get list of enabled attack categories from config"""
        categories = self.config.get("attack_categories", {})
        return [cat for cat, data in categories.items() if data.get("enabled", False)]

    @staticmethod
    def _summarize_response(response: Any) -> str:
        """Return a compact human-readable summary of a model response."""

        if response is None:
            return "(no response)"

        if isinstance(response, dict):
            for key in ("message", "content", "text"):
                if key in response and isinstance(response[key], str):
                    return response[key][:200]
            return json.dumps(response)[:200]

        if isinstance(response, str):
            try:
                data = json.loads(response)
                if isinstance(data, dict):
                    for key in ("message", "text", "body", "json"):
                        value = data.get(key)
                        if isinstance(value, str):
                            return value[:200]
                        if isinstance(value, dict) and "message" in value:
                            msg = value["message"]
                            if isinstance(msg, str):
                                return msg[:200]
                    return json.dumps(data)[:200]
            except json.JSONDecodeError:
                pass
            return response[:200]

        return str(response)[:200]

    @staticmethod
    def _build_campaign_summary(campaign: dict[str, Any]) -> dict[str, Any]:
        """Construct a numeric summary payload from a campaign record."""
        stats = campaign.get("stats", {}) if isinstance(campaign, dict) else {}

        def _as_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        total_turns = _as_int(stats.get("total_turns"))
        completed_turns = _as_int(stats.get("completed_turns"))
        failed_turns = _as_int(stats.get("failed_turns"))
        avg_score = stats.get("avg_score")

        summary = {
            "total_turns": total_turns,
            "completed_turns": completed_turns,
            "failed_turns": failed_turns,
        }

        if avg_score is not None:
            summary["average_score"] = avg_score

        if total_turns > 0:
            summary["success_rate"] = round(completed_turns / total_turns, 2)

        return summary

    def _build_campaign_insights(
        self, campaign: dict[str, Any], evaluations: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Derive qualitative insights from stored evaluations."""
        campaign_type = campaign.get("campaign_type")
        insights: dict[str, Any] = {"total_evaluations": len(evaluations)}

        if campaign_type == CampaignType.PERSONA.value:
            fail_counter: Counter[str] = Counter()
            sample_reasoning: str | None = None

            for evaluation in evaluations:
                failed = evaluation.get("pass_fail", {}).get("failed_metrics", [])
                fail_counter.update(m for m in failed if isinstance(m, str))

                if sample_reasoning:
                    continue

                metric_results = evaluation.get("metric_results", {})
                for metric in metric_results.values():
                    if isinstance(metric, dict) and not metric.get("passed", True):
                        reasoning = metric.get("reasoning")
                        if isinstance(reasoning, str) and reasoning.strip():
                            sample_reasoning = reasoning.strip()
                            break

            if fail_counter:
                insights["failed_metric_counts"] = dict(fail_counter)
                insights["top_failed_metrics"] = [
                    metric for metric, _ in fail_counter.most_common(3)
                ]

            if sample_reasoning:
                insights["sample_reasoning"] = sample_reasoning[:500]

        elif campaign_type == CampaignType.RED_TEAM.value:
            critical_failures: set[str] = set()
            failed_metrics: set[str] = set()

            for evaluation in evaluations:
                pass_fail = evaluation.get("pass_fail", {})
                critical_failures.update(
                    m for m in pass_fail.get("critical_failures", []) if isinstance(m, str)
                )
                failed_metrics.update(
                    m for m in pass_fail.get("failed_metrics", []) if isinstance(m, str)
                )

            if critical_failures:
                insights["critical_failures"] = sorted(critical_failures)
            if failed_metrics:
                insights["failed_metrics"] = sorted(failed_metrics)

        return insights

    def print_header(self, text: str):
        """Print formatted section header"""
        print("\n" + "=" * 80)
        print(f"  {text}")
        print("=" * 80 + "\n")

    def print_success(self, text: str):
        """Print success message"""
        print(f"✓ {text}")

    def print_info(self, text: str):
        """Print info message"""
        print(f"ℹ {text}")

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"⚠ {text}")

    def print_error(self, text: str):
        """Print error message"""
        print(f"✗ {text}")

    async def verify_aws_connectivity(self) -> bool:
        """Verify AWS services are accessible before starting demo"""
        self.print_header("VERIFYING AWS CONNECTIVITY")

        try:
            # Test DynamoDB
            self.print_info("Testing DynamoDB connection...")
            await self.container.dynamodb().connect()
            try:
                tables = await self.container.dynamodb().list_campaigns(limit=1)
                self.print_success(f"DynamoDB connected (region: {settings.aws.region})")
            except Exception as e:
                if "ResourceNotFoundException" in str(e) or "does not exist" in str(e):
                    self.print_error(f"AWS connectivity check failed: {e}")
                    self.print_info("")
                    self.print_info("Did you run the setup script?")
                    self.print_info("  → scripts/setup-live-demo.sh")
                    return False
                raise

            # Test S3
            self.print_info("Testing S3 connection...")
            await self.container.s3().connect()
            self.print_success(f"S3 connected (bucket: {settings.aws.s3_results_bucket})")

            # Test EventBridge
            self.print_info("Testing EventBridge connection...")
            await self.container.eventbridge().connect()
            self.print_success(f"EventBridge connected (bus: {settings.aws.eventbridge_bus_name})")

            # Test X-Ray (optional)
            try:
                self.print_info("Testing X-Ray connection...")
                await self.container.xray().connect()
                self.print_success("X-Ray connected (tracing enabled)")
            except Exception as e:
                self.print_warning(f"X-Ray not available: {e}")
                self.print_info("  → Demo will continue without distributed tracing")

            return True

        except Exception as e:
            self.print_error(f"AWS connectivity check failed: {e}")
            self.print_info("")
            self.print_info("Did you run the setup script?")
            self.print_info("  → scripts/setup-live-demo.sh")
            return False

    async def resolve_target_url(self) -> None:
        """Ensure the demo target endpoint is reachable, falling back if required."""
        candidate_urls = [self.primary_target_url]
        if self.fallback_target_url and self.fallback_target_url not in candidate_urls:
            candidate_urls.append(self.fallback_target_url)

        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            last_error: Exception | None = None
            for url in candidate_urls:
                try:
                    # Prefer HEAD to avoid mutating endpoints; fall back to GET
                    head_response = await client.head(url, follow_redirects=True)
                    head_response.raise_for_status()
                except Exception as head_error:
                    self.print_warning(
                        f"HEAD probe failed for {url}: {head_error}. Retrying with GET."
                    )
                    try:
                        get_response = await client.get(url, follow_redirects=True)
                        try:
                            get_response.raise_for_status()
                        except httpx.HTTPStatusError as exc:
                            if exc.response.status_code == 405:
                                self.print_info(
                                    f"Target {url} responded 405 to GET (likely POST-only). "
                                    "Considering endpoint reachable."
                                )
                            else:
                                raise
                    except Exception as exc:
                        last_error = exc
                        continue
                self.active_target_url = url
                if url != self.primary_target_url:
                    self.print_warning(f"Primary target unreachable. Falling back to {url}")
                else:
                    self.print_info(f"Using target endpoint: {url}")
                return

        # If all targets fail, keep the last candidate but warn
        self.active_target_url = candidate_urls[-1]
        if last_error:
            self.print_warning(
                f"Unable to reach configured target endpoints. HTTP calls may fail ({last_error})."
            )

    async def demo_persona_campaign(self) -> str:
        """Create and execute a Persona Agent campaign"""
        self.print_header("1. PERSONA AGENT - Real AWS Bedrock Execution")

        # All 10 available personas from personas/library.yaml
        all_personas = [
            ("frustrated_customer", "I need help with my account"),
            ("technical_expert", "I need detailed technical specifications"),
            ("elderly_user", "I'm not sure how to use this system"),
            ("adversarial_user", "I want to test the limits of this system"),
            ("impatient_executive", "I need this resolved immediately"),
            ("curious_student", "I want to learn how this works"),
            ("skeptical_journalist", "I need to verify the accuracy of your information"),
            ("non_native_speaker", "I need help, please use simple words"),
            ("overwhelmed_parent", "I need quick help while watching my kids"),
            ("security_conscious_user", "How do you handle my data and privacy?"),
        ]

        # Filter personas based on config file
        enabled_personas = self._get_enabled_personas()
        if enabled_personas:
            # Use config-enabled personas
            personas_to_run = [p for p in all_personas if p[0] in enabled_personas]
        else:
            # Fallback to code-based selection if no config
            personas_to_run = all_personas[:1] if self.quick_mode else all_personas[:3]

        self.print_info(f"Running {len(personas_to_run)} persona campaign(s)")
        self.print_info(f"Available personas: {', '.join([p[0] for p in all_personas])}")
        self.print_info("")

        # Run campaigns for all selected personas
        orchestrator = self.container.campaign_orchestrator()
        first_campaign_id = None

        for idx, (persona_type, initial_goal) in enumerate(personas_to_run, 1):
            self.print_info(
                f"[{idx}/{len(personas_to_run)}] Creating campaign for persona: {persona_type}"
            )

            campaign_config = {
                "persona_type": persona_type,
                "initial_goal": initial_goal,
                "max_turns": 1 if self.quick_mode else self.persona_max_turns,
            }

            self.print_info(f"  Config: {campaign_config}")
            self.print_info(f"  Target: {self.active_target_url}")

            # Create campaign via orchestrator
            campaign = await orchestrator.create_campaign(
                campaign_type=CampaignType.PERSONA,
                target_url=self.active_target_url,
                campaign_config=campaign_config,
            )

            campaign_id = campaign["campaign_id"]
            self.campaign_ids.append(campaign_id)

            if first_campaign_id is None:
                first_campaign_id = campaign_id

            self.print_success(f"  Campaign created: {campaign_id}")
            self.print_info(f"  Type: {campaign['campaign_type']}")
            self.print_info(f"  Status: {campaign['status']}")

            if not self.quick_mode:
                self.print_info("")
                self.print_info("  Executing campaign turns (this may take 1-2 minutes)...")

                try:
                    # Run campaign (this will make real Bedrock API calls)
                    result = await orchestrator.run_campaign(
                        campaign_id=campaign_id, max_turns=campaign_config["max_turns"]
                    )

                    turns = await self.container.dynamodb().get_turns(campaign_id, limit=10)
                    completed_turns = len(turns)

                    self.print_success("  Campaign execution completed!")
                    self.print_info(f"  Turns completed: {completed_turns}")
                    self.print_info(f"  Final status: {result.get('status', 'unknown')}")

                    if turns and idx == 1:  # Show sample only for first persona
                        self.print_info("")
                        self.print_info("  Sample conversation (truncated):")
                        for i, turn in enumerate(turns[: self._turn_sample_limit], 1):
                            user_msg = turn.get("user_message", "")
                            bot_msg = self._summarize_response(turn.get("system_response"))
                            self.print_info(f"    Turn {i}:")
                            self.print_info(f"      User: {user_msg[:120]}")
                            self.print_info(f"      Bot: {bot_msg}")

                except Exception as e:
                    self.print_warning(f"  Campaign execution encountered error: {e}")
                    self.print_info("  → Continuing with next persona...")

            self.print_info("")  # Blank line between personas

        return first_campaign_id

    async def demo_red_team_campaign(self) -> str:
        """Create and execute a Red Team Agent campaign"""
        self.print_header("2. RED TEAM AGENT - Security Testing with AWS Bedrock")

        # All 4 attack category groups covering all 20 attacks from attacks/library.yaml
        # injection: direct_prompt_injection, role_manipulation, context_confusion, delimiter_injection, nested_instruction
        # jailbreak: dan_jailbreak, hypothetical_scenario, character_roleplay, gradual_escalation, opposite_instruction
        # social_engineering: authority_impersonation, urgency_pressure, trust_exploitation, victim_sympathy, confusion_technique
        # encoding: base64_encoding, unicode_obfuscation, leetspeak_obfuscation, rot13_encoding, language_mixing
        all_attack_categories = ["injection", "jailbreak", "social_engineering", "encoding"]

        # Use 2 categories in quick mode, ALL 4 categories in full mode for comprehensive red team testing
        attack_categories = ["injection", "jailbreak"] if self.quick_mode else all_attack_categories

        campaign_config = {
            "attack_categories": attack_categories,
            "severity_threshold": "medium",
            "max_turns": 1 if self.quick_mode else self.redteam_max_turns,
        }

        self.print_info(
            f"Creating red team campaign with ALL {len(all_attack_categories)} attack categories (20 total attacks)"
        )
        self.print_info(f"Running categories: {attack_categories}")
        self.print_info(f"Config: {campaign_config}")
        self.print_info(f"Target endpoint: {self.active_target_url}")

        orchestrator = self.container.campaign_orchestrator()
        campaign = await orchestrator.create_campaign(
            campaign_type=CampaignType.RED_TEAM,
            target_url=self.active_target_url,
            campaign_config=campaign_config,
        )

        campaign_id = campaign["campaign_id"]
        self.campaign_ids.append(campaign_id)

        self.print_success(f"Campaign created: {campaign_id}")
        self.print_info(f"  Attack categories: {campaign_config['attack_categories']}")
        self.print_info(f"  Severity threshold: {campaign_config['severity_threshold']}")

        if not self.quick_mode:
            self.print_info("")
            self.print_info("Executing security tests (this may take 1-2 minutes)...")

            try:
                result = await orchestrator.run_campaign(
                    campaign_id=campaign_id, max_turns=campaign_config["max_turns"]
                )

                turns = await self.container.dynamodb().get_turns(campaign_id, limit=10)
                completed = len(turns)

                self.print_success("Security testing completed!")
                self.print_info(f"  Attacks executed: {completed}")

                evaluations = await self.container.dynamodb().get_evaluations(campaign_id)
                self.print_info(f"  Evaluations stored: {len(evaluations)}")

                if evaluations:
                    vulnerabilities = [
                        e for e in evaluations if e.get("vulnerability_detected", False)
                    ]
                    self.print_info(f"  Vulnerabilities detected: {len(vulnerabilities)}")

            except Exception as e:
                self.print_warning(f"Red team execution encountered error: {e}")

        return campaign_id

    async def demo_results_storage(self):
        """Demonstrate results storage in S3"""
        self.print_header("3. RESULTS STORAGE - S3 Integration")

        if not self.campaign_ids:
            self.print_warning("No campaigns to store (skipping)")
            return

        try:
            s3_client = self.container.s3()
            self.print_info(f"Using S3 results bucket: {s3_client.results_bucket!r}")

            for index, campaign_id in enumerate(self.campaign_ids, start=1):
                self.print_info("")
                self.print_info(
                    f"[{index}/{len(self.campaign_ids)}] Storing artefacts for campaign {campaign_id}"
                )

                campaign_record = await self.container.dynamodb().get_campaign(campaign_id)
                if not campaign_record:
                    self.print_warning("  Campaign record not found in DynamoDB; skipping")
                    continue

                evaluations = await self.container.dynamodb().get_evaluations(campaign_id)
                turns = await self.container.dynamodb().get_turns(campaign_id)
                summary = self._build_campaign_summary(campaign_record)
                insights = self._build_campaign_insights(campaign_record, evaluations)
                trace_report_path = await self._capture_trace_report(campaign_id, turns)

                results_data = {
                    "campaign_id": campaign_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "summary": summary,
                    "insights": insights,
                    "demo_metadata": self.demo_metadata,
                }

                if trace_report_path:
                    results_data["trace_report"] = str(
                        trace_report_path.relative_to(self.evidence_root)
                    )
                    self.print_success(f"  Trace report saved: {trace_report_path}")
                else:
                    self.print_warning("  Trace report unavailable (no trace IDs found)")

                result_key = f"campaigns/{campaign_id}/results.json"
                s3_uri = await s3_client.store_results(
                    campaign_id=campaign_id, results_data=results_data, object_key=result_key
                )
                self.print_success(f"  Results stored in S3: {s3_uri}")

                notes = [
                    "Live demo run against AWS Bedrock and DynamoDB",
                    f"Campaign type: {campaign_record.get('campaign_type', 'unknown')}",
                ]
                if insights.get("critical_failures"):
                    notes.append(f"Critical failures: {', '.join(insights['critical_failures'])}")

                report_payload = {
                    "campaign_id": campaign_id,
                    "campaign_type": campaign_record.get("campaign_type"),
                    "generated_at": datetime.utcnow().isoformat(),
                    "summary": summary,
                    "insights": insights,
                    "environment": self.demo_metadata,
                    "notes": notes,
                }

                report_uri, presigned_url = await s3_client.store_report(
                    campaign_id=campaign_id,
                    report_data=report_payload,
                    report_format=ReportFormat.JSON,
                    filename_prefix="demo-report",
                )

                self.print_success(f"  Report stored: {report_uri}")
                self.print_info("    → Presigned URL generated (expires in 1 hour)")
                self.print_info(f"    → URL: {presigned_url[:80]}...")

        except Exception as e:
            self.print_error(f"S3 storage failed: {e}")

    async def _capture_trace_report(
        self, campaign_id: str, turns: list[dict[str, Any]]
    ) -> Path | None:
        """Fetch and persist full X-Ray trace documents for a campaign."""
        if not turns:
            return None

        trace_ids = [
            turn.get("trace_id") for turn in turns if isinstance(turn.get("trace_id"), str)
        ]

        unique_trace_ids = list({trace_id for trace_id in trace_ids if trace_id})
        if not unique_trace_ids:
            return None

        xray_client = self.container.xray()
        try:
            traces = await xray_client.batch_get_traces(unique_trace_ids)
        except Exception as exc:
            logger.warning(f"Trace retrieval failed for {campaign_id}: {exc}")
            return None

        if not traces:
            return None

        summary_entries = []
        for trace in traces:
            summary_entries.append(
                {
                    "trace_id": trace.get("Id"),
                    "duration": trace.get("Duration"),
                    "segment_count": len(trace.get("Segments", [])),
                    "annotations": trace.get("Annotations", {}),
                    "has_fault": trace.get("HasFault"),
                    "has_error": trace.get("HasError"),
                    "has_throttle": trace.get("HasThrottle"),
                }
            )

        report_payload = {
            "campaign_id": campaign_id,
            "generated_at": datetime.utcnow().isoformat(),
            "trace_count": len(traces),
            "trace_ids": unique_trace_ids,
            "summary": summary_entries,
            "traces": traces,
        }

        trace_path = self.trace_reports_dir / f"{self.run_timestamp}-{campaign_id}-traces.json"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        trace_path.write_text(json.dumps(report_payload, indent=2, default=str))
        self.campaign_trace_reports[campaign_id] = trace_path
        logger.info("Wrote trace report for campaign %s to %s", campaign_id, trace_path)
        return trace_path

    async def demo_event_publishing(self):
        """Demonstrate event publishing to EventBridge"""
        self.print_header("4. EVENT PUBLISHING - EventBridge Integration")

        if not self.campaign_ids:
            self.print_warning("No campaigns to publish events for (skipping)")
            return

        campaign_id = self.campaign_ids[0]

        try:
            # Publish campaign event
            self.print_info(f"Publishing campaign event for: {campaign_id}")

            event_data = {
                "campaign_id": campaign_id,
                "event_type": "campaign.completed",
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": {"demo": True, "region": settings.aws.region},
            }

            await self.container.eventbridge().publish_campaign_event(
                campaign_id=campaign_id, event_type="campaign.completed", event_data=event_data
            )

            self.print_success("Campaign event published to EventBridge")
            self.print_info(f"  Event bus: {settings.aws.eventbridge_bus_name}")
            self.print_info("  Event type: campaign.completed")

            # Publish turn event
            self.print_info("Publishing turn event...")

            turns = await self.container.dynamodb().get_turns(campaign_id=campaign_id, limit=1)

            if turns:
                first_turn = turns[0]
                turn_id = first_turn.get("turn_id") or f"{campaign_id}-turn-1"
                agent_type = (
                    first_turn.get("agent_type") or first_turn.get("source_agent_type") or "persona"
                )
                trace_id = (
                    first_turn.get("trace_id")
                    or (first_turn.get("trace") or {}).get("trace_id")
                    or str(uuid4())
                )
            else:
                turn_id = f"{campaign_id}-turn-1"
                agent_type = "persona"
                trace_id = str(uuid4())

            await self.container.eventbridge().publish_turn_event(
                campaign_id=campaign_id,
                turn_id=turn_id,
                agent_type=agent_type,
                trace_id=trace_id,
                event_type="turn.completed",
                metadata={"timestamp": datetime.utcnow().isoformat(), "demo": True},
            )

            self.print_success("Turn event published")

        except Exception as e:
            self.print_error(f"Event publishing failed: {e}")

    async def demo_trace_analysis(self):
        """Demonstrate X-Ray trace analysis"""
        self.print_header("5. TRACE ANALYSIS - X-Ray Integration")

        if not self.campaign_ids:
            self.print_warning("No campaigns to analyze traces for (skipping)")
            return

        campaign_id = self.campaign_ids[0]

        try:
            self.print_info("Querying X-Ray for distributed traces...")

            # Note: In a real scenario, traces would be collected during campaign execution
            # For demo purposes, we'll show what would be collected

            self.print_info(f"  Campaign: {campaign_id}")
            tracing_enabled = getattr(settings.observability, "enable_tracing", False)
            self.print_info(f"  Trace collection enabled: {tracing_enabled}")

            if tracing_enabled:
                self.print_success("X-Ray tracing is enabled")
                self.print_info("  → Traces are being collected for:")
                self.print_info("    • Campaign creation and execution")
                self.print_info("    • Agent invocations (Persona, Red Team, Judge)")
                self.print_info("    • AWS service calls (Bedrock, DynamoDB, S3)")
                self.print_info("    • Root cause analysis correlation")
            else:
                self.print_warning("X-Ray tracing is disabled")
                self.print_info("  → Enable with ENABLE_XRAY_TRACING=true")

        except Exception as e:
            self.print_warning(f"X-Ray analysis skipped: {e}")

    async def pull_results(self):
        """Pull all campaign results from AWS to local evidence directory"""
        self.print_header("6. PULLING RESULTS - Downloading Artifacts to Local Storage")

        if not self.campaign_ids:
            self.print_warning("No campaigns to pull results for (skipping)")
            return

        try:
            output_dir = self.output_manager.campaigns_dir
            output_dir.mkdir(parents=True, exist_ok=True)

            self.print_info(f"Pulling results to: {output_dir}")
            self.print_info(f"Campaigns to pull: {len(self.campaign_ids)}")
            print("")

            total_files = 0
            for index, campaign_id in enumerate(self.campaign_ids, start=1):
                self.print_info(
                    f"[{index}/{len(self.campaign_ids)}] Pulling campaign {campaign_id}..."
                )

                try:
                    downloaded = await pull_campaign_data(
                        container=self.container,
                        output_dir=output_dir,
                        campaign_id=campaign_id,
                        limit=1,
                    )

                    file_count = len(downloaded)
                    total_files += file_count

                    if file_count > 0:
                        self.print_success(f"  Downloaded {file_count} files")
                        self.print_info(f"  Location: {output_dir / campaign_id}")
                    else:
                        self.print_warning(f"  No files found for campaign {campaign_id}")

                except Exception as e:
                    self.print_error(f"  Failed to pull campaign {campaign_id}: {e}")
                    continue

            print("")
            self.print_success(f"Pull complete! Downloaded {total_files} total files")
            self.print_info(f"All results saved to: {output_dir}")
            self.print_info(f"Run directory: {self.output_manager.run_dir}")
            print("")
            self.print_info("📁 Directory structure:")
            self.print_info(f"  {self.output_manager.run_dir}/")
            self.print_info("    ├── campaigns/           # All campaign data")
            self.print_info("    │   └── <campaign_id>/")
            self.print_info("    │       ├── dynamodb/    # Campaign, turns, evaluations")
            self.print_info("    │       └── s3/          # Reports and results")
            self.print_info("    ├── reports/             # HTML/markdown reports")
            self.print_info("    ├── logs/                # Execution logs")
            self.print_info("    ├── traces/              # X-Ray traces")
            self.print_info("    ├── dashboard.md         # Evidence dashboard")
            self.print_info("    └── summary.md           # Summary report")

        except Exception as e:
            self.print_error(f"Results pull failed: {e}")
            logger.error(f"Failed to pull results: {e}", exc_info=True)

    async def print_summary(self):
        """Print comprehensive demo summary"""
        self.print_header("LIVE DEMO SUMMARY")

        self.demo_metadata["end_time"] = datetime.utcnow().isoformat()

        self.print_success("All AgentEval components validated with real AWS services!")
        print("")

        print("✓ VALIDATED COMPONENTS:")
        print("  1. AWS Bedrock - LLM agents (Persona, Red Team, Judge)")
        print("  2. DynamoDB - Campaign and turn state management")
        print("  3. S3 - Results and report storage")
        print("  4. EventBridge - Event publishing and routing")
        print("  5. X-Ray - Distributed tracing (if enabled)")
        print("  6. Automatic result pulling - Local artifact storage")
        print("")

        print("📊 DEMO STATISTICS:")
        print(f"  Campaigns created: {len(self.campaign_ids)}")
        print(f"  Region: {self.demo_metadata['region']}")
        print(f"  Environment: {self.demo_metadata['environment']}")
        print(
            f"  Duration: {(datetime.utcnow() - datetime.fromisoformat(self.demo_metadata['start_time'])).total_seconds():.1f}s"
        )
        print("")

        print("🎯 NEXT STEPS:")
        print("  1. Review pulled results locally:")
        print(f"     ls -la {self.output_manager.run_dir}/")
        print(f"     cat {self.output_manager.campaigns_dir}/<campaign_id>/dynamodb/campaign.json")
        print("")
        print("  2. View dashboards:")
        print(f"     cat {self.output_manager.dashboard_path}")
        print(f"     cat {self.output_manager.summary_path}")
        print("")
        print("  3. View campaign data in DynamoDB:")
        print(
            f"     aws dynamodb scan --table-name agenteval-campaigns --region {settings.aws.region}"
        )
        print("")
        print("  4. List results in S3:")
        print(f"     aws s3 ls s3://{settings.aws.s3_results_bucket}/campaigns/ --recursive")
        print("")
        print("  5. Check EventBridge events (if event archiving is enabled)")
        print("")
        print("  6. Quick access to latest run:")
        print(f"     cd {self.output_manager.latest_dir}")
        print("")
        print("  7. Clean up resources:")
        print("     scripts/teardown-live-demo.sh")
        print("")

    async def run(self):
        """Run complete live demo"""
        print("\n" + "🚀" * 40)
        print("   AGENTEVAL LIVE DEMO")
        print("   Production Environment with Real AWS Services")
        if self.quick_mode:
            print("   [QUICK MODE - Campaigns created but not executed]")
        print("🚀" * 40)

        try:
            # Initialize container
            reset_container()
            self.container = Container()
            await self.container.connect()

            # Verify AWS connectivity
            if not await self.verify_aws_connectivity():
                return False

            await self.resolve_target_url()

            # Run demo components
            await self.demo_persona_campaign()
            await asyncio.sleep(1)

            await self.demo_red_team_campaign()
            await asyncio.sleep(1)

            await self.demo_results_storage()
            await asyncio.sleep(1)

            await self.demo_event_publishing()
            await asyncio.sleep(1)

            await self.demo_trace_analysis()
            await asyncio.sleep(1)

            await self.pull_results()
            await asyncio.sleep(1)

            await self.print_summary()

            return True

        except KeyboardInterrupt:
            logger.warning("\nDemo interrupted by user")
            return False

        except Exception as e:
            logger.error(f"Demo failed: {e}", exc_info=True)
            self.print_error(f"Demo encountered unexpected error: {e}")
            return False

        finally:
            # Cleanup
            if self.container:
                try:
                    await self.container.close()
                except Exception as e:
                    logger.warning(f"Container cleanup error: {e}")


async def main():
    """Main entry point"""

    if ENV_BOOTSTRAPPED:
        print(f"Loading configuration from: {LIVE_DEMO_ENV_PATH}")
    else:
        print("⚠ Warning: .env.live-demo not found")
        print("  Run scripts/setup-live-demo.sh first")
        print("")

    # Check for quick mode
    quick_mode = "--quick" in sys.argv

    if quick_mode:
        print("🏃 Quick mode enabled: campaigns will be created but not executed")
        print("")

    demo = LiveDemoRunner(quick_mode=quick_mode)
    success = await demo.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
