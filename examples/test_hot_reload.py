#!/usr/bin/env python
"""
Test Hot-Reload Functionality

Demonstrates how to add custom personas/attacks/metrics and reload them
without restarting the service.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def test_persona_reload():
    """Test persona library hot-reload"""
    from agenteval.persona import get_persona_library, reload_persona_library

    print("=" * 60)
    print("Testing Persona Library Hot-Reload")
    print("=" * 60)

    # Initial load
    library = get_persona_library()
    initial_count = library.count()
    print("\n1. Initial library state:")
    print(f"   Total personas: {initial_count}")
    print(f"   Available IDs: {library.list_ids()}")

    # Reload
    print(f"\n2. Reloading library from: {library.library_path}")
    reload_persona_library()

    # Check after reload
    library = get_persona_library()
    final_count = library.count()
    print("\n3. After reload:")
    print(f"   Total personas: {final_count}")
    print(f"   Available IDs: {library.list_ids()}")

    # Validation
    validation = library.validate()
    print("\n4. Validation:")
    print(f"   Valid: {validation['valid']}")
    print(f"   Errors: {validation['errors']}")
    print(f"   Warnings: {validation['warnings']}")

    if validation["valid"]:
        print("\n✅ Persona library reload successful!")
    else:
        print("\n❌ Validation errors found")


async def test_attack_reload():
    """Test attack library hot-reload"""
    from agenteval.redteam import get_attack_library, reload_attack_library

    print("\n" + "=" * 60)
    print("Testing Attack Library Hot-Reload")
    print("=" * 60)

    # Initial load
    library = get_attack_library()
    initial_count = library.count()
    print("\n1. Initial library state:")
    print(f"   Total attacks: {initial_count}")
    print(f"   Categories: {library.list_categories()}")

    # Reload
    print(f"\n2. Reloading library from: {library.library_path}")
    reload_attack_library()

    # Check after reload
    library = get_attack_library()
    final_count = library.count()
    print("\n3. After reload:")
    print(f"   Total attacks: {final_count}")
    print(f"   Categories: {library.list_categories()}")

    # Validation
    validation = library.validate()
    print("\n4. Validation:")
    print(f"   Valid: {validation['valid']}")

    if validation["valid"]:
        print("\n✅ Attack library reload successful!")
    else:
        print("\n❌ Validation errors found")


async def test_metric_reload():
    """Test metric library hot-reload"""
    from agenteval.evaluation import get_metric_library, reload_metric_library

    print("\n" + "=" * 60)
    print("Testing Metric Library Hot-Reload")
    print("=" * 60)

    # Initial load
    library = get_metric_library()
    initial_count = library.count()
    print("\n1. Initial library state:")
    print(f"   Total metrics: {initial_count}")
    print(f"   Available IDs: {library.list_ids()}")

    # Reload
    print(f"\n2. Reloading library from: {library.library_path}")
    reload_metric_library()

    # Check after reload
    library = get_metric_library()
    final_count = library.count()
    print("\n3. After reload:")
    print(f"   Total metrics: {final_count}")
    print(f"   Categories: {library.list_categories()}")

    # Validation
    validation = library.validate()
    print("\n4. Validation:")
    print(f"   Valid: {validation['valid']}")

    if validation["valid"]:
        print("\n✅ Metric library reload successful!")
    else:
        print("\n❌ Validation errors found")


async def test_custom_persona_usage():
    """Test using a reloaded persona in an agent"""
    from agenteval.persona import get_persona_library

    print("\n" + "=" * 60)
    print("Testing Custom Persona Usage")
    print("=" * 60)

    library = get_persona_library()

    # Try to get a specific persona
    persona_id = "frustrated_customer"
    persona = library.get(persona_id)

    if persona:
        print(f"\n✅ Successfully loaded persona: {persona.name}")
        print(f"   Category: {persona.category}")
        print(f"   Patience Level: {persona.patience_level}")
        print(f"   Communication Style: {persona.communication_style}")
        print("\n   System Prompt Preview:")
        print(f"   {persona.system_prompt[:200]}...")
    else:
        print(f"\n❌ Persona '{persona_id}' not found")


async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("AgentEval Hot-Reload Test Suite")
    print("=" * 60)

    try:
        # Test each library type
        await test_persona_reload()
        await test_attack_reload()
        await test_metric_reload()

        # Test using a custom persona
        await test_custom_persona_usage()

        print("\n" + "=" * 60)
        print("✅ All hot-reload tests passed!")
        print("=" * 60)

        print("\n💡 Try this:")
        print("1. Edit personas/library.yaml (add a new persona)")
        print("2. Run this script again to see it loaded!")
        print("3. Or use the API: curl -X POST http://localhost:8000/admin/personas/reload")

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
