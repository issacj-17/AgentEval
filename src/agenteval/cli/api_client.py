"""
HTTP Client for AgentEval API (Full Mode).

This client communicates with the deployed ECS API endpoint to create
campaigns, poll for status, and retrieve results.

Used by live_demo.py when running in full mode (--full flag).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class APIClientError(Exception):
    """Base exception for API client errors."""

    pass


class CampaignCreationError(APIClientError):
    """Raised when campaign creation fails."""

    pass


class CampaignTimeoutError(APIClientError):
    """Raised when campaign doesn't complete within timeout."""

    pass


class AgentEvalAPIClient:
    """
    HTTP client for AgentEval deployed API.

    Communicates with ECS Fargate deployment to:
    - Create evaluation campaigns
    - Poll campaign status
    - Retrieve results

    Example usage::

        async with AgentEvalAPIClient(
            base_url="http://agenteval-alb-123.us-east-1.elb.amazonaws.com",
            api_key="your-api-key"
        ) as client:
            campaign_id = await client.create_campaign(
                campaign_type="persona",
                config={"persona_type": "frustrated_customer", "max_turns": 3}
            )
            results = await client.wait_for_completion(campaign_id, timeout=300)
            print(f"Campaign completed: {results['status']}")
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: int = 120,
    ):
        """
        Initialize API client.

        Args:
            base_url: Base URL of deployed API (e.g., http://alb-dns.amazonaws.com)
            api_key: Optional API key for authentication
            timeout: Default timeout for requests in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # HTTP client (will be created in __aenter__)
        self.client: httpx.AsyncClient | None = None

        logger.info(f"API client initialized (base_url: {self.base_url})")

    async def __aenter__(self) -> AgentEvalAPIClient:
        """Context manager entry - create HTTP client."""
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=self._get_headers(),
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close HTTP client."""
        if self.client:
            await self.client.aclose()

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers including API key if provided."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def health_check(self) -> dict[str, Any]:
        """
        Check API health.

        Returns:
            Health status dict

        Raises:
            APIClientError: If health check fails
        """
        if not self.client:
            raise APIClientError("Client not initialized - use async context manager")

        try:
            response = await self.client.get(f"{self.base_url}/health")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Health check failed: {e}")
            raise APIClientError(f"Health check failed: {e}") from e

    async def create_campaign(
        self,
        campaign_type: str,
        target_url: str,
        config: dict[str, Any],
    ) -> str:
        """
        Create a new evaluation campaign.

        Args:
            campaign_type: Type of campaign ("persona" or "red_team")
            target_url: Target system URL to evaluate
            config: Campaign configuration dict

        Returns:
            Campaign ID

        Raises:
            CampaignCreationError: If campaign creation fails
        """
        if not self.client:
            raise APIClientError("Client not initialized - use async context manager")

        payload = {
            "campaign_type": campaign_type,
            "target_url": target_url,
            "config": config,
        }

        try:
            logger.info(f"Creating {campaign_type} campaign...")
            response = await self.client.post(
                f"{self.base_url}/campaigns",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            campaign_id = data.get("campaign_id")

            if not campaign_id:
                raise CampaignCreationError("No campaign_id in response")

            logger.info(f"Campaign created: {campaign_id}")
            return campaign_id

        except httpx.HTTPError as e:
            logger.error(f"Campaign creation failed: {e}")
            raise CampaignCreationError(f"Failed to create campaign: {e}") from e

    async def get_campaign_status(self, campaign_id: str) -> dict[str, Any]:
        """
        Get campaign status.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign status dict with 'status' field

        Raises:
            APIClientError: If status retrieval fails
        """
        if not self.client:
            raise APIClientError("Client not initialized - use async context manager")

        try:
            response = await self.client.get(f"{self.base_url}/campaigns/{campaign_id}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get campaign status: {e}")
            raise APIClientError(f"Failed to get status for {campaign_id}: {e}") from e

    async def get_campaign_results(self, campaign_id: str) -> dict[str, Any]:
        """
        Get campaign results.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Complete results dict

        Raises:
            APIClientError: If results retrieval fails
        """
        if not self.client:
            raise APIClientError("Client not initialized - use async context manager")

        try:
            response = await self.client.get(
                f"{self.base_url}/campaigns/{campaign_id}/results"
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to get campaign results: {e}")
            raise APIClientError(f"Failed to get results for {campaign_id}: {e}") from e

    async def wait_for_completion(
        self,
        campaign_id: str,
        timeout: int = 300,
        poll_interval: int = 5,
    ) -> dict[str, Any]:
        """
        Wait for campaign to complete by polling status.

        Args:
            campaign_id: Campaign identifier
            timeout: Maximum time to wait in seconds
            poll_interval: Time between status checks in seconds

        Returns:
            Final campaign status dict

        Raises:
            CampaignTimeoutError: If campaign doesn't complete within timeout
        """
        logger.info(f"Waiting for campaign {campaign_id} to complete...")

        start_time = asyncio.get_event_loop().time()

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise CampaignTimeoutError(
                    f"Campaign {campaign_id} did not complete within {timeout}s"
                )

            # Get status
            status_data = await self.get_campaign_status(campaign_id)
            status = status_data.get("status", "unknown")

            logger.debug(f"Campaign {campaign_id} status: {status} (elapsed: {elapsed:.1f}s)")

            # Check if completed
            if status in ["completed", "failed", "error"]:
                logger.info(f"Campaign {campaign_id} finished with status: {status}")
                return status_data

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def create_and_wait(
        self,
        campaign_type: str,
        target_url: str,
        config: dict[str, Any],
        timeout: int = 300,
    ) -> tuple[str, dict[str, Any]]:
        """
        Create campaign and wait for completion (convenience method).

        Args:
            campaign_type: Type of campaign
            target_url: Target URL
            config: Campaign config
            timeout: Maximum wait time

        Returns:
            Tuple of (campaign_id, final_status)

        Raises:
            CampaignCreationError: If creation fails
            CampaignTimeoutError: If timeout reached
        """
        campaign_id = await self.create_campaign(campaign_type, target_url, config)
        final_status = await self.wait_for_completion(campaign_id, timeout)
        return campaign_id, final_status


async def get_alb_url_from_cloudformation(
    region: str = "us-east-1",
    stack_name: str = "agenteval-ecs",
) -> str:
    """
    Retrieve ALB URL from CloudFormation stack outputs.

    Args:
        region: AWS region
        stack_name: CloudFormation stack name

    Returns:
        Load Balancer URL

    Raises:
        APIClientError: If URL cannot be retrieved
    """
    import boto3

    try:
        cf_client = boto3.client("cloudformation", region_name=region)
        response = cf_client.describe_stacks(StackName=stack_name)

        if not response.get("Stacks"):
            raise APIClientError(f"Stack {stack_name} not found")

        stack = response["Stacks"][0]
        outputs = stack.get("Outputs", [])

        # Look for LoadBalancerURL or LoadBalancerDNS output
        for output in outputs:
            key = output.get("OutputKey", "")
            if key in ["LoadBalancerURL", "LoadBalancerDNS", "APIEndpoint"]:
                url = output.get("OutputValue", "")
                logger.info(f"Found ALB URL from CloudFormation: {url}")
                return url

        raise APIClientError(f"No LoadBalancer URL found in stack {stack_name} outputs")

    except Exception as e:
        logger.error(f"Failed to get ALB URL from CloudFormation: {e}")
        raise APIClientError(f"Failed to retrieve ALB URL: {e}") from e
