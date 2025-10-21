"""
Campaign Orchestrator - Central Coordination System

Orchestrates complete evaluation campaigns:
1. Creates campaigns with configuration
2. Coordinates PersonaAgent, RedTeamAgent, JudgeAgent
3. Manages turn-by-turn interactions
4. Retrieves and analyzes traces (SECRET SAUCE)
5. Correlates evaluations with traces
6. Stores results and generates reports
7. Publishes lifecycle events

This is the "brain" that brings all components together.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import httpx

from agenteval.agents.judge_agent import JudgeAgent
from agenteval.agents.persona_agent import PersonaAgent
from agenteval.agents.redteam_agent import RedTeamAgent
from agenteval.analysis.correlation_engine import CorrelationEngine
from agenteval.analysis.trace_analyzer import TraceAnalyzer
from agenteval.aws.dynamodb import DynamoDBClient
from agenteval.aws.eventbridge import EventBridgeClient
from agenteval.aws.s3 import S3Client
from agenteval.aws.xray import XRayClient
from agenteval.config import settings
from agenteval.factories.judge_factory import JudgeAgentFactory
from agenteval.factories.persona_factory import PersonaAgentFactory
from agenteval.factories.redteam_factory import RedTeamAgentFactory
from agenteval.observability.tracer import (
    convert_otel_trace_id_to_xray,
    get_current_trace_id,
    get_current_xray_trace_id,
    inject_agentcore_headers,
    set_baggage,
    trace_operation,
)

logger = logging.getLogger(__name__)


class CampaignType(str, Enum):
    """Types of evaluation campaigns"""

    PERSONA = "persona"  # Persona-driven conversation testing
    RED_TEAM = "red_team"  # Security/adversarial testing
    COMBINED = "combined"  # Both persona and red team


class CampaignStatus(str, Enum):
    """Campaign lifecycle states"""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TurnStatus(str, Enum):
    """Turn execution states"""

    PENDING = "pending"
    EXECUTING = "executing"
    EVALUATED = "evaluated"
    ANALYZED = "analyzed"  # Trace analyzed and correlated
    COMPLETED = "completed"
    FAILED = "failed"


class CampaignOrchestrator:
    """
    Orchestrates evaluation campaigns

    Coordinates:
    - PersonaAgent or RedTeamAgent for input generation
    - Target system interaction
    - JudgeAgent for evaluation
    - TraceAnalyzer + CorrelationEngine for insights (SECRET SAUCE)
    """

    def __init__(
        self,
        dynamodb_client: DynamoDBClient | None = None,
        s3_client: S3Client | None = None,
        xray_client: XRayClient | None = None,
        eventbridge_client: EventBridgeClient | None = None,
        persona_factory: PersonaAgentFactory | None = None,
        redteam_factory: RedTeamAgentFactory | None = None,
        judge_factory: JudgeAgentFactory | None = None,
    ) -> None:
        """
        Initialize campaign orchestrator

        Args:
            dynamodb_client: DynamoDB client for state management
            s3_client: S3 client for results storage
            xray_client: X-Ray client for trace retrieval
            eventbridge_client: EventBridge client for events
            persona_factory: Factory for creating PersonaAgent instances
            redteam_factory: Factory for creating RedTeamAgent instances
            judge_factory: Factory for creating JudgeAgent instances
        """
        self.dynamodb = dynamodb_client or DynamoDBClient()
        self.s3 = s3_client or S3Client()
        self.xray = xray_client or XRayClient()
        self.eventbridge = eventbridge_client or EventBridgeClient()

        self.persona_factory = persona_factory or PersonaAgentFactory()
        self.redteam_factory = redteam_factory or RedTeamAgentFactory()
        self.judge_factory = judge_factory or JudgeAgentFactory()

        self.trace_analyzer = TraceAnalyzer()
        self.correlation_engine = CorrelationEngine()
        self._clients_connected = False

        # HTTP client for target system communication
        self._http_client: httpx.AsyncClient | None = None
        self._campaign_tasks: dict[str, asyncio.Task] = {}

        # Concurrency controls
        self._campaign_semaphore = asyncio.Semaphore(settings.app.max_concurrent_campaigns)
        self._turn_semaphore = asyncio.Semaphore(settings.app.max_concurrent_turns)

        logger.info(
            "CampaignOrchestrator initialized",
            extra={
                "max_concurrent_campaigns": settings.app.max_concurrent_campaigns,
                "max_concurrent_turns": settings.app.max_concurrent_turns,
            },
        )

    async def connect(self) -> None:
        """Connect all AWS clients and HTTP client"""
        if not self._clients_connected:
            await self.dynamodb.connect()
            await self.s3.connect()
            await self.xray.connect()
            await self.eventbridge.connect()

            # Initialize HTTP client with timeouts and tracing
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    timeout=float(settings.app.turn_timeout_seconds),
                    connect=5.0,
                    read=float(settings.app.turn_timeout_seconds),
                    write=5.0,
                    pool=5.0,
                ),
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )

            self._clients_connected = True
            logger.info("All AWS clients and HTTP client connected")

    async def close(self) -> None:
        """Close all AWS clients and HTTP client"""
        if self._clients_connected:
            await self.dynamodb.close()
            await self.s3.close()
            await self.xray.close()
            await self.eventbridge.close()

            if self._http_client:
                await self._http_client.aclose()
                self._http_client = None

            self._clients_connected = False
            logger.info("All AWS clients and HTTP client closed")

    async def __aenter__(self) -> "CampaignOrchestrator":
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        await self.close()

    async def _ensure_clients(self) -> None:
        """Ensure all dependent clients are ready."""
        await self.connect()

    def _track_task(self, campaign_id: str, task: asyncio.Task) -> None:
        """Track background tasks so they can be observed/cleaned up."""
        self._campaign_tasks[campaign_id] = task

        def _cleanup(_: asyncio.Task) -> None:
            self._campaign_tasks.pop(campaign_id, None)

        task.add_done_callback(_cleanup)

    async def create_campaign(
        self,
        campaign_type: CampaignType,
        target_url: str,
        campaign_config: dict[str, Any],
        campaign_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new evaluation campaign

        Args:
            campaign_type: Type of campaign
            target_url: URL of target system to evaluate
            campaign_config: Campaign configuration
            campaign_id: Optional campaign ID (auto-generated if not provided)

        Returns:
            Campaign metadata
        """
        campaign_id = campaign_id or str(uuid4())
        await self._ensure_clients()

        with trace_operation(
            "campaign_creation", campaign_id=campaign_id, campaign_type=campaign_type.value
        ):
            logger.info(
                f"Creating campaign: {campaign_id}",
                extra={
                    "campaign_id": campaign_id,
                    "type": campaign_type.value,
                    "target_url": target_url,
                },
            )

            # Validate configuration
            self._validate_campaign_config(campaign_type, campaign_config)

            # Create campaign metadata
            campaign_metadata = {
                "campaign_id": campaign_id,
                "campaign_type": campaign_type.value,
                "target_url": target_url,
                "status": CampaignStatus.CREATED.value,
                "config": campaign_config,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "stats": {
                    "total_turns": 0,
                    "completed_turns": 0,
                    "failed_turns": 0,
                    "avg_score": 0.0,
                },
            }

            # Store in DynamoDB
            await self.dynamodb.create_campaign(campaign_id=campaign_id, config=campaign_metadata)

            # Publish campaign created event
            await self.eventbridge.publish_campaign_event(
                event_type="Created",
                campaign_id=campaign_id,
                campaign_type=campaign_type.value,
                target_url=target_url,
            )

            logger.info(f"Campaign created: {campaign_id}")

            return campaign_metadata

    async def run_campaign(
        self, campaign_id: str, max_turns: int = 10, enable_parallel_turns: bool = False
    ) -> dict[str, Any]:
        """
        Execute a complete campaign with concurrency control

        Args:
            campaign_id: Campaign identifier
            max_turns: Maximum number of turns to execute
            enable_parallel_turns: Enable parallel turn execution (default: False for sequential)

        Returns:
            Campaign execution results

        Raises:
            asyncio.TimeoutError: If campaign exceeds timeout
            RuntimeError: If campaign execution fails
        """
        # Acquire campaign semaphore to limit concurrent campaigns
        async with self._campaign_semaphore:
            logger.info(
                f"Acquired campaign slot ({self._campaign_semaphore._value}/{settings.app.max_concurrent_campaigns} available)",
                extra={"campaign_id": campaign_id},
            )

            try:
                # Execute campaign with timeout
                timeout_seconds = settings.app.campaign_timeout_minutes * 60
                return await asyncio.wait_for(
                    self._execute_campaign_impl(campaign_id, max_turns, enable_parallel_turns),
                    timeout=timeout_seconds,
                )
            except TimeoutError:
                logger.error(
                    f"Campaign timed out after {settings.app.campaign_timeout_minutes} minutes",
                    extra={"campaign_id": campaign_id},
                )
                await self.dynamodb.update_campaign_status(
                    campaign_id=campaign_id, status=CampaignStatus.FAILED.value
                )
                raise
            except Exception as e:
                logger.error(
                    f"Campaign execution failed: {e}",
                    extra={"campaign_id": campaign_id},
                    exc_info=True,
                )
                await self.dynamodb.update_campaign_status(
                    campaign_id=campaign_id, status=CampaignStatus.FAILED.value
                )
                raise
            finally:
                logger.info("Released campaign slot", extra={"campaign_id": campaign_id})

    async def _execute_campaign_impl(
        self, campaign_id: str, max_turns: int, enable_parallel_turns: bool
    ) -> dict[str, Any]:
        """
        Internal campaign execution implementation

        Args:
            campaign_id: Campaign identifier
            max_turns: Maximum number of turns
            enable_parallel_turns: Enable parallel execution

        Returns:
            Campaign execution results
        """
        await self._ensure_clients()

        with trace_operation(
            "campaign_execution",
            campaign_id=campaign_id,
            max_turns=max_turns,
            parallel_turns=enable_parallel_turns,
        ):
            logger.info(
                f"Starting campaign execution: {campaign_id}",
                extra={
                    "campaign_id": campaign_id,
                    "max_turns": max_turns,
                    "parallel_turns": enable_parallel_turns,
                },
            )

            # Load campaign metadata
            campaign = await self.dynamodb.get_campaign(campaign_id)

            if not campaign:
                raise ValueError(f"Campaign not found: {campaign_id}")

            # Update status to running
            await self.dynamodb.update_campaign_status(
                campaign_id=campaign_id, status=CampaignStatus.RUNNING.value
            )

            # Initialize agents based on campaign type
            campaign_type = CampaignType(campaign["campaign_type"])
            config = campaign["config"]

            persona_agent = None
            redteam_agent = None

            if campaign_type == CampaignType.PERSONA:
                persona_agent = await self._create_persona_agent(config)
            elif campaign_type == CampaignType.RED_TEAM:
                redteam_agent = await self._create_redteam_agent(config)
            else:  # COMBINED
                # For combined, create both agents to alternate between them
                persona_agent = await self._create_persona_agent(config)
                redteam_agent = await self._create_redteam_agent(config)
                logger.info(
                    "Combined campaign initialized with both persona and red team agents",
                    extra={"campaign_id": campaign_id},
                )

            # Create judge agent using factory
            judge_agent = await self.judge_factory.create()

            # Execute turns (sequential or parallel based on config)
            if enable_parallel_turns:
                turn_results = await self._execute_turns_parallel(
                    campaign_id=campaign_id,
                    campaign=campaign,
                    campaign_type=campaign_type,
                    persona_agent=persona_agent,
                    redteam_agent=redteam_agent,
                    judge_agent=judge_agent,
                    max_turns=max_turns,
                )
            else:
                turn_results = await self._execute_turns_sequential(
                    campaign_id=campaign_id,
                    campaign=campaign,
                    campaign_type=campaign_type,
                    persona_agent=persona_agent,
                    redteam_agent=redteam_agent,
                    judge_agent=judge_agent,
                    max_turns=max_turns,
                )

            # Mark campaign as completed
            await self.dynamodb.update_campaign_status(
                campaign_id=campaign_id, status=CampaignStatus.COMPLETED.value
            )

            # Generate campaign report
            report = await self.generate_campaign_report(
                campaign_id=campaign_id, turn_results=turn_results
            )

            # Publish campaign completed event
            await self.eventbridge.publish_campaign_event(
                event_type="Completed",
                campaign_id=campaign_id,
                total_turns=len(turn_results),
                avg_score=report["aggregate_metrics"]["overall_score"],
            )

            logger.info(
                f"Campaign completed: {campaign_id}",
                extra={"campaign_id": campaign_id, "turns_completed": len(turn_results)},
            )

            # Auto-pull results to local storage if enabled
            if settings.app.auto_pull_results_to_local:
                try:
                    from pathlib import Path

                    from agenteval.reporting.pull import (  # Lazy import to avoid circular dependency
                        pull_campaign_data,
                    )
                    from agenteval.reporting.output_manager import get_output_manager

                    # Use OutputManager's campaigns directory for proper timestamped structure
                    output_manager = get_output_manager()
                    output_dir = output_manager.campaigns_dir
                    output_dir.mkdir(parents=True, exist_ok=True)

                    logger.info(
                        f"Auto-pulling campaign results to {output_dir}",
                        extra={"campaign_id": campaign_id},
                    )

                    # Create a temporary container with the same clients
                    from agenteval.container import Container

                    temp_container = Container()
                    temp_container._dynamodb = self.dynamodb
                    temp_container._s3 = self.s3

                    downloaded_files = await pull_campaign_data(
                        container=temp_container,
                        output_dir=output_dir,
                        campaign_id=campaign_id,
                        limit=1,
                    )

                    logger.info(
                        f"Auto-pulled {len(downloaded_files)} files to {output_dir / campaign_id}",
                        extra={"campaign_id": campaign_id, "file_count": len(downloaded_files)},
                    )

                    # Add pulled results location to report
                    report["local_results_path"] = str(output_dir / campaign_id)

                except Exception as e:
                    logger.warning(
                        f"Failed to auto-pull results (non-fatal): {e}",
                        extra={"campaign_id": campaign_id},
                        exc_info=True,
                    )
                    # Don't fail the campaign due to pull failure

            # Auto-generate dashboard if enabled
            if settings.app.auto_generate_dashboard:
                try:
                    from pathlib import Path

                    from agenteval.application.dashboard_service import (
                        DashboardConfig,
                        create_dashboard_service,
                    )
                    from agenteval.reporting.output_manager import get_output_manager

                    # Use OutputManager's run directory for proper timestamped structure
                    output_manager = get_output_manager()
                    dashboard_dir = output_manager.run_dir
                    dashboard_dir.mkdir(parents=True, exist_ok=True)

                    logger.info(
                        f"Auto-generating dashboard for campaign {campaign_id}",
                        extra={"campaign_id": campaign_id},
                    )

                    # Create dashboard service
                    # NOTE: Do NOT pass campaign_ids to scan ALL campaigns from DynamoDB
                    # This ensures the HTML dashboard shows all completed campaigns, not just this one
                    dashboard_config = DashboardConfig(
                        region=settings.aws.region,
                        environment=settings.app.environment,
                        output_dir=dashboard_dir,
                        generate_html=True,
                        generate_markdown=True,
                        campaign_ids=None,  # Scan all campaigns
                    )

                    dashboard_service = await create_dashboard_service(config=dashboard_config)

                    # Generate dashboard with all campaigns
                    dashboard_files = await dashboard_service.generate_dashboard(
                        campaign_ids=None  # Scan all campaigns
                    )

                    logger.info(
                        f"Auto-generated {len(dashboard_files)} dashboard files",
                        extra={
                            "campaign_id": campaign_id,
                            "file_count": len(dashboard_files),
                            "files": list(dashboard_files.keys()),
                        },
                    )

                    # Add dashboard locations to report
                    report["dashboard_files"] = {
                        name: str(path) for name, path in dashboard_files.items()
                    }
                    report["dashboard_path"] = str(dashboard_dir)

                except Exception as e:
                    logger.warning(
                        f"Failed to auto-generate dashboard (non-fatal): {e}",
                        extra={"campaign_id": campaign_id},
                        exc_info=True,
                    )
                    # Don't fail the campaign due to dashboard generation failure

            # Auto-generate markdown evidence report if enabled
            if settings.app.auto_generate_evidence_report:
                try:
                    from pathlib import Path

                    from agenteval.reporting.dashboard import (
                        collect_campaign_insights,
                        generate_live_demo_summary,
                    )
                    from agenteval.reporting.dashboard import (
                        generate_dashboard as generate_markdown_dashboard,
                    )

                    evidence_dir = Path(settings.app.evidence_report_output_dir).resolve()
                    evidence_dir.mkdir(parents=True, exist_ok=True)

                    # Use the pulled results directory as the campaigns directory
                    # Note: local_results_output_dir is already "outputs/campaigns"
                    campaigns_dir = Path(settings.app.local_results_output_dir).resolve()

                    logger.info(
                        f"Auto-generating markdown evidence report for campaign {campaign_id}",
                        extra={"campaign_id": campaign_id},
                    )

                    # Collect insights from pulled data
                    insights = collect_campaign_insights(campaigns_dir)

                    # Generate full markdown dashboard
                    dashboard_path = evidence_dir / "dashboard.md"
                    generate_markdown_dashboard(
                        campaigns_dir=campaigns_dir, output_path=dashboard_path, campaigns=insights
                    )

                    # Generate compact live demo summary
                    summary_path = evidence_dir / "live-demo-latest.md"
                    generate_live_demo_summary(
                        campaigns_dir=campaigns_dir, output_path=summary_path, campaigns=insights
                    )

                    logger.info(
                        "Auto-generated markdown evidence reports",
                        extra={
                            "campaign_id": campaign_id,
                            "dashboard": str(dashboard_path),
                            "summary": str(summary_path),
                        },
                    )

                    # Add evidence report locations to report
                    report["evidence_reports"] = {
                        "dashboard": str(dashboard_path),
                        "summary": str(summary_path),
                    }

                except Exception as e:
                    logger.warning(
                        f"Failed to auto-generate evidence report (non-fatal): {e}",
                        extra={"campaign_id": campaign_id},
                        exc_info=True,
                    )
                    # Don't fail the campaign due to evidence report generation failure

            return report

    async def execute_turn(
        self,
        campaign_id: str,
        turn_number: int,
        input_agent: Any,  # PersonaAgent or RedTeamAgent
        judge_agent: JudgeAgent,
        target_url: str,
    ) -> dict[str, Any]:
        """
        Execute a single turn of evaluation

        This is where the SECRET SAUCE happens:
        1. Generate input (persona or attack)
        2. Send to target system
        3. Evaluate response with JudgeAgent
        4. Retrieve trace from X-Ray
        5. Analyze trace
        6. Correlate evaluation with trace
        7. Store results

        Args:
            campaign_id: Campaign ID
            turn_number: Turn sequence number
            input_agent: Persona or Red Team agent
            judge_agent: Judge agent for evaluation
            target_url: Target system URL

        Returns:
            Turn execution result with correlation analysis
        """
        await self._ensure_clients()

        turn_id = f"{campaign_id}-turn-{turn_number}"

        # Determine agent type early for baggage propagation
        agent_descriptor = "persona" if isinstance(input_agent, PersonaAgent) else "red_team"
        agent_id = getattr(input_agent, "agent_id", None)

        # Set baggage for trace propagation
        set_baggage("campaign.id", campaign_id)
        set_baggage("turn.number", str(turn_number))
        set_baggage("agent.type", agent_descriptor)
        if agent_id:
            set_baggage("agent.id", agent_id)

        with trace_operation(
            "turn_execution",
            campaign_id=campaign_id,
            turn_number=turn_number,
            agent_type=agent_descriptor,
            agent_id=agent_id or "unknown",
        ) as span:
            logger.info(
                f"Executing turn {turn_number}",
                extra={"campaign_id": campaign_id, "turn": turn_number},
            )

            # Update turn status
            await self.dynamodb.save_turn(
                campaign_id=campaign_id,
                turn_id=turn_id,
                turn_data={
                    "status": TurnStatus.EXECUTING.value,
                    "started_at": datetime.utcnow().isoformat(),
                },
            )

            # Step 1: Generate input message
            if isinstance(input_agent, PersonaAgent):
                user_message = await input_agent.generate_message()
                agent_descriptor = "persona"
            else:  # RedTeamAgent
                attack = input_agent.select_attack()
                if attack:
                    user_message = attack.generate_payload()
                else:
                    user_message = "Test message"
                agent_descriptor = "red_team"

            span.set_attribute("user_message_length", len(user_message))

            # Step 2: Send to target system with full observability context
            system_response = await self._send_to_target(
                target_url=target_url,
                message=user_message,
                campaign_id=campaign_id,
                agent_id=agent_id,
                agent_type=agent_descriptor,
                turn_number=turn_number,
            )

            span.set_attribute("system_response_length", len(system_response))

            # Capture trace ID for this interaction (OpenTelemetry format for logging)
            otel_trace_id = get_current_trace_id()
            span.set_attribute("trace_id", otel_trace_id or "none")

            # Convert to X-Ray format for X-Ray API calls
            xray_trace_id = get_current_xray_trace_id() if otel_trace_id else None

            # Step 3: Evaluate response with JudgeAgent
            evaluation_result = await judge_agent.evaluate_response(
                user_message=user_message,
                system_response=system_response,
                context={
                    "campaign_id": campaign_id,
                    "turn_number": turn_number,
                    "trace_id": otel_trace_id,
                },
            )

            # Update persona memory state if using PersonaAgent
            if isinstance(input_agent, PersonaAgent):
                response_quality = evaluation_result["aggregate_scores"]["overall"]
                await input_agent.process_response(
                    user_message=user_message,
                    system_response=system_response,
                    turn_number=turn_number,
                    response_quality=response_quality,
                )
                logger.debug(
                    f"Updated persona memory after turn {turn_number}",
                    extra={
                        "campaign_id": campaign_id,
                        "turn_number": turn_number,
                        "frustration": input_agent.memory.state.frustration_level,
                        "goal_progress": input_agent.memory.state.goal_progress,
                    },
                )

            # Persist granular evaluation document for downstream analytics
            await self.dynamodb.save_evaluation(
                campaign_id=campaign_id, eval_id=turn_id, evaluation_data=evaluation_result
            )

            # Update turn status
            await self.dynamodb.update_turn_status(
                campaign_id=campaign_id, turn_id=turn_id, status=TurnStatus.EVALUATED.value
            )

            # Step 4: Retrieve and analyze trace (SECRET SAUCE)
            correlation_result = None

            if xray_trace_id:
                try:
                    # Retrieve trace from X-Ray (using X-Ray formatted trace ID)
                    trace_data = await self.xray.get_trace(xray_trace_id)

                    if trace_data:
                        # Analyze trace
                        trace_analysis = self.trace_analyzer.analyze_trace(trace_data)

                        # Extract insights
                        trace_insights = self.trace_analyzer.extract_trace_insights(trace_analysis)

                        # Correlate evaluation with trace (SECRET SAUCE!)
                        correlation_result = self.correlation_engine.correlate(
                            evaluation_results=evaluation_result,
                            trace_analysis=trace_analysis,
                            trace_insights=trace_insights,
                        )

                        span.set_attribute(
                            "correlation_confidence", correlation_result.overall_confidence
                        )
                        span.set_attribute("root_causes_found", len(correlation_result.root_causes))

                        # Update turn status
                        await self.dynamodb.update_turn_status(
                            campaign_id=campaign_id,
                            turn_id=turn_id,
                            status=TurnStatus.ANALYZED.value,
                        )

                except Exception as e:
                    logger.error(f"Trace analysis failed: {e}", exc_info=True)
                    # Continue without trace analysis

            # Step 5: Store complete turn result
            turn_result = {
                "turn_id": turn_id,
                "campaign_id": campaign_id,
                "turn_number": turn_number,
                "trace_id": otel_trace_id,  # Store OpenTelemetry trace ID for logging
                "agent_type": agent_descriptor,
                "user_message": user_message,
                "system_response": system_response,
                "evaluation": evaluation_result,
                "correlation": (
                    self._serialize_correlation_result(correlation_result)
                    if correlation_result
                    else None
                ),
                "completed_at": datetime.utcnow().isoformat(),
                "status": TurnStatus.COMPLETED.value,
            }

            # Add persona memory snapshot if using PersonaAgent
            if isinstance(input_agent, PersonaAgent):
                turn_result["persona_memory"] = input_agent.memory.to_dict()
                logger.debug(
                    f"Stored persona memory snapshot for turn {turn_number}",
                    extra={"campaign_id": campaign_id, "turn_number": turn_number},
                )

            # Save to DynamoDB
            await self.dynamodb.save_turn(
                campaign_id=campaign_id, turn_id=turn_id, turn_data=turn_result
            )

            # Publish turn completed event
            await self.eventbridge.publish_turn_event(
                campaign_id=campaign_id,
                turn_id=turn_id,
                agent_type=agent_descriptor,
                trace_id=otel_trace_id or "none",
                overall_score=evaluation_result["aggregate_scores"]["overall"],
                trace_analyzed=correlation_result is not None,
            )

            logger.info(
                f"Turn {turn_number} completed",
                extra={
                    "campaign_id": campaign_id,
                    "turn": turn_number,
                    "score": evaluation_result["aggregate_scores"]["overall"],
                },
            )

            return turn_result

    async def generate_campaign_report(
        self, campaign_id: str, turn_results: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Generate comprehensive campaign report

        Args:
            campaign_id: Campaign identifier
            turn_results: All turn results

        Returns:
            Comprehensive campaign report
        """
        await self._ensure_clients()

        with trace_operation("campaign_report_generation", campaign_id=campaign_id):
            logger.info(f"Generating report for campaign: {campaign_id}")

            # Calculate aggregate metrics
            all_scores = [
                turn["evaluation"]["aggregate_scores"]["overall"] for turn in turn_results
            ]

            quality_scores = [
                turn["evaluation"]["aggregate_scores"].get("quality", 0.0) for turn in turn_results
            ]

            safety_scores = [
                turn["evaluation"]["aggregate_scores"].get("safety", 0.0) for turn in turn_results
            ]

            # Collect all root causes
            all_root_causes = []
            for turn in turn_results:
                if turn.get("correlation") and turn["correlation"].get("root_causes"):
                    all_root_causes.extend(turn["correlation"]["root_causes"])

            # Group and prioritize root causes
            root_cause_summary = self._summarize_root_causes(all_root_causes)

            # Generate report
            report = {
                "campaign_id": campaign_id,
                "generated_at": datetime.utcnow().isoformat(),
                "aggregate_metrics": {
                    "overall_score": sum(all_scores) / len(all_scores) if all_scores else 0.0,
                    "quality_score": (
                        sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
                    ),
                    "safety_score": (
                        sum(safety_scores) / len(safety_scores) if safety_scores else 0.0
                    ),
                    "total_turns": len(turn_results),
                    "passing_turns": sum(
                        1 for turn in turn_results if turn["evaluation"]["pass_fail"]["all_passed"]
                    ),
                },
                "turn_results": turn_results,
                "root_cause_analysis": root_cause_summary,
                "recommendations": self._generate_campaign_recommendations(
                    turn_results, root_cause_summary
                ),
            }

            # Store report in S3
            report_key = (
                f"campaigns/{campaign_id}/report-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
            )
            await self.s3.store_results(
                campaign_id=campaign_id, results_data=report, object_key=report_key
            )

            logger.info(f"Report generated and stored: {report_key}")

            return report

    async def _send_to_target(
        self,
        target_url: str,
        message: str,
        campaign_id: str | None = None,
        agent_id: str | None = None,
        agent_type: str | None = None,
        turn_number: int | None = None,
    ) -> str:
        """
        Send message to target system with HTTP client

        Makes an actual HTTP POST request to the target system
        with proper timeouts, tracing headers, and error handling.
        Includes full AgentCore observability context for trace correlation.

        Args:
            target_url: Target system URL
            message: Message to send
            campaign_id: Campaign identifier for tracing
            agent_id: Agent identifier for tracing
            agent_type: Agent type (persona, red_team, judge)
            turn_number: Turn number for tracing

        Returns:
            System response text

        Raises:
            httpx.HTTPError: If request fails
            RuntimeError: If HTTP client not connected
        """
        if not self._http_client:
            raise RuntimeError("HTTP client not connected. Call connect() first.")

        logger.info(
            f"Sending message to {target_url}",
            extra={
                "target_url": target_url,
                "campaign_id": campaign_id,
                "agent_type": agent_type,
                "turn_number": turn_number,
            },
        )

        # Prepare headers with full AgentCore observability context
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AgentEval/1.0",
        }

        # Inject AgentCore headers (includes traceparent, baggage, X-Amzn-Trace-Id, etc.)
        headers = inject_agentcore_headers(
            headers=headers,
            campaign_id=campaign_id,
            agent_id=agent_id,
            agent_type=agent_type,
            turn_number=turn_number,
        )

        # Prepare request payload
        payload = {"message": message, "timestamp": datetime.utcnow().isoformat()}

        try:
            # Make HTTP POST request with timeout
            response = await self._http_client.post(target_url, json=payload, headers=headers)

            # Raise for HTTP errors (4xx, 5xx)
            response.raise_for_status()

            # Try to parse response as JSON and extract the message
            extracted = None
            try:
                response_data = response.json()
                if response_data is not None:
                    extracted = self._extract_response_message(response_data)
            except ValueError:
                # Not JSON, will use raw text below
                pass

            if extracted:
                # Check if the response is just echoing back the user message
                if extracted.strip().lower() == message.strip().lower():
                    logger.warning(
                        "Target system echoed user message verbatim",
                        extra={
                            "campaign_id": campaign_id,
                            "turn_number": turn_number,
                            "user_message": message[:100],
                        },
                    )
                    return f"(echo detected) {extracted.strip()}"
                return extracted

            # Fallback to raw response text when no structured message is found
            return response.text

        except httpx.TimeoutException as e:
            logger.error(f"Request to {target_url} timed out: {e}")
            raise RuntimeError(f"Target system timeout: {e}")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {target_url}: {e.response.status_code}")
            raise RuntimeError(f"Target system returned error: {e.response.status_code}")

        except httpx.RequestError as e:
            logger.error(f"Request error to {target_url}: {e}")
            raise RuntimeError(f"Failed to connect to target system: {e}")

    @staticmethod
    def _extract_response_message(payload: Any) -> str | None:
        """
        Attempt to pull a human-readable message from varied response shapes.

        Handles common echo/mock services that wrap the actual response text in
        `json`, `data`, or nested structures.
        """
        if isinstance(payload, str):
            candidate = payload.strip()
            return candidate or None

        if isinstance(payload, dict):
            # Primary keys to check for the actual response message
            # Added "reply" to support ChatResponse format from demo chatbot
            primary_keys = ("reply", "response", "message", "text", "content", "body")
            for key in primary_keys:
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            # Check nested structures for wrapped responses
            nested_keys = ("json", "data", "body", "results")
            for key in nested_keys:
                value = payload.get(key)
                extracted = CampaignOrchestrator._extract_response_message(value)
                if extracted:
                    return extracted

        if isinstance(payload, list):
            for item in payload:
                extracted = CampaignOrchestrator._extract_response_message(item)
                if extracted:
                    return extracted

        return None

    def _validate_campaign_config(
        self, campaign_type: CampaignType, config: dict[str, Any]
    ) -> None:
        """Validate campaign configuration"""
        if campaign_type == CampaignType.PERSONA:
            if "persona_type" not in config:
                raise ValueError("persona_type required for PERSONA campaign")

        elif campaign_type == CampaignType.RED_TEAM:
            if "attack_categories" not in config:
                logger.warning("No attack_categories specified, will use all")

    async def _create_persona_agent(self, config: dict[str, Any]) -> PersonaAgent:
        """Create and initialize persona agent from config using factory"""
        persona_config = {
            "persona_type": config.get("persona_type", "frustrated_customer"),
            "initial_goal": config.get("initial_goal", "Get help with my issue"),
        }
        return await self.persona_factory.create(persona_config)

    async def _create_redteam_agent(self, config: dict[str, Any]) -> RedTeamAgent:
        """Create and initialize red team agent from config using factory"""
        redteam_config = {
            "attack_categories": config.get("attack_categories"),
            "severity_threshold": config.get("severity_threshold"),
            "use_mutations": config.get("use_mutations", True),
        }
        return await self.redteam_factory.create(redteam_config)

    async def _execute_turns_sequential(
        self,
        campaign_id: str,
        campaign: dict[str, Any],
        campaign_type: CampaignType,
        persona_agent: PersonaAgent | None,
        redteam_agent: RedTeamAgent | None,
        judge_agent: JudgeAgent,
        max_turns: int,
    ) -> list[dict[str, Any]]:
        """
        Execute turns sequentially (one after another)

        Args:
            campaign_id: Campaign ID
            campaign: Campaign metadata
            campaign_type: Campaign type
            persona_agent: Persona agent (if any)
            redteam_agent: Red team agent (if any)
            judge_agent: Judge agent
            max_turns: Maximum turns

        Returns:
            List of turn results
        """
        turn_results = []
        config = campaign["config"]

        for turn_num in range(1, max_turns + 1):
            try:
                # Select agent for this turn
                if campaign_type == CampaignType.COMBINED:
                    input_agent = self._select_agent_for_turn(
                        turn_num, persona_agent, redteam_agent, config
                    )
                else:
                    input_agent = persona_agent or redteam_agent

                # Execute turn
                turn_result = await self.execute_turn(
                    campaign_id=campaign_id,
                    turn_number=turn_num,
                    input_agent=input_agent,
                    judge_agent=judge_agent,
                    target_url=campaign["target_url"],
                )
                turn_results.append(turn_result)

                # Update campaign stats
                await self._update_campaign_stats(campaign_id, turn_results)

            except Exception as e:
                logger.error(
                    f"Turn {turn_num} failed: {e}",
                    extra={"campaign_id": campaign_id, "turn": turn_num},
                    exc_info=True,
                )
                await self.dynamodb.update_turn_status(
                    campaign_id=campaign_id,
                    turn_id=f"{campaign_id}-turn-{turn_num}",
                    status=TurnStatus.FAILED.value,
                    error=str(e),
                )

        return turn_results

    async def _execute_turns_parallel(
        self,
        campaign_id: str,
        campaign: dict[str, Any],
        campaign_type: CampaignType,
        persona_agent: PersonaAgent | None,
        redteam_agent: RedTeamAgent | None,
        judge_agent: JudgeAgent,
        max_turns: int,
    ) -> list[dict[str, Any]]:
        """
        Execute turns in parallel with bounded concurrency

        Uses semaphore to limit concurrent turn execution.
        Collects all results and sorts by turn number.

        Args:
            campaign_id: Campaign ID
            campaign: Campaign metadata
            campaign_type: Campaign type
            persona_agent: Persona agent (if any)
            redteam_agent: Red team agent (if any)
            judge_agent: Judge agent
            max_turns: Maximum turns

        Returns:
            List of turn results (sorted by turn number)
        """
        config = campaign["config"]
        turn_results = []

        async def execute_turn_with_semaphore(turn_num: int) -> dict[str, Any]:
            """Execute a single turn with semaphore control"""
            async with self._turn_semaphore:
                logger.debug(
                    f"Acquired turn slot for turn {turn_num} "
                    f"({self._turn_semaphore._value}/{settings.app.max_concurrent_turns} available)",
                    extra={"campaign_id": campaign_id, "turn": turn_num},
                )

                try:
                    # Select agent for this turn
                    if campaign_type == CampaignType.COMBINED:
                        input_agent = self._select_agent_for_turn(
                            turn_num, persona_agent, redteam_agent, config
                        )
                    else:
                        input_agent = persona_agent or redteam_agent

                    # Execute turn
                    turn_result = await self.execute_turn(
                        campaign_id=campaign_id,
                        turn_number=turn_num,
                        input_agent=input_agent,
                        judge_agent=judge_agent,
                        target_url=campaign["target_url"],
                    )

                    logger.debug(
                        f"Released turn slot for turn {turn_num}",
                        extra={"campaign_id": campaign_id, "turn": turn_num},
                    )

                    return turn_result

                except Exception as e:
                    logger.error(
                        f"Turn {turn_num} failed: {e}",
                        extra={"campaign_id": campaign_id, "turn": turn_num},
                        exc_info=True,
                    )
                    await self.dynamodb.update_turn_status(
                        campaign_id=campaign_id,
                        turn_id=f"{campaign_id}-turn-{turn_num}",
                        status=TurnStatus.FAILED.value,
                        error=str(e),
                    )
                    raise

        # Create all turn tasks
        turn_tasks = [execute_turn_with_semaphore(turn_num) for turn_num in range(1, max_turns + 1)]

        # Execute all turns concurrently (bounded by semaphore)
        logger.info(
            f"Executing {max_turns} turns in parallel (max {settings.app.max_concurrent_turns} concurrent)",
            extra={"campaign_id": campaign_id},
        )

        # Gather results (return_exceptions=True to collect partial results)
        results = await asyncio.gather(*turn_tasks, return_exceptions=True)

        # Filter out exceptions and collect successful results
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Turn {idx + 1} raised exception during parallel execution",
                    extra={"campaign_id": campaign_id, "exception": str(result)},
                )
            else:
                turn_results.append(result)

        # Sort by turn number to maintain order
        turn_results.sort(key=lambda x: x["turn_number"])

        # Update campaign stats with all results
        if turn_results:
            await self._update_campaign_stats(campaign_id, turn_results)

        logger.info(
            f"Parallel turn execution completed: {len(turn_results)}/{max_turns} succeeded",
            extra={"campaign_id": campaign_id},
        )

        return turn_results

    def _select_agent_for_turn(
        self,
        turn_number: int,
        persona_agent: PersonaAgent,
        redteam_agent: RedTeamAgent,
        config: dict[str, Any],
    ) -> Any:
        """
        Select which agent to use for a given turn in COMBINED campaigns

        Args:
            turn_number: Current turn number (1-indexed)
            persona_agent: Persona agent instance
            redteam_agent: Red team agent instance
            config: Campaign configuration

        Returns:
            The agent to use for this turn
        """
        # Get alternation strategy from config (default: round-robin)
        strategy = config.get("combined_strategy", "round_robin")

        if strategy == "round_robin":
            # Alternate between persona and red team (odd=persona, even=red_team)
            if turn_number % 2 == 1:
                logger.debug(f"Turn {turn_number}: Using persona agent")
                return persona_agent
            else:
                logger.debug(f"Turn {turn_number}: Using red team agent")
                return redteam_agent

        elif strategy == "persona_first":
            # Run persona for first N turns, then red team
            persona_turns = config.get("persona_turns", 5)
            if turn_number <= persona_turns:
                logger.debug(f"Turn {turn_number}: Using persona agent (persona_first strategy)")
                return persona_agent
            else:
                logger.debug(f"Turn {turn_number}: Using red team agent (persona_first strategy)")
                return redteam_agent

        elif strategy == "weighted":
            # Weighted selection (e.g., 70% persona, 30% red team)
            import random

            persona_weight = config.get("persona_weight", 0.7)
            if random.random() < persona_weight:
                logger.debug(f"Turn {turn_number}: Using persona agent (weighted strategy)")
                return persona_agent
            else:
                logger.debug(f"Turn {turn_number}: Using red team agent (weighted strategy)")
                return redteam_agent

        else:
            # Default to round-robin if strategy unknown
            logger.warning(f"Unknown combined_strategy '{strategy}', defaulting to round_robin")
            return persona_agent if turn_number % 2 == 1 else redteam_agent

    async def _update_campaign_stats(
        self, campaign_id: str, turn_results: list[dict[str, Any]]
    ) -> None:
        """Update campaign statistics"""
        stats = {
            "total_turns": len(turn_results),
            "completed_turns": sum(
                1 for t in turn_results if t["status"] == TurnStatus.COMPLETED.value
            ),
            "failed_turns": sum(1 for t in turn_results if t["status"] == TurnStatus.FAILED.value),
            "avg_score": (
                sum(t["evaluation"]["aggregate_scores"]["overall"] for t in turn_results)
                / len(turn_results)
                if turn_results
                else 0.0
            ),
        }

        await self.dynamodb.update_campaign_stats(campaign_id, stats)

    def _serialize_correlation_result(self, correlation_result: Any) -> dict[str, Any]:
        """Serialize correlation result for storage"""
        return {
            "trace_id": correlation_result.trace_id,
            "overall_confidence": correlation_result.overall_confidence,
            "correlations": [
                {
                    "metric_type": c.metric_type.value,
                    "correlation_type": c.correlation_type.value,
                    "confidence": c.confidence,
                    "impact": c.impact,
                    "explanation": c.explanation,
                }
                for c in correlation_result.correlations
            ],
            "root_causes": [
                {
                    "issue": rc.issue,
                    "severity": rc.severity,
                    "affected_metrics": [m.value for m in rc.affected_metrics],
                    "recommendations": rc.recommendations,
                }
                for rc in correlation_result.root_causes
            ],
            "recommendations": correlation_result.recommendations,
        }

    def _summarize_root_causes(self, all_root_causes: list[dict[str, Any]]) -> dict[str, Any]:
        """Summarize root causes across all turns"""
        if not all_root_causes:
            return {"total": 0, "by_issue": {}, "top_recommendations": []}

        # Group by issue
        by_issue = {}
        for rc in all_root_causes:
            issue = rc["issue"]
            if issue not in by_issue:
                by_issue[issue] = {"count": 0, "avg_severity": 0.0, "recommendations": set()}

            by_issue[issue]["count"] += 1
            by_issue[issue]["avg_severity"] += rc["severity"]
            by_issue[issue]["recommendations"].update(rc["recommendations"])

        # Calculate averages
        for issue_data in by_issue.values():
            issue_data["avg_severity"] /= issue_data["count"]
            issue_data["recommendations"] = list(issue_data["recommendations"])

        # Get top recommendations
        all_recommendations = []
        for rc in all_root_causes:
            all_recommendations.extend(rc["recommendations"])

        from collections import Counter

        top_recommendations = [
            {"recommendation": rec, "frequency": count}
            for rec, count in Counter(all_recommendations).most_common(5)
        ]

        return {
            "total": len(all_root_causes),
            "by_issue": by_issue,
            "top_recommendations": top_recommendations,
        }

    def _generate_campaign_recommendations(
        self, turn_results: list[dict[str, Any]], root_cause_summary: dict[str, Any]
    ) -> list[str]:
        """Generate high-level campaign recommendations"""
        recommendations = []

        # Average score recommendations
        overall_scores = [
            turn.get("evaluation", {}).get("aggregate_scores", {}).get("overall")
            for turn in turn_results
        ]
        overall_scores = [score for score in overall_scores if isinstance(score, (int, float))]

        if overall_scores:
            avg_score = sum(overall_scores) / len(overall_scores)

            if avg_score < 0.6:
                recommendations.append(
                    "CRITICAL: Overall quality is low (< 0.6). Immediate attention required."
                )
            elif avg_score < 0.75:
                recommendations.append(
                    "WARNING: Overall quality is below target (< 0.75). Improvement needed."
                )
        else:
            recommendations.append(
                "INFO: No completed turns available to compute overall quality score."
            )

        # Add top recommendations from root cause analysis
        top_recs = root_cause_summary.get("top_recommendations", [])
        for rec_data in top_recs[:3]:
            recommendations.append(f"[{rec_data['frequency']}x] {rec_data['recommendation']}")

        return recommendations
