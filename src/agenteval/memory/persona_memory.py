"""
PersonaMemory - Multi-level memory system for Persona Agents

Implements a cognitive-realistic memory architecture with:
- Preferences (likes/dislikes)
- Semantic facts (knowledge about user)
- Conversation summaries (long-term memory)
- Recent turns (short-term memory)
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Turn:
    """Represents a single conversation turn"""

    user_message: str
    system_response: str
    timestamp: datetime
    turn_number: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaState:
    """Dynamic state tracking for persona behavior"""

    frustration_level: int = 0  # 0-10 scale
    patience_level: int = 5  # 0-10 scale
    goal_progress: float = 0.0  # 0.0-1.0 scale
    interaction_count: int = 0
    escalation_count: int = 0
    satisfaction_score: float = 5.0  # 0.0-10.0 scale

    def update_frustration(self, delta: int) -> None:
        """Update frustration level (clamped to 0-10)"""
        self.frustration_level = max(0, min(10, self.frustration_level + delta))

    def update_patience(self, delta: int) -> None:
        """Update patience level (clamped to 0-10)"""
        self.patience_level = max(0, min(10, self.patience_level + delta))

    def update_goal_progress(self, progress: float) -> None:
        """Update goal completion progress (clamped to 0.0-1.0)"""
        self.goal_progress = max(0.0, min(1.0, progress))

    def should_escalate(self) -> bool:
        """Determine if persona should escalate"""
        return (
            self.frustration_level > 7
            or self.patience_level < 2
            or (self.interaction_count > 5 and self.goal_progress < 0.3)
        )


class PersonaMemory:
    """
    Multi-level memory system for realistic persona behavior

    Memory Levels:
    1. Preferences - Persistent likes/dislikes
    2. Semantic Facts - Knowledge about the user
    3. Summaries - Conversation history summaries
    4. Recent Turns - Short-term interaction memory
    """

    def __init__(self, persona_id: str, max_recent_turns: int = 10, max_summaries: int = 5) -> None:
        """
        Initialize persona memory

        Args:
            persona_id: Unique persona identifier
            max_recent_turns: Maximum recent turns to keep in memory
            max_summaries: Maximum conversation summaries to keep
        """
        self.persona_id = persona_id

        # Global persistent memory
        self.preferences: dict[str, Any] = {}
        self.semantic_facts: list[str] = []
        self.summaries: list[str] = []

        # Session memory
        self.recent_turns: deque = deque(maxlen=max_recent_turns)
        self.max_summaries = max_summaries

        # State tracking
        self.state = PersonaState()

        # Metadata
        self.created_at = datetime.utcnow()
        self.last_updated = datetime.utcnow()

        logger.debug(f"PersonaMemory initialized for {persona_id}")

    def add_preference(self, key: str, value: Any) -> None:
        """
        Add or update a preference

        Args:
            key: Preference key (e.g., 'communication_style', 'preferred_language')
            value: Preference value
        """
        self.preferences[key] = value
        self.last_updated = datetime.utcnow()
        logger.debug(f"Added preference: {key}={value}")

    def add_semantic_fact(self, fact: str) -> None:
        """
        Add a semantic fact about the user

        Args:
            fact: A factual statement (e.g., "User is a software engineer")
        """
        if fact not in self.semantic_facts:
            self.semantic_facts.append(fact)
            self.last_updated = datetime.utcnow()
            logger.debug(f"Added semantic fact: {fact}")

    def add_summary(self, summary: str) -> None:
        """
        Add a conversation summary

        Args:
            summary: Summary of conversation segment
        """
        self.summaries.append(summary)

        # Keep only the most recent summaries
        if len(self.summaries) > self.max_summaries:
            self.summaries = self.summaries[-self.max_summaries :]

        self.last_updated = datetime.utcnow()
        logger.debug(f"Added summary (total: {len(self.summaries)})")

    def add_turn(
        self,
        user_message: str,
        system_response: str,
        turn_number: int,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Add a conversation turn to recent memory

        Args:
            user_message: User's message
            system_response: System's response
            turn_number: Turn sequence number
            metadata: Optional metadata
        """
        turn = Turn(
            user_message=user_message,
            system_response=system_response,
            timestamp=datetime.utcnow(),
            turn_number=turn_number,
            metadata=metadata or {},
        )

        self.recent_turns.append(turn)
        self.state.interaction_count += 1
        self.last_updated = datetime.utcnow()

        logger.debug(f"Added turn {turn_number} (recent turns: {len(self.recent_turns)})")

    def get_recent_context(self, num_turns: int | None = None) -> str:
        """
        Get recent conversation context as a string

        Args:
            num_turns: Number of recent turns to retrieve (None = all)

        Returns:
            Formatted conversation context
        """
        turns_to_retrieve = list(self.recent_turns)
        if num_turns:
            turns_to_retrieve = turns_to_retrieve[-num_turns:]

        if not turns_to_retrieve:
            return "No recent conversation history."

        context_parts = []
        for turn in turns_to_retrieve:
            context_parts.append(f"Turn {turn.turn_number}:")
            context_parts.append(f"  User: {turn.user_message}")
            context_parts.append(f"  System: {turn.system_response}")

        return "\n".join(context_parts)

    def get_full_memory_context(self) -> str:
        """
        Get complete memory context for LLM prompting

        Returns:
            Formatted memory context including all memory levels
        """
        parts = []

        # Preferences
        if self.preferences:
            parts.append("User Preferences:")
            for key, value in self.preferences.items():
                parts.append(f"  - {key}: {value}")

        # Semantic facts
        if self.semantic_facts:
            parts.append("\nKnown Facts:")
            for fact in self.semantic_facts:
                parts.append(f"  - {fact}")

        # Summaries
        if self.summaries:
            parts.append("\nConversation History:")
            for i, summary in enumerate(self.summaries, 1):
                parts.append(f"  {i}. {summary}")

        # Recent turns
        if self.recent_turns:
            parts.append("\nRecent Conversation:")
            parts.append(self.get_recent_context())

        # Current state
        parts.append("\nCurrent State:")
        parts.append(f"  - Frustration Level: {self.state.frustration_level}/10")
        parts.append(f"  - Patience Level: {self.state.patience_level}/10")
        parts.append(f"  - Goal Progress: {self.state.goal_progress * 100:.0f}%")
        parts.append(f"  - Interactions: {self.state.interaction_count}")

        return "\n".join(parts)

    def consolidate_memory(self, summary: str) -> None:
        """
        Consolidate recent turns into a summary (simulates memory consolidation)

        Args:
            summary: Summary of recent interactions
        """
        self.add_summary(summary)

        # Clear older recent turns (keep only last 3)
        while len(self.recent_turns) > 3:
            self.recent_turns.popleft()

        logger.info(f"Memory consolidated for {self.persona_id}")

    def update_state_from_response(
        self, response_quality: float, goal_achieved: bool = False
    ) -> None:
        """
        Update persona state based on system response

        Args:
            response_quality: Quality of response (0.0-1.0)
            goal_achieved: Whether user's goal was achieved
        """
        # Update frustration based on response quality
        if response_quality < 0.3:
            self.state.update_frustration(2)
            self.state.update_patience(-1)
        elif response_quality < 0.6:
            self.state.update_frustration(1)
        elif response_quality > 0.8:
            self.state.update_frustration(-1)
            self.state.update_patience(1)

        # Update goal progress
        if goal_achieved:
            self.state.update_goal_progress(1.0)
            self.state.satisfaction_score = 9.0
        elif response_quality > 0.7:
            current_progress = self.state.goal_progress
            self.state.update_goal_progress(current_progress + 0.2)

        # Track escalations
        if self.state.should_escalate():
            self.state.escalation_count += 1

        logger.debug(
            f"State updated: frustration={self.state.frustration_level}, "
            f"patience={self.state.patience_level}, "
            f"goal_progress={self.state.goal_progress:.2f}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Export memory to dictionary for persistence"""
        return {
            "persona_id": self.persona_id,
            "preferences": self.preferences,
            "semantic_facts": self.semantic_facts,
            "summaries": self.summaries,
            "recent_turns": [
                {
                    "user_message": turn.user_message,
                    "system_response": turn.system_response,
                    "timestamp": turn.timestamp.isoformat(),
                    "turn_number": turn.turn_number,
                    "metadata": turn.metadata,
                }
                for turn in self.recent_turns
            ],
            "state": {
                "frustration_level": self.state.frustration_level,
                "patience_level": self.state.patience_level,
                "goal_progress": self.state.goal_progress,
                "interaction_count": self.state.interaction_count,
                "escalation_count": self.state.escalation_count,
                "satisfaction_score": self.state.satisfaction_score,
            },
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonaMemory":
        """Create PersonaMemory from dictionary"""
        memory = cls(persona_id=data["persona_id"])

        memory.preferences = data.get("preferences", {})
        memory.semantic_facts = data.get("semantic_facts", [])
        memory.summaries = data.get("summaries", [])

        # Restore recent turns
        for turn_data in data.get("recent_turns", []):
            turn = Turn(
                user_message=turn_data["user_message"],
                system_response=turn_data["system_response"],
                timestamp=datetime.fromisoformat(turn_data["timestamp"]),
                turn_number=turn_data["turn_number"],
                metadata=turn_data.get("metadata", {}),
            )
            memory.recent_turns.append(turn)

        # Restore state
        state_data = data.get("state", {})
        memory.state = PersonaState(
            frustration_level=state_data.get("frustration_level", 0),
            patience_level=state_data.get("patience_level", 5),
            goal_progress=state_data.get("goal_progress", 0.0),
            interaction_count=state_data.get("interaction_count", 0),
            escalation_count=state_data.get("escalation_count", 0),
            satisfaction_score=state_data.get("satisfaction_score", 5.0),
        )

        memory.created_at = datetime.fromisoformat(data["created_at"])
        memory.last_updated = datetime.fromisoformat(data["last_updated"])

        return memory
