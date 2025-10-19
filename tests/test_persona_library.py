import pytest

from agenteval.agents.persona_agent import PersonaAgent, PersonaType
from agenteval.persona import get_persona_library


@pytest.fixture(scope="module")
def persona_library():
    return get_persona_library()


def test_persona_library_contains_expected_personas(persona_library):
    assert persona_library.get_persona_count() >= 4
    personas = persona_library.list_persona_ids()
    assert "frustrated_customer" in personas
    frustrated = persona_library.get_persona("frustrated_customer")
    assert frustrated is not None
    assert frustrated.attributes["patience_level"] <= 10


@pytest.mark.asyncio
async def test_persona_agent_supports_legacy_and_new_identifiers():
    async with PersonaAgent(persona_type=PersonaType.FRUSTRATED_CUSTOMER) as legacy_agent:
        info = legacy_agent.get_agent_info()
        assert info["agent_type"] == "persona"

    async with PersonaAgent(persona_id="curious_student") as modern_agent:
        assert modern_agent.persona_definition.id == "curious_student"
        assert modern_agent.memory.state.patience_level >= 0
