"""
AgentEval Configuration Management

Centralized configuration using pydantic-settings for type safety and validation.
"""

from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AWSConfig(BaseSettings):
    """AWS Service Configuration"""

    region: str = Field(default="us-east-1", description="AWS region")
    profile: str | None = Field(default=None, description="AWS profile name")
    access_key_id: str | None = Field(default=None, description="AWS access key")
    secret_access_key: str | None = Field(default=None, description="AWS secret key")

    # Bedrock Model IDs
    bedrock_persona_model: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        description="Claude Haiku 4.5 model for persona agents",
    )
    bedrock_redteam_model: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        description="Claude Haiku 4.5 model for red team agents",
    )
    bedrock_judge_model: str = Field(
        default="us.amazon.nova-pro-v1:0", description="Nova Pro model for judge agents"
    )
    bedrock_persona_fallback_model: str | None = Field(
        default="amazon.titan-text-lite-v1",
        description="Optional fallback model for persona agents when the primary model requires an inference profile",
    )
    bedrock_redteam_fallback_model: str | None = Field(
        default="amazon.titan-text-lite-v1",
        description="Optional fallback model for red team agents",
    )
    bedrock_judge_fallback_model: str | None = Field(
        default="amazon.titan-text-express-v1",
        description="Optional fallback model for judge agents",
    )
    bedrock_persona_profile_arn: str | None = Field(
        default=None, description="Inference profile ARN for persona model (if required)"
    )
    bedrock_redteam_profile_arn: str | None = Field(
        default=None, description="Inference profile ARN for red team model (if required)"
    )
    bedrock_judge_profile_arn: str | None = Field(
        default=None, description="Inference profile ARN for judge model (if required)"
    )

    # DynamoDB Tables
    dynamodb_campaigns_table: str = Field(
        default="agenteval-campaigns", description="Campaigns table name"
    )
    dynamodb_turns_table: str = Field(
        default="agenteval-turns", description="Conversation turns table name"
    )
    dynamodb_evaluations_table: str = Field(
        default="agenteval-evaluations", description="Evaluations table name"
    )
    dynamodb_knowledge_base_table: str = Field(
        default="agenteval-attack-knowledge", description="Red team knowledge base table name"
    )

    # S3 Buckets
    s3_results_bucket: str = Field(
        default="agenteval-results", description="Results storage bucket"
    )
    s3_reports_bucket: str = Field(
        default="agenteval-reports", description="Reports storage bucket"
    )

    # EventBridge
    eventbridge_bus_name: str = Field(default="agenteval", description="EventBridge bus name")

    model_config = SettingsConfigDict(env_prefix="AWS_", case_sensitive=False, extra="ignore")

    def model_post_init(self, __context: Any) -> None:  # type: ignore[override]
        for attr in (
            "profile",
            "access_key_id",
            "secret_access_key",
            "bedrock_persona_profile_arn",
            "bedrock_redteam_profile_arn",
            "bedrock_judge_profile_arn",
        ):
            if getattr(self, attr) == "":
                setattr(self, attr, None)


class ObservabilityConfig(BaseSettings):
    """OpenTelemetry and X-Ray Configuration"""

    enable_tracing: bool = Field(default=True, description="Enable distributed tracing")
    otel_collector_endpoint: str = Field(
        default="http://localhost:4317", description="OpenTelemetry collector endpoint"
    )
    xray_daemon_address: str = Field(
        default="127.0.0.1:2000", description="AWS X-Ray daemon address"
    )
    trace_sample_rate: float = Field(
        default=1.0, description="Trace sampling rate (0.0-1.0)", ge=0.0, le=1.0
    )
    trace_cache_ttl_minutes: int = Field(default=5, description="Trace cache TTL in minutes")
    trace_retrieval_timeout_seconds: int = Field(
        default=10, description="Timeout for trace retrieval"
    )

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")


class ApplicationConfig(BaseSettings):
    """Application Configuration"""

    environment: str = Field(default="development", description="Environment name")
    log_level: str = Field(default="INFO", description="Logging level")
    api_base_url: str = Field(default="http://localhost:8000", description="API base URL")

    # Security Settings
    api_key_enabled: bool = Field(
        default=True, description="Enable API key authentication (always required in production)"
    )
    api_key: str | None = Field(
        default=None, description="API authentication key (required in production)"
    )
    secret_key: str = Field(default="change-me-in-production", description="Secret key for JWT")
    require_https_in_production: bool = Field(
        default=True, description="Require HTTPS in production"
    )

    # API Server Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port", ge=1, le=65535)
    api_workers: int = Field(default=4, description="Number of workers", ge=1)
    api_reload: bool = Field(default=False, description="Enable auto-reload")
    api_cors_origins: list = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins",
    )

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(
        default=100, description="Rate limit per minute", ge=1
    )
    rate_limit_burst: int = Field(default=20, description="Rate limit burst size", ge=1)

    # Campaign Configuration
    max_concurrent_campaigns: int = Field(default=100, description="Max concurrent campaigns", ge=1)
    max_concurrent_turns: int = Field(
        default=3, description="Max concurrent turns per campaign (for parallel execution)", ge=1
    )
    campaign_timeout_minutes: int = Field(
        default=60, description="Campaign timeout in minutes", ge=1
    )
    turn_timeout_seconds: int = Field(default=30, description="Turn timeout in seconds", ge=1)
    auto_pull_results_to_local: bool = Field(
        default=True,
        description="Automatically pull campaign results to local storage after completion",
    )
    local_results_output_dir: str = Field(
        default="outputs/campaigns",
        description="Local directory for pulled campaign results (legacy, use evidence_report_output_dir instead)",
    )
    auto_generate_dashboard: bool = Field(
        default=True, description="Automatically generate HTML dashboard after campaign completion"
    )
    dashboard_output_dir: str = Field(
        default="outputs/reports",
        description="Output directory for HTML dashboard files (legacy, managed by OutputManager)",
    )
    auto_generate_evidence_report: bool = Field(
        default=True,
        description="Automatically generate markdown evidence report after campaign completion",
    )
    evidence_report_output_dir: str = Field(
        default="outputs",
        description="Root directory for all evidence outputs (logs, reports, campaigns, traces)",
    )

    # Root Cause Analysis
    root_cause_confidence_threshold: float = Field(
        default=0.7, description="Minimum confidence for root cause", ge=0.0, le=1.0
    )

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class DemoConfig(BaseSettings):
    """Live demo specific configuration."""

    target_url: str = Field(
        default="https://postman-echo.com/post",
        description="Primary target endpoint exercised during the live demo",
    )
    fallback_target_url: str | None = Field(
        default="https://postman-echo.com/post",
        description="Fallback endpoint used when the primary target is unreachable",
    )
    persona_max_turns: int = Field(
        default=3, description="Default maximum turns for persona campaigns during live demo", ge=1
    )
    redteam_max_turns: int = Field(
        default=2, description="Default maximum turns for red team campaigns during live demo", ge=1
    )

    model_config = SettingsConfigDict(env_prefix="DEMO_", case_sensitive=False, extra="ignore")


class Settings:
    """Global Settings Container"""

    def __init__(self) -> None:
        self.aws = AWSConfig()
        self.observability = ObservabilityConfig()
        self.app = ApplicationConfig()
        self.demo = DemoConfig()

        # Security validation
        self._validate_security_settings()

    def _validate_security_settings(self) -> None:
        """Validate security-critical settings and warn about insecure defaults"""
        import logging

        logger = logging.getLogger(__name__)

        # CRITICAL: Check for default secret key in production
        if self.is_production and self.app.secret_key == "change-me-in-production":
            logger.critical(
                "SECURITY ERROR: Default secret key detected in production! "
                "Set SECRET_KEY environment variable immediately."
            )
            raise ValueError(
                "Cannot run in production with default secret key. "
                "Set SECRET_KEY environment variable."
            )

        # CRITICAL: Require API key in production
        if self.is_production:
            if not self.app.api_key_enabled:
                logger.critical(
                    "SECURITY ERROR: API key authentication is disabled in production! "
                    "Set API_KEY_ENABLED=true"
                )
                raise ValueError(
                    "Cannot run in production without API key authentication. "
                    "Set API_KEY_ENABLED=true"
                )

            if not self.app.api_key:
                logger.critical(
                    "SECURITY ERROR: No API key configured in production! "
                    "Set API_KEY environment variable."
                )
                raise ValueError(
                    "Cannot run in production without API key. Set API_KEY environment variable."
                )

            # Check API key strength (minimum 32 characters)
            if len(self.app.api_key) < 32:
                logger.critical(
                    "SECURITY ERROR: API key too short (minimum 32 characters required)! "
                    "Generate a strong API key."
                )
                raise ValueError("API key must be at least 32 characters long in production.")

            # Check for HTTPS requirement
            if self.app.require_https_in_production and not self.app.api_base_url.startswith(
                "https://"
            ):
                logger.warning(
                    "SECURITY WARNING: API base URL does not use HTTPS in production. "
                    "Set API_BASE_URL to use https://"
                )

        # Development/Test warnings
        if not self.is_production:
            if not self.app.api_key:
                logger.warning(
                    "API authentication disabled: No API_KEY configured. "
                    "Admin endpoints will be accessible without authentication. "
                    "This is acceptable in development but NEVER in production."
                )
            elif not self.app.api_key_enabled:
                logger.warning(
                    "API key authentication is explicitly disabled. "
                    "This should NEVER be done in production."
                )

            # Warn about default secret key in development
            if self.app.secret_key == "change-me-in-production":
                logger.warning(
                    "Using default secret key in development. "
                    "Set SECRET_KEY environment variable for production."
                )

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.app.environment.lower() in ("development", "dev")

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.app.environment.lower() in ("production", "prod")

    @property
    def api(self):
        """Convenience accessor for API settings"""

        class APISettings:
            def __init__(self, app_config):
                self.host = app_config.api_host
                self.port = app_config.api_port
                self.workers = app_config.api_workers
                self.reload = app_config.api_reload
                self.cors_origins = app_config.api_cors_origins

        return APISettings(self.app)


# Global settings instance
settings = Settings()
