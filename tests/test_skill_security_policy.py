import pytest

from core.skills import SkillRegistry


def test_unsafe_builtin_skills_are_hidden_and_cannot_execute_by_default(monkeypatch):
    monkeypatch.delenv("ADGENTS_ENABLE_UNSAFE_TOOLS", raising=False)
    registry = SkillRegistry()

    visible_names = {skill.name for skill in registry.list()}
    assert "code_execute" not in visible_names
    assert "file_write" not in visible_names
    assert "code_execute" not in {tool["function"]["name"] for tool in registry.get_openai_tools()}
    result = registry.execute("code_execute", code="print('should not run')")

    assert not result.success
    assert "security policy" in result.error


def test_custom_python_skill_registration_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("ADGENTS_ENABLE_CUSTOM_SKILLS", raising=False)
    registry = SkillRegistry()

    with pytest.raises(ValueError, match="ADGENTS_ENABLE_CUSTOM_SKILLS"):
        registry.register_from_code("custom", "custom test", "def handler(): return 'ran'")