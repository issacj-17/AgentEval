"""
Unit tests for Health Check Endpoints

Tests the improved health checks with actual AWS connectivity verification.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status as http_status
from fastapi.testclient import TestClient

from agenteval.api.main import app


class TestBasicHealthCheck:
    """Test basic health check endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_health_check_returns_200(self, client):
        """Test that basic health check returns 200"""
        response = client.get("/api/v1/health")

        assert response.status_code == http_status.HTTP_200_OK

    def test_health_check_returns_correct_structure(self, client):
        """Test that health check returns expected fields"""
        response = client.get("/api/v1/health")
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "agenteval"
        assert "version" in data


class TestDetailedHealthCheck:
    """Test detailed health check with AWS connectivity"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_detailed_health_check_structure(self, client):
        """Test detailed health check returns expected structure"""
        # Note: This will actually try to connect to AWS
        # In a real environment with AWS credentials, this would work
        response = client.get("/api/v1/health/detailed")

        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "dependencies" in data
        assert "summary" in data

    def test_detailed_health_check_includes_all_services(self, client):
        """Test that all AWS services are checked"""
        response = client.get("/api/v1/health/detailed")
        data = response.json()

        dependencies = data["dependencies"]
        assert "dynamodb" in dependencies
        assert "s3" in dependencies
        assert "eventbridge" in dependencies
        assert "xray" in dependencies
        assert "tracing" in dependencies

    def test_detailed_health_check_has_summary(self, client):
        """Test that summary includes check counts and duration"""
        response = client.get("/api/v1/health/detailed")
        data = response.json()

        assert "summary" in data
        assert "checks_passed" in data["summary"]
        assert "checks_failed" in data["summary"]
        assert "duration_ms" in data["summary"]
        assert isinstance(data["summary"]["duration_ms"], int)


class TestHealthCheckStatuses:
    """Test health check status determination"""

    @pytest.mark.asyncio
    async def test_healthy_status_when_all_checks_pass(self):
        """Test that status is healthy when all checks pass"""
        from fastapi import Response

        from agenteval.api.routes.health import detailed_health_check

        response = Response()

        # Mock all AWS checks to succeed
        with (
            patch("agenteval.api.routes.health._check_dynamodb_health") as mock_db,
            patch("agenteval.api.routes.health._check_s3_health") as mock_s3,
            patch("agenteval.api.routes.health._check_eventbridge_health") as mock_eb,
            patch("agenteval.api.routes.health._check_xray_health") as mock_xray,
        ):
            mock_db.return_value = {"status": "healthy"}
            mock_s3.return_value = {"status": "healthy"}
            mock_eb.return_value = {"status": "healthy"}
            mock_xray.return_value = {"status": "healthy"}

            result = await detailed_health_check(response)

            assert result["status"] == "healthy"
            assert response.status_code == http_status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_degraded_status_when_some_checks_fail(self):
        """Test that status is degraded when some checks fail"""
        from fastapi import Response

        from agenteval.api.routes.health import detailed_health_check

        response = Response()

        # Mock some checks to fail
        with (
            patch("agenteval.api.routes.health._check_dynamodb_health") as mock_db,
            patch("agenteval.api.routes.health._check_s3_health") as mock_s3,
            patch("agenteval.api.routes.health._check_eventbridge_health") as mock_eb,
            patch("agenteval.api.routes.health._check_xray_health") as mock_xray,
        ):
            mock_db.return_value = {"status": "healthy"}
            mock_s3.return_value = {"status": "healthy"}
            mock_eb.return_value = {"status": "unhealthy", "error": "Connection failed"}
            mock_xray.return_value = {"status": "degraded", "error": "Timeout"}

            result = await detailed_health_check(response)

            assert result["status"] == "degraded"
            assert response.status_code == http_status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_unhealthy_status_when_all_checks_fail(self):
        """Test that status is unhealthy when all checks fail"""
        from fastapi import Response

        from agenteval.api.routes.health import detailed_health_check

        response = Response()

        # Mock all checks to fail
        with (
            patch("agenteval.api.routes.health._check_dynamodb_health") as mock_db,
            patch("agenteval.api.routes.health._check_s3_health") as mock_s3,
            patch("agenteval.api.routes.health._check_eventbridge_health") as mock_eb,
            patch("agenteval.api.routes.health._check_xray_health") as mock_xray,
        ):
            mock_db.return_value = {"status": "unhealthy", "error": "No connection"}
            mock_s3.return_value = {"status": "unhealthy", "error": "No connection"}
            mock_eb.return_value = {"status": "unhealthy", "error": "No connection"}
            mock_xray.return_value = {"status": "unhealthy", "error": "No connection"}

            result = await detailed_health_check(response)

            assert result["status"] == "unhealthy"
            assert response.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE


class TestIndividualServiceChecks:
    """Test individual AWS service health checks"""

    @pytest.mark.asyncio
    async def test_dynamodb_health_check_success(self):
        """Test DynamoDB health check with successful connection"""
        from agenteval.api.routes.health import _check_dynamodb_health

        # Mock DynamoDB client
        mock_client = AsyncMock()

        # Mock the low-level client that will be created
        mock_low_level_client = AsyncMock()
        mock_low_level_client.describe_table.return_value = {"Table": {"TableStatus": "ACTIVE"}}
        mock_low_level_client.__aexit__ = AsyncMock()

        # Mock session.client() to return the low-level client
        mock_session = MagicMock()
        mock_session_client = AsyncMock()
        mock_session_client.__aenter__.return_value = mock_low_level_client
        mock_session.client.return_value = mock_session_client

        mock_client.session = mock_session

        result = await _check_dynamodb_health(mock_client)

        assert result["status"] == "healthy"
        assert "region" in result
        assert "table_status" in result

    @pytest.mark.asyncio
    async def test_dynamodb_health_check_timeout(self):
        """Test DynamoDB health check with timeout"""
        import asyncio

        from agenteval.api.routes.health import _check_dynamodb_health

        # Mock DynamoDB client to timeout
        mock_client = AsyncMock()

        # Make the describe_table hang
        async def slow_describe(**kwargs):
            await asyncio.sleep(10)

        mock_low_level_client = AsyncMock()
        mock_low_level_client.describe_table = slow_describe
        mock_low_level_client.__aexit__ = AsyncMock()

        mock_session = MagicMock()
        mock_session_client = AsyncMock()
        mock_session_client.__aenter__.return_value = mock_low_level_client
        mock_session.client.return_value = mock_session_client

        mock_client.session = mock_session

        result = await _check_dynamodb_health(mock_client)

        assert result["status"] == "unhealthy"
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_s3_health_check_success(self):
        """Test S3 health check with successful connection"""
        from agenteval.api.routes.health import _check_s3_health

        # Mock S3 client
        mock_client = AsyncMock()
        mock_client._client.list_buckets.return_value = {"Buckets": [{"Name": "test-bucket"}]}

        result = await _check_s3_health(mock_client)

        assert result["status"] == "healthy"
        assert "bucket_count" in result
        assert result["bucket_count"] == 1

    @pytest.mark.asyncio
    async def test_eventbridge_health_check_degraded_on_failure(self):
        """Test EventBridge health check returns degraded (non-critical)"""
        from agenteval.api.routes.health import _check_eventbridge_health

        # Mock EventBridge client to fail
        mock_client = AsyncMock()
        mock_client._client.list_event_buses.side_effect = Exception("Connection failed")

        result = await _check_eventbridge_health(mock_client)

        # EventBridge is non-critical, so should be degraded not unhealthy
        assert result["status"] == "degraded"
        assert "note" in result or "Non-critical" in str(result)

    @pytest.mark.asyncio
    async def test_xray_health_check_degraded_on_failure(self):
        """Test X-Ray health check returns degraded (non-critical)"""
        from agenteval.api.routes.health import _check_xray_health

        # Mock X-Ray client to fail
        mock_client = AsyncMock()
        mock_client._client.get_trace_summaries.side_effect = Exception("Connection failed")

        result = await _check_xray_health(mock_client)

        # X-Ray is non-critical, so should be degraded not unhealthy
        assert result["status"] == "degraded"
        assert "note" in result or "Non-critical" in str(result)


class TestReadinessCheck:
    """Test Kubernetes readiness check"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_readiness_check_structure(self, client):
        """Test readiness check returns expected structure"""
        response = client.get("/api/v1/health/ready")
        data = response.json()

        assert "status" in data
        assert "checks" in data

    @pytest.mark.asyncio
    async def test_readiness_returns_200_when_ready(self):
        """Test readiness check returns 200 when services are ready"""
        from fastapi import Response

        from agenteval.api.routes.health import readiness_check

        response = Response()

        # Mock AWS clients to succeed quickly
        with (
            patch("agenteval.api.routes.health.DynamoDBClient") as mock_db,
            patch("agenteval.api.routes.health.S3Client") as mock_s3,
        ):
            mock_db.return_value.__aenter__.return_value = AsyncMock()
            mock_db.return_value.__aexit__.return_value = None
            mock_s3.return_value.__aenter__.return_value = AsyncMock()
            mock_s3.return_value.__aexit__.return_value = None

            result = await readiness_check(response)

            assert result["status"] == "ready"
            assert response.status_code == http_status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_readiness_returns_503_when_not_ready(self):
        """Test readiness check returns 503 when services are not ready"""
        from fastapi import Response

        from agenteval.api.routes.health import readiness_check

        response = Response()

        # Pass None as clients to simulate not ready state
        result = await readiness_check(response, dynamodb=None, s3=None)

        assert result["status"] == "not_ready"
        assert response.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE


class TestLivenessCheck:
    """Test Kubernetes liveness check"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_liveness_check_returns_200(self, client):
        """Test liveness check always returns 200"""
        response = client.get("/api/v1/health/live")

        assert response.status_code == http_status.HTTP_200_OK

    def test_liveness_check_structure(self, client):
        """Test liveness check returns expected structure"""
        response = client.get("/api/v1/health/live")
        data = response.json()

        assert "status" in data
        assert data["status"] == "alive"
        assert "timestamp" in data
