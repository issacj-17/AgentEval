"""
Amazon Bedrock Client for LLM Inference

Provides async interface to Amazon Bedrock for Claude and Nova models.
"""

import json
import logging
from typing import Any

import aioboto3
from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agenteval.config import settings

logger = logging.getLogger(__name__)


class BedrockClient:
    """Async client for Amazon Bedrock Runtime API"""

    def __init__(self) -> None:
        self.session = aioboto3.Session(
            region_name=settings.aws.region,
            profile_name=settings.aws.profile,
            aws_access_key_id=settings.aws.access_key_id,
            aws_secret_access_key=settings.aws.secret_access_key,
        )
        self._client: Any | None = None
        self._model_profiles: dict[str, str | None] = {
            (
                settings.aws.bedrock_persona_model or ""
            ).lower(): settings.aws.bedrock_persona_profile_arn,
            (
                settings.aws.bedrock_redteam_model or ""
            ).lower(): settings.aws.bedrock_redteam_profile_arn,
            (
                settings.aws.bedrock_judge_model or ""
            ).lower(): settings.aws.bedrock_judge_profile_arn,
        }
        self._fallback_models: dict[str, str | None] = {
            (
                settings.aws.bedrock_persona_model or ""
            ).lower(): settings.aws.bedrock_persona_fallback_model,
            (
                settings.aws.bedrock_redteam_model or ""
            ).lower(): settings.aws.bedrock_redteam_fallback_model,
            (
                settings.aws.bedrock_judge_model or ""
            ).lower(): settings.aws.bedrock_judge_fallback_model,
        }

    async def __aenter__(self) -> "BedrockClient":
        """Async context manager entry"""
        self._client = await self.session.client("bedrock-runtime").__aenter__()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit"""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ClientError),
        reraise=True,
    )
    async def invoke_claude(
        self,
        prompt: str,
        model_id: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Invoke Claude model via Bedrock

        Args:
            prompt: User prompt text
            model_id: Bedrock model ID (defaults to persona model)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system prompt

        Returns:
            Dict containing model response

        Raises:
            ClientError: If Bedrock API call fails
        """
        if not model_id:
            model_id = settings.aws.bedrock_persona_model

        # Build request body for Claude
        messages = [{"role": "user", "content": prompt}]

        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if system_prompt:
            body["system"] = system_prompt

        try:
            # Use inference profile ARN as modelId if available, otherwise use model_id
            profile_arn = self._resolve_profile(model_id)
            effective_model_id = profile_arn if profile_arn else model_id

            invoke_kwargs: dict[str, Any] = {
                "modelId": effective_model_id,
                "body": json.dumps(body),
            }

            response = await self._client.invoke_model(**invoke_kwargs)

            response_body = json.loads(await response["body"].read())

            logger.info(
                "Claude invocation successful",
                extra={
                    "model_id": model_id,
                    "input_tokens": response_body.get("usage", {}).get("input_tokens"),
                    "output_tokens": response_body.get("usage", {}).get("output_tokens"),
                    "stop_reason": response_body.get("stop_reason"),
                },
            )

            return {
                "content": response_body["content"][0]["text"],
                "stop_reason": response_body.get("stop_reason"),
                "usage": response_body.get("usage", {}),
                "model_id": response_body.get("model"),
            }

        except ClientError as e:
            fallback_response = await self._maybe_invoke_fallback(
                original_model=model_id,
                prompt=prompt,
                error=e,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
            )
            if fallback_response is not None:
                return fallback_response
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"Bedrock API error: {error_code} - {error_message}",
                extra={"model_id": model_id, "error_code": error_code},
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ClientError),
        reraise=True,
    )
    async def invoke_nova(
        self,
        prompt: str,
        model_id: str | None = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Invoke Nova model via Bedrock

        Args:
            prompt: User prompt text
            model_id: Bedrock model ID (defaults to judge model)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system instruction for the model

        Returns:
            Dict containing model response

        Raises:
            ClientError: If Bedrock API call fails
        """
        if not model_id:
            model_id = settings.aws.bedrock_judge_model

        # Build request body for Nova
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": [{"text": system_prompt}]})
        messages.append({"role": "user", "content": [{"text": prompt}]})

        inference_config: dict[str, Any] = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
        }

        # Accept common optional sampling parameters without raising.
        optional_parameters = {
            "top_p": "top_p",
            "top_k": "top_k",
        }
        for kwarg_name, config_key in optional_parameters.items():
            value = kwargs.get(kwarg_name)
            if value is not None:
                inference_config[config_key] = value

        body = {
            "messages": messages,
            "inferenceConfig": inference_config,
        }

        try:
            # Use inference profile ARN as modelId if available, otherwise use model_id
            profile_arn = self._resolve_profile(model_id)
            effective_model_id = profile_arn if profile_arn else model_id

            invoke_kwargs: dict[str, Any] = {
                "modelId": effective_model_id,
                "body": json.dumps(body),
            }

            response = await self._client.invoke_model(**invoke_kwargs)

            response_body = json.loads(await response["body"].read())

            logger.info(
                "Nova invocation successful",
                extra={"model_id": model_id, "stop_reason": response_body.get("stopReason")},
            )

            return {
                "content": response_body["output"]["message"]["content"][0]["text"],
                "stop_reason": response_body.get("stopReason"),
                "usage": response_body.get("usage", {}),
                "model_id": model_id,
            }

        except ClientError as e:
            fallback_response = await self._maybe_invoke_fallback(
                original_model=model_id,
                prompt=prompt,
                error=e,
                max_tokens=max_tokens,
                temperature=temperature,
                system_prompt=system_prompt,
                **kwargs,
            )
            if fallback_response is not None:
                return fallback_response
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"Bedrock API error: {error_code} - {error_message}",
                extra={"model_id": model_id, "error_code": error_code},
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(ClientError),
        reraise=True,
    )
    async def invoke_titan(
        self,
        prompt: str,
        model_id: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        """Invoke Amazon Titan text models via Bedrock."""

        if not model_id:
            model_id = settings.aws.bedrock_persona_model

        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"

        body = {
            "inputText": prompt,
            "textGenerationConfig": {"maxTokenCount": max_tokens, "temperature": temperature},
        }

        try:
            # Use inference profile ARN as modelId if available, otherwise use model_id
            profile_arn = self._resolve_profile(model_id)
            effective_model_id = profile_arn if profile_arn else model_id

            invoke_kwargs: dict[str, Any] = {
                "modelId": effective_model_id,
                "body": json.dumps(body),
            }

            response = await self._client.invoke_model(**invoke_kwargs)

            response_body = json.loads(await response["body"].read())
            result = (response_body.get("results") or [{}])[0]

            logger.info(
                "Titan invocation successful",
                extra={"model_id": model_id, "completion_reason": result.get("completionReason")},
            )

            usage = result.get("tokenCount") or response_body.get("tokenCount", {})

            return {
                "content": result.get("outputText", ""),
                "stop_reason": result.get("completionReason"),
                "usage": usage,
                "model_id": model_id,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]

            logger.error(
                f"Bedrock API error: {error_code} - {error_message}",
                extra={"model_id": model_id, "error_code": error_code},
            )
            raise

    async def invoke_model(self, prompt: str, model_id: str, **kwargs: Any) -> dict[str, Any]:
        """
        Universal model invocation (auto-detects Claude vs Nova)

        Args:
            prompt: User prompt text
            model_id: Bedrock model ID
            **kwargs: Additional model-specific parameters

        Returns:
            Dict containing model response
        """
        model_lower = model_id.lower()

        if "claude" in model_lower:
            return await self.invoke_claude(prompt, model_id, **kwargs)
        if "nova" in model_lower:
            return await self.invoke_nova(prompt, model_id, **kwargs)
        if "titan" in model_lower:
            return await self.invoke_titan(prompt, model_id, **kwargs)

        raise ValueError(f"Unsupported model: {model_id}")

    def _resolve_profile(self, model_id: str | None) -> str | None:
        """Return a configured inference profile ARN for the given model, if any."""
        if not model_id:
            return None
        return self._model_profiles.get(model_id.lower())

    async def _maybe_invoke_fallback(
        self,
        *,
        original_model: str | None,
        prompt: str,
        error: ClientError,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """
        Attempt to invoke a configured fallback model when the primary model fails.
        """
        if not original_model:
            return None

        error_code = error.response.get("Error", {}).get("Code")
        error_message = error.response.get("Error", {}).get("Message", "")

        # Only consider fallbacks for inference profile or throughput validation errors
        if error_code != "ValidationException" or "inference profile" not in error_message.lower():
            return None

        fallback_model = self._fallback_models.get(original_model.lower())
        if not fallback_model or fallback_model.lower() == original_model.lower():
            return None

        logger.warning(
            "Falling back from model '%s' to '%s' due to validation error: %s",
            original_model,
            fallback_model,
            error_message,
        )

        # Perform the fallback invocation using the generic dispatch
        return await self.invoke_model(prompt, fallback_model, **kwargs)


# Global client instance (use with context manager)
async def get_bedrock_client() -> BedrockClient:
    """Dependency injection for Bedrock client"""
    return BedrockClient()
