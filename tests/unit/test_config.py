"""
Unit tests for Configuration Module.

Tests configuration validation and security checks.
"""

from unittest.mock import patch

import pytest

from agenteval.config import AWSConfig, Settings


class TestAWSConfigPostInit:
    """Test suite for AWS config post-initialization"""

    def test_empty_string_converts_to_none(self):
        """Test that empty strings are converted to None"""
        # Create config with empty strings
        config = AWSConfig(profile="", access_key_id="", secret_access_key="")

        # Verify empty strings converted to None
        assert config.profile is None
        assert config.access_key_id is None
        assert config.secret_access_key is None

    def test_empty_profile_arn_converts_to_none(self):
        """Test that empty profile ARNs are converted to None"""
        config = AWSConfig(
            bedrock_persona_profile_arn="",
            bedrock_redteam_profile_arn="",
            bedrock_judge_profile_arn="",
        )

        assert config.bedrock_persona_profile_arn is None
        assert config.bedrock_redteam_profile_arn is None
        assert config.bedrock_judge_profile_arn is None

    def test_non_empty_values_preserved(self):
        """Test that non-empty values are preserved"""
        config = AWSConfig(profile="my-profile", access_key_id="AKIA...", region="us-west-2")

        assert config.profile == "my-profile"
        assert config.access_key_id == "AKIA..."
        assert config.region == "us-west-2"


class TestSecurityValidationProduction:
    """Test suite for production security validations"""

    @patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "change-me-in-production",
            "API_KEY_ENABLED": "true",
            "API_KEY": "my-strong-api-key-with-at-least-32-characters-abc123",
        },
        clear=False,
    )
    def test_production_requires_non_default_secret_key(self):
        """Test that production mode rejects default secret key"""
        with pytest.raises(ValueError, match="Cannot run in production with default secret key"):
            Settings()

    @patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "my-secure-secret-key-at-least-32-chars-long-12345",
        },
        clear=False,
    )
    def test_production_requires_api_key_enabled(self):
        """Test that production requires API key authentication"""
        with patch.dict("os.environ", {"API_KEY_ENABLED": "false"}), pytest.raises(
            ValueError, match="Cannot run in production without API key authentication"
        ):
            Settings()

    @patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "my-secure-secret-key-at-least-32-chars-long-12345",
            "API_KEY_ENABLED": "true",
            "API_KEY": "",
        },
        clear=True,
    )
    def test_production_requires_api_key(self):
        """Test that production requires API key to be set"""
        with pytest.raises(ValueError, match="Cannot run in production without API key"):
            Settings()

    @patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "my-secure-secret-key-at-least-32-chars-long-12345",
            "API_KEY_ENABLED": "true",
            "API_KEY": "short",
        },
        clear=False,
    )
    def test_production_requires_strong_api_key(self):
        """Test that production requires API key of minimum length"""
        with pytest.raises(ValueError, match="API key must be at least 32 characters"):
            Settings()

    @patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "my-secure-secret-key-at-least-32-chars-long-12345",
            "API_KEY_ENABLED": "true",
            "API_KEY": "my-strong-api-key-with-at-least-32-characters-abc123",
            "API_BASE_URL": "http://example.com",
            "REQUIRE_HTTPS_IN_PRODUCTION": "true",
        },
        clear=False,
    )
    def test_production_warns_about_http(self, caplog):
        """Test that production warns when using HTTP instead of HTTPS"""
        import logging

        with caplog.at_level(logging.WARNING):
            settings = Settings()

            assert "SECURITY WARNING: API base URL does not use HTTPS" in caplog.text

    @patch.dict(
        "os.environ",
        {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "my-secure-secret-key-at-least-32-chars-long-12345",
            "API_KEY_ENABLED": "true",
            "API_KEY": "my-strong-api-key-with-at-least-32-characters-abc123",
            "API_BASE_URL": "https://example.com",
        },
        clear=False,
    )
    def test_production_valid_config_succeeds(self):
        """Test that valid production config works"""
        settings = Settings()

        assert settings.is_production is True
        assert settings.app.api_key_enabled is True
        assert len(settings.app.api_key) >= 32
        assert settings.app.api_base_url.startswith("https://")


class TestSecurityValidationDevelopment:
    """Test suite for development security warnings"""

    @patch.dict("os.environ", {"ENVIRONMENT": "development"}, clear=False)
    def test_development_warns_no_api_key(self, caplog):
        """Test that development warns when API key is not configured"""
        import logging

        # Clear API_KEY if it exists
        with patch.dict("os.environ", {"API_KEY": ""}, clear=False):
            with caplog.at_level(logging.WARNING):
                Settings()

        # Should log warning about no API key
        assert any("API authentication disabled" in record.message for record in caplog.records)

    @patch.dict(
        "os.environ",
        {"ENVIRONMENT": "development", "SECRET_KEY": "change-me-in-production"},
        clear=False,
    )
    def test_development_allows_default_secret_key(self):
        """Test that development mode allows default secret key"""
        settings = Settings()

        # Should not raise, just allow it
        assert settings.app.secret_key == "change-me-in-production"
        assert settings.is_production is False

    @patch.dict("os.environ", {"ENVIRONMENT": "test", "API_KEY_ENABLED": "false"}, clear=False)
    def test_test_allows_disabled_api_key(self):
        """Test that test mode allows disabled API key"""
        settings = Settings()

        assert settings.is_production is False
        # In test mode, we can disable API key
        # (though the warning still fires)


class TestConfigDefaults:
    """Test suite for configuration defaults"""

    def test_aws_config_defaults(self):
        """Test AWS config has sensible defaults"""
        with patch.dict(
            "os.environ",
            {
                "AWS_PROFILE": "",
                "AWS_ACCESS_KEY_ID": "",
                "AWS_SECRET_ACCESS_KEY": "",
                "AWS_REGION": "us-east-1",
                "AWS_DYNAMODB_CAMPAIGNS_TABLE": "agenteval-campaigns",
                "AWS_S3_RESULTS_BUCKET": "agenteval-results",
                "AWS_S3_REPORTS_BUCKET": "agenteval-reports",
            },
            clear=False,
        ):
            config = AWSConfig()

        assert config.region == "us-east-1"
        assert config.profile is None
        assert config.dynamodb_campaigns_table == "agenteval-campaigns"
        assert config.s3_results_bucket == "agenteval-results"

    @patch.dict("os.environ", {"ENVIRONMENT": "test"}, clear=False)
    def test_settings_initialization(self):
        """Test Settings initializes all sub-configs"""
        settings = Settings()

        assert settings.aws is not None
        assert settings.observability is not None
        assert settings.app is not None
        assert settings.demo is not None


# Import os for environment manipulation
