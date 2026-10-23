"""Storage and prompt loading for Markdown-based agent skills."""
import re
from pathlib import Path
from typing import Dict, List


SKILLS_DIR = Path(__file__).parent.parent / "data" / "agent_skills"
SKILL_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class AgentSkillStore:
    def __init__(self, root: Path = SKILLS_DIR):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _skill_path(self, name: str) -> Path:
        if not SKILL_NAME_PATTERN.fullmatch(name):
            raise ValueError("Skill name must use lowercase letters, numbers, hyphens, or underscores")
        return self.root / name / "SKILL.md"

    def list(self) -> List[Dict[str, str]]:
        skills = []
        for path in sorted(self.root.glob("*/SKILL.md")):
            try:
                text = path.read_text(encoding="utf-8")
                name, description, body = self._parse(path.parent.name, text)
                skills.append({"name": name, "description": description, "content": body})
            except (OSError, ValueError):
                continue
        return skills

    def save(self, name: str, description: str, content: str, overwrite: bool = False) -> Dict[str, str]:
        path = self._skill_path(name)
        description = description.strip()
        content = content.strip()
        if not description:
            raise ValueError("Skill description is required")
        if not content:
            raise ValueError("Markdown instructions are required")
        if len(content) > 100_000:
            raise ValueError("Skill instructions must be 100 KB or less")
        if path.exists() and not overwrite:
            raise FileExistsError(f"A skill named '{name}' already exists")

        path.parent.mkdir(parents=True, exist_ok=True)
        markdown = f"---\nname: {name}\ndescription: {description}\n---\n\n{content}\n"
        path.write_text(markdown, encoding="utf-8")
        return {"name": name, "description": description, "content": content}

    def delete(self, name: str) -> bool:
        path = self._skill_path(name)
        if not path.exists():
            return False
        path.unlink()
        try:
            path.parent.rmdir()
        except OSError:
            pass
        return True

    @staticmethod
    def _parse(fallback_name: str, markdown: str):
        name = fallback_name
        description = ""
        body = markdown
        if markdown.startswith("---\n"):
            _, frontmatter, remainder = markdown.split("---\n", 2)
            body = remainder.strip()
            for line in frontmatter.splitlines():
                key, separator, value = line.partition(":")
                if not separator:
                    continue
                value = value.strip().strip("\"'")
                if key.strip() == "name" and value:
                    name = value
                elif key.strip() == "description":
                    description = value
        return name, description, body


AGENT_SKILL_STORE = AgentSkillStore()


def get_assigned_agent_skills(skill_names=None) -> List[Dict[str, str]]:
    """Return the assigned Markdown workflows that still exist in the library."""
    skills = AGENT_SKILL_STORE.list()
    if skill_names is None:
        return skills
    selected = set(skill_names)
    return [skill for skill in skills if skill["name"] in selected]


def get_agent_skill_context(skill_names=None) -> str:
    """Return selected Markdown workflows for an autonomous run."""
    skills = get_assigned_agent_skills(skill_names)
    if not skills:
        return ""
    sections = []
    for skill in skills:
        sections.append(
            f"### {skill['name']}\nDescription: {skill['description']}\n\n{skill['content']}"
        )
    return "## Agent Skills (Markdown Workflows)\nUse a workflow when its description matches the task. Follow its steps and checks.\n\n" + "\n\n---\n\n".join(sections)