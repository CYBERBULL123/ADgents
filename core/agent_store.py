"""
Agent Persistence Store
Saves and loads Agent definition (Persona) to JSON files.
"""
import json
from pathlib import Path
from typing import List

from .persona import Persona

AGENTS_DIR = Path(__file__).parent.parent / "data" / "agents"
AGENTS_DIR.mkdir(parents=True, exist_ok=True)

def save_agent_persona(persona: Persona) -> None:
    """Save an agent persona to disk."""
    filepath = AGENTS_DIR / f"{persona.id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(persona.to_dict(), f, indent=2)

def load_all_personas() -> List[Persona]:
    """Load all saved agent personas from disk."""
    personas = []
    for filepath in AGENTS_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                personas.append(Persona.from_dict(data))
        except Exception as e:
            print(f"Error loading agent persona {filepath}: {e}")
    return personas

def delete_agent_persona(agent_id: str) -> None:
    """Delete an agent persona from disk."""
    filepath = AGENTS_DIR / f"{agent_id}.json"
    if filepath.exists():
        filepath.unlink()
