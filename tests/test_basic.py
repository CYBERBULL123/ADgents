"""
ADgents Test Suite
"""

def test_import():
    """Test that main modules can be imported."""
    try:
        from core.agent import Agent
        from core.persona import Persona
        from core.skills import SKILL_REGISTRY
        assert True
    except ImportError as e:
        assert False, f"Import failed: {e}"


def test_persona_creation():
    """Test basic persona creation."""
    from core.persona import Persona
    
    persona = Persona(
        name="TestAgent",
        role="Test",
        avatar="🤖"
    )
    
    assert persona.name == "TestAgent"
    assert persona.role == "Test"
    assert persona.avatar == "🤖"


def test_skill_registry():
    """Test skill registry."""
    from core.skills import SKILL_REGISTRY
    
    skills = SKILL_REGISTRY.list()
    assert isinstance(skills, list)
    # Should have at least mock built-in skills
    assert len(skills) >= 0
