from __future__ import annotations

from agenteval.memory.persona_memory import PersonaMemory, PersonaState


def _create_memory(max_recent: int = 5, max_summaries: int = 2) -> PersonaMemory:
    return PersonaMemory(
        persona_id="tester", max_recent_turns=max_recent, max_summaries=max_summaries
    )


def test_preference_and_fact_management() -> None:
    memory = _create_memory()

    memory.add_preference("communication_style", "concise")
    memory.add_preference("preferred_language", "en")
    assert memory.preferences == {
        "communication_style": "concise",
        "preferred_language": "en",
    }

    memory.add_semantic_fact("User is a software engineer")
    memory.add_semantic_fact("User is a software engineer")  # Duplicate ignored
    assert memory.semantic_facts == ["User is a software engineer"]

    memory.add_summary("Initial onboarding complete")
    memory.add_summary("Follow-up questions resolved")
    memory.add_summary("Escalated to supervisor")  # Should trim to max summaries
    assert memory.summaries == ["Follow-up questions resolved", "Escalated to supervisor"]


def test_recent_context_and_full_memory_output() -> None:
    memory = _create_memory(max_recent=3)

    for idx in range(1, 4):
        memory.add_turn(f"question {idx}", f"answer {idx}", turn_number=idx)

    context = memory.get_recent_context()
    assert "Turn 3" in context and "question 1" in context

    memory.add_preference("tone", "empathetic")
    memory.add_semantic_fact("Prefers email follow-ups")
    memory.add_summary("Resolved billing inquiry")

    full_context = memory.get_full_memory_context()
    assert "User Preferences" in full_context
    assert "Known Facts" in full_context
    assert "Conversation History" in full_context
    assert "Recent Conversation" in full_context


def test_consolidate_memory_trims_recent_turns() -> None:
    memory = _create_memory(max_recent=5)

    for idx in range(1, 6):
        memory.add_turn(f"user {idx}", f"system {idx}", turn_number=idx)
    memory.consolidate_memory("Summarised escalation")

    assert len(memory.recent_turns) <= 3
    assert memory.summaries[-1] == "Summarised escalation"


def test_update_state_and_escalation_logic() -> None:
    memory = _create_memory()
    memory.state = PersonaState(
        frustration_level=7,
        patience_level=3,
        goal_progress=0.2,
        interaction_count=6,
    )

    memory.update_state_from_response(0.2)
    assert memory.state.frustration_level >= 8
    assert memory.state.patience_level <= 2
    assert memory.state.escalation_count == 1

    memory.update_state_from_response(0.95, goal_achieved=True)
    assert memory.state.goal_progress == 1.0
    assert memory.state.satisfaction_score == 9.0


def test_round_trip_serialisation() -> None:
    memory = _create_memory()
    memory.add_preference("channel", "mobile app")
    memory.add_semantic_fact("Located in Singapore")
    memory.add_turn("hello", "hi there", turn_number=1, metadata={"intent": "greeting"})
    memory.update_state_from_response(0.45)
    memory.consolidate_memory("Warm introduction")

    payload = memory.to_dict()
    restored = PersonaMemory.from_dict(payload)

    assert restored.persona_id == memory.persona_id
    assert restored.preferences == memory.preferences
    assert restored.semantic_facts == memory.semantic_facts
    assert restored.to_dict() == payload
