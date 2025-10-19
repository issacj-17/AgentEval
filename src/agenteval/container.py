"""
Dependency Injection Container

Provides centralized dependency management and lifecycle control.
Uses factory functions for lazy initialization.

This container follows the Service Locator pattern with managed lifecycles.
"""

import logging
from contextlib import asynccontextmanager

from agenteval.analysis.correlation_engine import CorrelationEngine
from agenteval.analysis.trace_analyzer import TraceAnalyzer
from agenteval.application.campaign_service import CampaignService
from agenteval.application.report_service import ReportService
from agenteval.aws.dynamodb import DynamoDBClient
from agenteval.aws.eventbridge import EventBridgeClient
from agenteval.aws.s3 import S3Client
from agenteval.aws.xray import XRayClient
from agenteval.config import settings
from agenteval.factories.judge_factory import JudgeAgentFactory
from agenteval.factories.persona_factory import PersonaAgentFactory
from agenteval.factories.redteam_factory import RedTeamAgentFactory
from agenteval.orchestration.campaign import CampaignOrchestrator

logger = logging.getLogger(__name__)


class Container:
    """
    Dependency Injection Container

    Manages singleton instances and provides factory methods.
    Handles lifecycle (connect/close) for all managed dependencies.

    Design Philosophy:
    - Lazy initialization: Dependencies created on first access
    - Singleton pattern: One instance per container
    - Managed lifecycle: Connect on startup, close on shutdown
    - Testability: Reset method for test isolation
    """

    def __init__(self):
        # Infrastructure clients (singletons within container)
        self._dynamodb: DynamoDBClient | None = None
        self._s3: S3Client | None = None
        self._xray: XRayClient | None = None
        self._eventbridge: EventBridgeClient | None = None

        # Analysis engines (stateless, can be singletons)
        self._trace_analyzer: TraceAnalyzer | None = None
        self._correlation_engine: CorrelationEngine | None = None

        # Orchestration
        self._campaign_orchestrator: CampaignOrchestrator | None = None

        # Application Services
        self._campaign_service: CampaignService | None = None
        self._report_service: ReportService | None = None

        # Agent Factories
        self._persona_factory: PersonaAgentFactory | None = None
        self._redteam_factory: RedTeamAgentFactory | None = None
        self._judge_factory: JudgeAgentFactory | None = None

        # Connection state
        self._connected = False

        logger.info("DI Container initialized")

    # ========================================================================
    # Infrastructure Layer Factories
    # ========================================================================

    def dynamodb(self) -> DynamoDBClient:
        """
        Get or create DynamoDB client singleton

        Returns:
            DynamoDBClient instance
        """
        if self._dynamodb is None:
            self._dynamodb = DynamoDBClient(
                region=settings.aws.region,
                profile=settings.aws.profile,
                access_key_id=settings.aws.access_key_id,
                secret_access_key=settings.aws.secret_access_key,
                campaigns_table=settings.aws.dynamodb_campaigns_table,
                turns_table=settings.aws.dynamodb_turns_table,
                evaluations_table=settings.aws.dynamodb_evaluations_table,
                knowledge_base_table=settings.aws.dynamodb_knowledge_base_table,
            )
            logger.debug("Created DynamoDB client via DI container")
        return self._dynamodb

    def s3(self) -> S3Client:
        """
        Get or create S3 client singleton

        Returns:
            S3Client instance
        """
        if self._s3 is None:
            self._s3 = S3Client(
                region=settings.aws.region,
                profile=settings.aws.profile,
                access_key_id=settings.aws.access_key_id,
                secret_access_key=settings.aws.secret_access_key,
                results_bucket=settings.aws.s3_results_bucket,
                reports_bucket=settings.aws.s3_reports_bucket,
            )
            logger.debug("Created S3 client via DI container")
        return self._s3

    def xray(self) -> XRayClient:
        """
        Get or create X-Ray client singleton

        Returns:
            XRayClient instance
        """
        if self._xray is None:
            self._xray = XRayClient(
                region=settings.aws.region,
                profile=settings.aws.profile,
                access_key_id=settings.aws.access_key_id,
                secret_access_key=settings.aws.secret_access_key,
            )
            logger.debug(
                "Created X-Ray client via DI container", extra={"region": settings.aws.region}
            )
        return self._xray

    def eventbridge(self) -> EventBridgeClient:
        """
        Get or create EventBridge client singleton

        Returns:
            EventBridgeClient instance
        """
        if self._eventbridge is None:
            self._eventbridge = EventBridgeClient(
                region=settings.aws.region,
                profile=settings.aws.profile,
                access_key_id=settings.aws.access_key_id,
                secret_access_key=settings.aws.secret_access_key,
                bus_name=settings.aws.eventbridge_bus_name,
            )
            logger.debug(
                "Created EventBridge client via DI container",
                extra={
                    "region": settings.aws.region,
                    "bus_name": settings.aws.eventbridge_bus_name,
                },
            )
        return self._eventbridge

    # ========================================================================
    # Analysis Layer Factories
    # ========================================================================

    def trace_analyzer(self) -> TraceAnalyzer:
        """
        Get or create TraceAnalyzer singleton

        Returns:
            TraceAnalyzer instance
        """
        if self._trace_analyzer is None:
            self._trace_analyzer = TraceAnalyzer()
            logger.debug("Created TraceAnalyzer via DI container")
        return self._trace_analyzer

    def correlation_engine(self) -> CorrelationEngine:
        """
        Get or create CorrelationEngine singleton

        Returns:
            CorrelationEngine instance
        """
        if self._correlation_engine is None:
            self._correlation_engine = CorrelationEngine()
            logger.debug("Created CorrelationEngine via DI container")
        return self._correlation_engine

    # ========================================================================
    # Orchestration Layer Factories
    # ========================================================================

    def campaign_orchestrator(self) -> CampaignOrchestrator:
        """
        Get or create CampaignOrchestrator singleton

        The orchestrator is injected with all required AWS clients
        and agent factories from the container, ensuring proper
        lifecycle management and testability.

        Returns:
            CampaignOrchestrator instance
        """
        if self._campaign_orchestrator is None:
            self._campaign_orchestrator = CampaignOrchestrator(
                dynamodb_client=self.dynamodb(),
                s3_client=self.s3(),
                xray_client=self.xray(),
                eventbridge_client=self.eventbridge(),
                persona_factory=self.persona_factory(),
                redteam_factory=self.redteam_factory(),
                judge_factory=self.judge_factory(),
            )
            logger.debug("Created CampaignOrchestrator via DI container")
        return self._campaign_orchestrator

    # ========================================================================
    # Application Services Layer Factories
    # ========================================================================

    def campaign_service(self) -> CampaignService:
        """
        Get or create CampaignService singleton

        The service is injected with the orchestrator,
        encapsulating business logic for campaign operations.

        Returns:
            CampaignService instance
        """
        if self._campaign_service is None:
            self._campaign_service = CampaignService(orchestrator=self.campaign_orchestrator())
            logger.debug("Created CampaignService via DI container")
        return self._campaign_service

    def report_service(self) -> ReportService:
        """
        Get or create ReportService singleton

        The service is injected with orchestrator and S3 client,
        encapsulating business logic for report generation.

        Returns:
            ReportService instance
        """
        if self._report_service is None:
            self._report_service = ReportService(
                orchestrator=self.campaign_orchestrator(), s3_client=self.s3()
            )
            logger.debug("Created ReportService via DI container")
        return self._report_service

    # ========================================================================
    # Agent Factories Layer
    # ========================================================================

    def persona_factory(self) -> PersonaAgentFactory:
        """
        Get or create PersonaAgentFactory singleton

        Factory for creating PersonaAgent instances with
        proper configuration validation and initialization.

        Returns:
            PersonaAgentFactory instance
        """
        if self._persona_factory is None:
            self._persona_factory = PersonaAgentFactory()
            logger.debug("Created PersonaAgentFactory via DI container")
        return self._persona_factory

    def redteam_factory(self) -> RedTeamAgentFactory:
        """
        Get or create RedTeamAgentFactory singleton

        Factory for creating RedTeamAgent instances with
        attack category and severity threshold validation.

        Returns:
            RedTeamAgentFactory instance
        """
        if self._redteam_factory is None:
            self._redteam_factory = RedTeamAgentFactory()
            logger.debug("Created RedTeamAgentFactory via DI container")
        return self._redteam_factory

    def judge_factory(self) -> JudgeAgentFactory:
        """
        Get or create JudgeAgentFactory singleton

        Factory for creating JudgeAgent instances with
        minimal configuration requirements.

        Returns:
            JudgeAgentFactory instance
        """
        if self._judge_factory is None:
            self._judge_factory = JudgeAgentFactory()
            logger.debug("Created JudgeAgentFactory via DI container")
        return self._judge_factory

    # ========================================================================
    # Lifecycle Management
    # ========================================================================

    async def connect(self):
        """
        Connect all infrastructure clients

        This should be called on application startup.
        Idempotent - safe to call multiple times.
        """
        if not self._connected:
            logger.info("Connecting DI container dependencies...")

            # Connect infrastructure clients that have been created
            if self._dynamodb:
                await self._dynamodb.connect()
            if self._s3:
                await self._s3.connect()
            if self._xray:
                await self._xray.connect()
            if self._eventbridge:
                await self._eventbridge.connect()

            # Connect orchestrator if it's been created
            if self._campaign_orchestrator:
                await self._campaign_orchestrator.connect()

            self._connected = True
            logger.info(
                "DI container connected",
                extra={
                    "dynamodb_connected": self._dynamodb is not None,
                    "s3_connected": self._s3 is not None,
                    "xray_connected": self._xray is not None,
                    "eventbridge_connected": self._eventbridge is not None,
                },
            )

    async def close(self):
        """
        Close all infrastructure clients

        This should be called on application shutdown.
        Ensures graceful cleanup of connections.
        """
        if self._connected:
            logger.info("Closing DI container dependencies...")

            # Close orchestrator first if it's been created
            if self._campaign_orchestrator:
                await self._campaign_orchestrator.close()

            # Close infrastructure clients in reverse order
            if self._eventbridge:
                await self._eventbridge.close()
            if self._xray:
                await self._xray.close()
            if self._s3:
                await self._s3.close()
            if self._dynamodb:
                await self._dynamodb.close()

            self._connected = False
            logger.info("DI container closed")

    @asynccontextmanager
    async def managed(self):
        """
        Context manager for automatic lifecycle management

        Usage:
            async with container.managed():
                # Use container
                dynamodb = container.dynamodb()
                # ...
            # Automatically closed on exit

        Yields:
            Container instance
        """
        await self.connect()
        try:
            yield self
        finally:
            await self.close()

    def reset(self):
        """
        Reset container to initial state

        Used for test isolation. Clears all singleton instances
        and resets connection state.

        Warning: Should only be called in test environments!
        """
        logger.warning("Resetting DI container (test mode)")

        self._dynamodb = None
        self._s3 = None
        self._xray = None
        self._eventbridge = None
        self._trace_analyzer = None
        self._correlation_engine = None
        self._campaign_orchestrator = None
        self._campaign_service = None
        self._report_service = None
        self._persona_factory = None
        self._redteam_factory = None
        self._judge_factory = None
        self._connected = False

    def is_connected(self) -> bool:
        """
        Check if container is connected

        Returns:
            True if connected, False otherwise
        """
        return self._connected

    def __repr__(self) -> str:
        """String representation for debugging"""
        return (
            f"Container(connected={self._connected}, "
            f"clients_created={sum(1 for c in [self._dynamodb, self._s3, self._xray, self._eventbridge] if c is not None)})"
        )


# ============================================================================
# Global Container Instance
# ============================================================================

_container: Container | None = None


def get_container() -> Container:
    """
    Get global container instance

    Creates container on first access (lazy initialization).
    Subsequent calls return the same instance.

    Returns:
        Global Container instance
    """
    global _container
    if _container is None:
        _container = Container()
        logger.info("Global DI container instantiated")
    return _container


def reset_container():
    """
    Reset global container instance

    Used for test isolation. Creates a fresh container
    on next get_container() call.

    Warning: Should only be called in test environments!
    """
    global _container
    if _container is not None:
        _container.reset()
    _container = None
    logger.info("Global DI container reset")


# ============================================================================
# Convenience Functions for FastAPI Dependencies
# ============================================================================


async def get_dynamodb() -> DynamoDBClient:
    """
    FastAPI dependency for DynamoDB client

    Usage:
        @app.get("/campaigns")
        async def list_campaigns(db: DynamoDBClient = Depends(get_dynamodb)):
            campaigns = await db.list_campaigns()
            return campaigns

    Returns:
        DynamoDBClient from global container
    """
    return get_container().dynamodb()


async def get_s3() -> S3Client:
    """
    FastAPI dependency for S3 client

    Returns:
        S3Client from global container
    """
    return get_container().s3()


async def get_xray() -> XRayClient:
    """
    FastAPI dependency for X-Ray client

    Returns:
        XRayClient from global container
    """
    return get_container().xray()


async def get_eventbridge() -> EventBridgeClient:
    """
    FastAPI dependency for EventBridge client

    Returns:
        EventBridgeClient from global container
    """
    return get_container().eventbridge()


async def get_trace_analyzer() -> TraceAnalyzer:
    """
    FastAPI dependency for TraceAnalyzer

    Returns:
        TraceAnalyzer from global container
    """
    return get_container().trace_analyzer()


async def get_correlation_engine() -> CorrelationEngine:
    """
    FastAPI dependency for CorrelationEngine

    Returns:
        CorrelationEngine from global container
    """
    return get_container().correlation_engine()


async def get_campaign_orchestrator() -> CampaignOrchestrator:
    """
    FastAPI dependency for CampaignOrchestrator

    Returns:
        CampaignOrchestrator from global container
    """
    return get_container().campaign_orchestrator()


async def get_campaign_service() -> CampaignService:
    """
    FastAPI dependency for CampaignService

    Returns:
        CampaignService from global container
    """
    return get_container().campaign_service()


async def get_report_service() -> ReportService:
    """
    FastAPI dependency for ReportService

    Returns:
        ReportService from global container
    """
    return get_container().report_service()


async def get_persona_factory() -> PersonaAgentFactory:
    """
    FastAPI dependency for PersonaAgentFactory

    Returns:
        PersonaAgentFactory from global container
    """
    return get_container().persona_factory()


async def get_redteam_factory() -> RedTeamAgentFactory:
    """
    FastAPI dependency for RedTeamAgentFactory

    Returns:
        RedTeamAgentFactory from global container
    """
    return get_container().redteam_factory()


async def get_judge_factory() -> JudgeAgentFactory:
    """
    FastAPI dependency for JudgeAgentFactory

    Returns:
        JudgeAgentFactory from global container
    """
    return get_container().judge_factory()
