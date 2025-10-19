"""
PersonaAgent - Realistic user simulation with cognitive memory

Loads personas from YAML-based library for flexible, swappable user simulation.
Supports 10+ persona types including frustrated customers, technical experts,
elderly users, adversarial testers, and more.
"""

import json
import logging
import re
from enum import Enum
from typing import Any
from uuid import uuid4

import httpx
from opentelemetry import trace
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from agenteval.agents.base import BaseAgent
from agenteval.config import settings
from agenteval.memory.persona_memory import PersonaMemory
from agenteval.observability.tracer import (
    get_current_trace_id,
    inject_agentcore_headers,
    trace_operation,
)
from agenteval.persona import get_persona_library

logger = logging.getLogger(__name__)


class PersonaType(str, Enum):
    """
    Legacy persona types for backward compatibility.
    New code should use persona_id strings directly.
    """

    FRUSTRATED_CUSTOMER = "frustrated_customer"
    TECHNICAL_EXPERT = "technical_expert"
    ELDERLY_USER = "elderly_user"
    ADVERSARIAL_USER = "adversarial_user"
    IMPATIENT_EXECUTIVE = "impatient_executive"
    CURIOUS_STUDENT = "curious_student"
    SKEPTICAL_JOURNALIST = "skeptical_journalist"
    NON_NATIVE_SPEAKER = "non_native_speaker"
    OVERWHELMED_PARENT = "overwhelmed_parent"
    SECURITY_CONSCIOUS_USER = "security_conscious_user"


class PersonaAgent(BaseAgent):
    """
    Agent that simulates realistic user behavior

    Features:
    - Multi-level memory system
    - Dynamic state tracking (frustration, patience, goals)
    - Persona-specific behavior patterns
    - Context-aware message generation
    """

    def __init__(
        self,
        persona_type: PersonaType | str | None = None,
        persona_id: str | None = None,
        agent_id: str | None = None,
        initial_goal: str | None = None,
    ) -> None:
        """
        Initialize persona agent

        Args:
            persona_type: (Legacy) Type of persona to simulate (PersonaType enum)
            persona_id: Persona ID from persona library (preferred method)
            agent_id: Unique agent identifier
            initial_goal: Initial goal for the persona

        Note:
            Either persona_type OR persona_id must be provided.
            persona_id is preferred for new code.
        """
        super().__init__(agent_id=agent_id or str(uuid4()), agent_type="persona")

        # Load persona library
        self.persona_library = get_persona_library()

        # Determine persona ID (support both legacy and new API)
        if persona_id:
            self._persona_id = persona_id
        elif persona_type:
            # Support both enum and string
            self._persona_id = (
                persona_type.value if isinstance(persona_type, PersonaType) else persona_type
            )
        else:
            raise ValueError("Either persona_type or persona_id must be provided")

        # Load persona definition from library
        self.persona_definition = self.persona_library.get_persona(self._persona_id)
        if not self.persona_definition:
            raise ValueError(
                f"Persona '{self._persona_id}' not found in library. "
                f"Available personas: {self.persona_library.list_persona_ids()}"
            )

        # Keep legacy persona_type attribute for backward compatibility
        self.persona_type = (
            PersonaType(self._persona_id)
            if self._persona_id in [p.value for p in PersonaType]
            else None
        )

        self.initial_goal = initial_goal or "Get help with my issue"
        self.memory = PersonaMemory(persona_id=self.agent_id)

        # Initialize persona-specific attributes from library
        self._setup_persona_characteristics()

        logger.info(
            "PersonaAgent initialized",
            extra={
                "agent_id": self.agent_id,
                "persona_id": self._persona_id,
                "persona_name": self.persona_definition.name,
            },
        )

    def _setup_persona_characteristics(self) -> None:
        """
        Set up persona-specific characteristics from library definition
        """
        persona = self.persona_definition

        # Load attributes from PersonaDefinition
        self.memory.state.patience_level = persona.attributes.get("patience_level", 5)
        self.memory.state.frustration_level = persona.attributes.get("frustration_level", 0)

        # Load communication style
        comm_style = persona.attributes.get("communication_style", "casual")
        self.memory.add_preference("communication_style", comm_style)

        # Load other preferences
        for pref_key, pref_value in persona.preferences.items():
            self.memory.add_preference(pref_key, pref_value)

        # Load behavioral traits as semantic facts
        for trait in persona.behavioral_traits:
            self.memory.add_semantic_fact(trait)

        logger.debug(
            "Loaded persona characteristics",
            extra={
                "persona_id": self._persona_id,
                "patience": self.memory.state.patience_level,
                "frustration": self.memory.state.frustration_level,
                "traits_count": len(persona.behavioral_traits),
            },
        )

    def _get_default_model(self) -> str:
        """Get default Bedrock model for persona agents"""
        return settings.aws.bedrock_persona_model

    def _build_system_prompt(self) -> str:
        """
        Build system prompt based on persona definition and memory

        Returns:
            System prompt for LLM
        """
        # Use system_prompt template from persona definition
        prompt_template = self.persona_definition.system_prompt

        # Add memory context
        memory_context = self.memory.get_full_memory_context()

        # Format prompt with current state variables
        full_prompt = prompt_template.format(
            goal=self.initial_goal,
            frustration=self.memory.state.frustration_level,
            patience=self.memory.state.patience_level,
        )

        if memory_context:
            full_prompt += f"\n\nContext from memory:\n{memory_context}"

        full_prompt += (
            "\n\nCommunication directives:\n"
            "- Speak only as the persona (the end user) using first-person language.\n"
            "- Do not roleplay as or speak on behalf of the support bot; never say you are here to help.\n"
            "- Avoid prefixes such as 'Bot:' or 'Assistant:' and omit system/tool metadata.\n"
            "- Provide a natural sentence or two that reflects the persona's tone and goal.\n"
            "- Escalate frustration if the system repeats your words or fails to provide new help."
        )

        return full_prompt

    def _sanitize_user_message(self, message: str) -> str:
        """
        Clean LLM output so stored messages reflect the persona perspective.

        Removes role prefixes, meta explanations, and unwraps simple JSON/code fences.
        Falls back to the persona goal if nothing meaningful remains.
        """
        cleaned = message.strip()

        if not cleaned:
            return self._fallback_user_message()

        # CRITICAL: Reject meta-response hallucinations where LLM echoes context
        # This prevents Turn 2+ from exposing internal state
        meta_response_patterns = [
            "current state:",
            "frustration level:",
            "patience level:",
            "goal progress:",
        ]
        cleaned_lower = cleaned.lower()
        for pattern in meta_response_patterns:
            if pattern in cleaned_lower:
                logger.warning(
                    f"Meta-response detected in user message (pattern: '{pattern}'). "
                    f"Using fallback message."
                )
                return self._fallback_user_message()

        # Unwrap common fenced formats (```text ... ```)
        if cleaned.startswith("```"):
            parts = cleaned.split("\n", 1)
            if len(parts) == 2:
                cleaned = parts[1]
            cleaned = cleaned.strip("` \n")

        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0].strip()

        # Attempt to extract text from simple JSON blobs
        if cleaned.startswith("{") and cleaned.endswith("}"):
            try:
                payload = json.loads(cleaned)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                for key in ("message", "content", "text", "response"):
                    value = payload.get(key)
                    if isinstance(value, str) and value.strip():
                        cleaned = value.strip()
                        break

        # Remove meta lead-ins and role prefixes
        lead_phrases = [
            "here's my next message",
            "here is my next message",
            "here's what i will send",
            "here is what i will send",
            "here's your next message",
            "here is your next message",
            "this is your next message",
            "your next message is",
            "sure, here's my response",
            "next message:",
            "message:",
        ]
        lowered = cleaned.lower()
        for phrase in lead_phrases:
            if lowered.startswith(phrase):
                cleaned = cleaned[len(phrase) :].lstrip(" :-\n")
                lowered = cleaned.lower()
                break

        prefix_pattern = re.compile(
            r"^(?:assistant|agent|ai|bot|system|support(?: agent)?|customer service|support team)\s*[:\-]\s*",
            re.IGNORECASE,
        )
        cleaned = prefix_pattern.sub("", cleaned, count=1)

        if cleaned.lower().startswith("persona:"):
            cleaned = cleaned.split(":", 1)[1].lstrip(" -")

        cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()

        if not cleaned:
            return self._fallback_user_message()

        transcript_markers = (
            r"\buser:\s*",
            r"\bcustomer:\s*",
            r"\bpersona:\s*",
        )
        for pattern in transcript_markers:
            if re.search(pattern, cleaned, re.IGNORECASE):
                cleaned = re.split(pattern, cleaned, flags=re.IGNORECASE)[-1]
                cleaned = re.split(r"(?i)\b(bot|assistant|agent):\s*", cleaned)[0]
                cleaned = cleaned.strip()
                break

        normalized = re.sub(r"\s+", " ", cleaned).strip()
        sentences = re.split(r"(?<=[.!?])\s+|\n+", normalized)

        support_markers = (
            "i'm here to help",
            "i am here to help",
            "i'll be glad to assist",
            "i'll be happy to assist",
            "i'm sorry you're having",
            "i apologize for the inconvenience",
            "give me a moment",
            "sorry - this model",
            "sorry, this model",
            "i will do my best",
            "sincerely, bot",
        )
        meta_markers = (
            "your next message",
            "here is your message",
            "this message conveys",
            "as the persona",
            "the persona should say",
            "start your message",
            "remember to",
            "make sure to",
            "model is designed to avoid",
            "simulated conversation",
            # CRITICAL: Detect meta-response hallucinations from context echo
            "current state:",
            "frustration level:",
            "patience level:",
            "goal progress:",
            "interaction count:",
            "recent conversation:",
            "known facts:",
            "user preferences:",
        )

        filtered_sentences: list[str] = []
        seen_sentences: set[str] = set()
        for sentence in sentences:
            stripped = sentence.strip()
            if not stripped:
                continue
            if stripped.startswith("-"):
                continue

            lower_sentence = stripped.lower()

            if any(marker in lower_sentence for marker in support_markers):
                continue
            if any(marker in lower_sentence for marker in meta_markers):
                continue

            if lower_sentence in seen_sentences:
                continue

            seen_sentences.add(lower_sentence)
            filtered_sentences.append(stripped)

            if len(filtered_sentences) >= 3:
                break

        if not filtered_sentences:
            return self._fallback_user_message()

        pronoun_pattern = re.compile(r"^(i|i'm|i’ve|i have|my|we|we're|we have)\b", re.IGNORECASE)
        preferred = [s for s in filtered_sentences if pronoun_pattern.match(s)]
        selected = preferred if preferred else filtered_sentences

        cleaned = " ".join(selected[:3]).strip()

        if not cleaned or re.search(r"\[[^\]]+\]", cleaned):
            return self._fallback_user_message()

        return cleaned

    def _fallback_user_message(self) -> str:
        """Provide a reasonable fallback user utterance."""
        base = self.initial_goal or "I need help with my issue"
        return base if base.endswith((".", "!", "?")) else f"{base}."

    @staticmethod
    def validate_user_message(message: str) -> tuple[bool, str | None]:
        """
        Validate that a user message is natural dialogue, not a meta-response.

        Args:
            message: The message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        forbidden_patterns = [
            ("current state", "contains internal state information"),
            ("frustration level", "exposes frustration metric"),
            ("patience level", "exposes patience metric"),
            ("goal progress", "exposes goal progress metric"),
            ("interaction count", "exposes interaction count"),
            ("interactions:", "exposes interaction tracking"),
        ]

        message_lower = message.lower()
        for pattern, reason in forbidden_patterns:
            if pattern in message_lower:
                return False, f"Meta-response detected: {reason}"

        return True, None

    async def generate_message(self, conversation_context: str | None = None) -> str:
        """
        Generate a message based on persona type and current state

        Args:
            conversation_context: Additional context for message generation

        Returns:
            Generated user message
        """
        with trace_operation(
            "persona_message_generation",
            agent_id=self.agent_id,
            persona_id=self._persona_id,
            persona_name=self.persona_definition.name,
            frustration_level=self.memory.state.frustration_level,
        ) as span:
            # Build prompt with context
            system_prompt = self._build_system_prompt()

            user_prompt = (
                "Compose the exact message you, the persona, will send to the support system.\n"
                '- Use first-person language ("I", "my").\n'
                "- Do NOT include role labels (e.g., 'Bot:'), meta commentary, or JSON.\n"
                "- Do NOT repeat or echo the context information provided above.\n"
                "- Do NOT include state information like 'Frustration Level' or 'Current State'.\n"
                "- Express your need or frustration and never offer to help or apologize on behalf of the bot.\n"
                "- Provide ONLY the natural language message content that a real user would type."
            )

            if conversation_context:
                user_prompt += f"\n\nRecent conversation:\n{conversation_context}"
            else:
                recent_context = self.memory.get_recent_context(num_turns=3)
                if recent_context != "No recent conversation history.":
                    user_prompt += f"\n\nRecent conversation:\n{recent_context}"

            # Add behavioral instructions based on state
            if self.memory.state.should_escalate():
                user_prompt += "\n\nYou're reaching your limit. Consider escalating or expressing strong frustration."

            if self.memory.state.goal_progress < 0.2 and self.memory.state.interaction_count > 3:
                user_prompt += "\n\nYou haven't made much progress. Show this in your message."

            # Generate message using LLM
            try:
                response = await self.invoke_llm(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.8,  # Higher temperature for more natural variation
                    max_tokens=300,
                )

                message = response["content"].strip()

                span.set_attribute("message_length", len(message))
                span.set_attribute("goal_progress", self.memory.state.goal_progress)

                message = self._sanitize_user_message(message)

                logger.info(
                    "Message generated",
                    extra={
                        "agent_id": self.agent_id,
                        "persona_id": self._persona_id,
                        "message_length": len(message),
                    },
                )

                return message

            except Exception as e:
                logger.error(f"Failed to generate message: {e}")
                # Generic fallback message
                return "I need some help with this. Can you assist me?"

    async def process_response(
        self,
        user_message: str,
        system_response: str,
        turn_number: int,
        response_quality: float = 0.5,
    ) -> None:
        """
        Process system response and update memory/state

        Args:
            user_message: The message sent by persona
            system_response: System's response
            turn_number: Turn sequence number
            response_quality: Assessed quality of response (0.0-1.0)
        """
        # Add turn to memory
        self.memory.add_turn(
            user_message=user_message, system_response=system_response, turn_number=turn_number
        )

        # Update state based on response quality
        self.memory.update_state_from_response(response_quality)

        # Consolidate memory if needed (every 10 turns)
        if turn_number % 10 == 0:
            summary = f"After {turn_number} turns, user goal progress: {self.memory.state.goal_progress:.0%}"
            self.memory.consolidate_memory(summary)

        logger.debug(
            "Response processed",
            extra={
                "agent_id": self.agent_id,
                "turn_number": turn_number,
                "quality": response_quality,
                "frustration": self.memory.state.frustration_level,
            },
        )

    async def _send_to_target_with_retry(
        self,
        client: httpx.AsyncClient,
        target_url: str,
        message: str,
        turn_number: int,
        timeout: float = 30.0,
    ) -> str:
        """
        Send message to target with retry logic

        Args:
            client: HTTP client
            target_url: Target system URL
            message: Message to send
            turn_number: Current turn number
            timeout: Request timeout in seconds

        Returns:
            Response from target system

        Raises:
            httpx.HTTPError: If all retries fail
        """
        # Prepare headers with observability context
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"AgentEval-Persona/{self._persona_id}",
        }

        # Inject trace context and AgentCore metadata
        headers = inject_agentcore_headers(
            headers=headers, agent_id=self.agent_id, agent_type="persona", turn_number=turn_number
        )

        # Prepare payload
        payload = {"message": message, "persona_id": self._persona_id, "turn_number": turn_number}

        # Retry decorator for transient failures
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type(
                (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.NetworkError)
            ),
            reraise=True,
        )
        async def _do_request():
            with trace_operation(
                "persona_http_request",
                agent_id=self.agent_id,
                turn_number=turn_number,
                target_url=target_url,
            ) as span:
                response = await client.post(
                    target_url, json=payload, headers=headers, timeout=timeout
                )

                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("http.response_length", len(response.text))

                response.raise_for_status()

                # Try to extract structured response (reply, response, message, etc.)
                extracted = None
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        # Check for common response keys
                        for key in ("reply", "response", "message", "text", "content", "body"):
                            value = response_data.get(key)
                            if isinstance(value, str) and value.strip():
                                extracted = value.strip()
                                break
                except (ValueError, AttributeError):
                    # Not JSON or no valid data, use raw text
                    pass

                # Return extracted message or fallback to raw text
                return extracted if extracted else response.text

        try:
            return await _do_request()
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error from target system",
                extra={
                    "agent_id": self.agent_id,
                    "turn_number": turn_number,
                    "status_code": e.response.status_code,
                    "error": str(e),
                },
            )
            # Return error message for persona to react to
            return f"Error: Received {e.response.status_code} from system"
        except Exception as e:
            logger.error(
                "Failed to send message after retries",
                extra={"agent_id": self.agent_id, "turn_number": turn_number, "error": str(e)},
            )
            return f"Error: Could not reach system - {str(e)}"

    async def execute(
        self,
        target_url: str,
        max_turns: int = 10,
        request_timeout: float = 30.0,
        early_stop_on_success: bool = True,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Execute persona interaction with target system

        Implements full HTTP interaction loop with:
        - Real HTTP calls to target system
        - Retry logic for transient failures
        - Observability context propagation
        - Adaptive memory updates
        - Conversation history tracking

        Args:
            target_url: URL of target system
            max_turns: Maximum number of conversation turns
            request_timeout: HTTP request timeout in seconds
            early_stop_on_success: Stop if goal is achieved
            **kwargs: Additional parameters

        Returns:
            Execution results including conversation history and metrics
        """
        with trace_operation(
            "persona_execution",
            agent_id=self.agent_id,
            persona_id=self._persona_id,
            persona_name=self.persona_definition.name,
            max_turns=max_turns,
        ) as execution_span:
            logger.info(
                "Starting persona execution",
                extra={
                    "agent_id": self.agent_id,
                    "persona_id": self._persona_id,
                    "persona_name": self.persona_definition.name,
                    "target_url": target_url,
                    "max_turns": max_turns,
                },
            )

            # Track conversation history
            conversation_history: list[dict[str, Any]] = []
            execution_status = "completed"
            stop_reason = "max_turns_reached"

            # Create HTTP client with connection pooling
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(request_timeout), limits=httpx.Limits(max_connections=10)
            ) as client:
                # Interaction loop
                for turn_number in range(1, max_turns + 1):
                    with trace_operation(
                        "persona_turn", turn_number=turn_number, agent_id=self.agent_id
                    ) as turn_span:
                        try:
                            # Generate message based on current state
                            logger.debug(
                                f"Generating message for turn {turn_number}",
                                extra={
                                    "agent_id": self.agent_id,
                                    "frustration": self.memory.state.frustration_level,
                                    "goal_progress": self.memory.state.goal_progress,
                                },
                            )

                            user_message = await self.generate_message()

                            turn_span.set_attribute("message_length", len(user_message))
                            turn_span.set_attribute(
                                "frustration_level", self.memory.state.frustration_level
                            )
                            turn_span.set_attribute(
                                "goal_progress", self.memory.state.goal_progress
                            )

                            # Send to target system with retries
                            logger.debug(
                                "Sending message to target system",
                                extra={
                                    "agent_id": self.agent_id,
                                    "turn_number": turn_number,
                                    "target_url": target_url,
                                },
                            )

                            system_response = await self._send_to_target_with_retry(
                                client=client,
                                target_url=target_url,
                                message=user_message,
                                turn_number=turn_number,
                                timeout=request_timeout,
                            )

                            turn_span.set_attribute("response_length", len(system_response))

                            # Estimate response quality (simple heuristic)
                            # In real scenarios, this would be done by a judge agent
                            response_quality = self._estimate_response_quality(
                                system_response, user_message
                            )

                            # Update memory and state
                            await self.process_response(
                                user_message=user_message,
                                system_response=system_response,
                                turn_number=turn_number,
                                response_quality=response_quality,
                            )

                            # Record turn in history
                            turn_record = {
                                "turn_number": turn_number,
                                "user_message": user_message,
                                "system_response": system_response,
                                "response_quality": response_quality,
                                "frustration_level": self.memory.state.frustration_level,
                                "patience_level": self.memory.state.patience_level,
                                "goal_progress": self.memory.state.goal_progress,
                                "trace_id": get_current_trace_id(),
                            }
                            conversation_history.append(turn_record)

                            logger.info(
                                f"Turn {turn_number} completed",
                                extra={
                                    "agent_id": self.agent_id,
                                    "turn_number": turn_number,
                                    "quality": response_quality,
                                    "frustration": self.memory.state.frustration_level,
                                    "goal_progress": self.memory.state.goal_progress,
                                },
                            )

                            # Check early stopping conditions
                            if early_stop_on_success and self.memory.state.goal_progress >= 0.8:
                                stop_reason = "goal_achieved"
                                logger.info(
                                    "Goal achieved, stopping early",
                                    extra={
                                        "agent_id": self.agent_id,
                                        "turns_completed": turn_number,
                                        "goal_progress": self.memory.state.goal_progress,
                                    },
                                )
                                break

                            if self.memory.state.should_escalate():
                                stop_reason = "escalation_triggered"
                                logger.info(
                                    "Escalation threshold reached",
                                    extra={
                                        "agent_id": self.agent_id,
                                        "turns_completed": turn_number,
                                        "frustration": self.memory.state.frustration_level,
                                    },
                                )
                                break

                        except Exception as e:
                            logger.error(
                                f"Error during turn {turn_number}: {e}",
                                extra={
                                    "agent_id": self.agent_id,
                                    "turn_number": turn_number,
                                    "error": str(e),
                                },
                            )
                            execution_status = "failed"
                            stop_reason = f"error_turn_{turn_number}"
                            turn_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                            turn_span.record_exception(e)
                            break

            # Build final results
            execution_span.set_attribute("execution_status", execution_status)
            execution_span.set_attribute("stop_reason", stop_reason)
            execution_span.set_attribute("turns_completed", len(conversation_history))
            execution_span.set_attribute("final_goal_progress", self.memory.state.goal_progress)

            results = {
                "agent_id": self.agent_id,
                "persona_id": self._persona_id,
                "persona_name": self.persona_definition.name,
                "persona_category": self.persona_definition.category,
                "target_url": target_url,
                "max_turns": max_turns,
                "turns_completed": len(conversation_history),
                "execution_status": execution_status,
                "stop_reason": stop_reason,
                "conversation_history": conversation_history,
                "final_memory_state": self.memory.to_dict(),
                "metrics": {
                    "final_frustration": self.memory.state.frustration_level,
                    "final_patience": self.memory.state.patience_level,
                    "final_goal_progress": self.memory.state.goal_progress,
                    "interaction_count": self.memory.state.interaction_count,
                    "escalated": self.memory.state.should_escalate(),
                },
            }

            logger.info(
                "Persona execution completed",
                extra={
                    "agent_id": self.agent_id,
                    "persona_id": self._persona_id,
                    "execution_status": execution_status,
                    "stop_reason": stop_reason,
                    "turns_completed": len(conversation_history),
                    "goal_progress": self.memory.state.goal_progress,
                },
            )

            return results

    def _estimate_response_quality(self, system_response: str, user_message: str) -> float:
        """
        Estimate response quality using simple heuristics

        This is a basic implementation. In campaign mode, the judge agent
        provides more sophisticated evaluation.

        Args:
            system_response: System's response
            user_message: User's message

        Returns:
            Quality score (0.0-1.0)
        """
        quality = 0.5  # Default neutral quality

        # Heuristic 1: Longer responses tend to be more helpful (up to a point)
        response_length = len(system_response)
        if response_length > 50:
            quality += 0.1
        if response_length > 200:
            quality += 0.1

        # Heuristic 2: Check for error indicators
        error_indicators = ["error", "failed", "cannot", "unable", "sorry"]
        if any(indicator in system_response.lower() for indicator in error_indicators):
            quality -= 0.2

        # Heuristic 3: Check for helpful indicators
        helpful_indicators = ["here", "help", "assist", "provide", "available"]
        if any(indicator in system_response.lower() for indicator in helpful_indicators):
            quality += 0.1

        # Clamp to valid range
        return max(0.0, min(1.0, quality))

    def get_agent_info(self) -> dict[str, Any]:
        """Get comprehensive agent information"""
        base_info = super().get_agent_info()
        base_info.update(
            {
                "persona_id": self._persona_id,
                "persona_name": self.persona_definition.name,
                "persona_category": self.persona_definition.category,
                "initial_goal": self.initial_goal,
                "frustration_level": self.memory.state.frustration_level,
                "patience_level": self.memory.state.patience_level,
                "goal_progress": self.memory.state.goal_progress,
                "interaction_count": self.memory.state.interaction_count,
            }
        )
        return base_info
