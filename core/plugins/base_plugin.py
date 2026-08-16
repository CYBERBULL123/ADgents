"""
Base Abstract Class for all ADgents Plugins.
Supports dynamic skill compile/registration patterns.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.skills import Skill

class BasePlugin(ABC):
    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique plugin ID (e.g. 'github')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """User-friendly display name (e.g. 'GitHub Integration')."""
        pass

    @abstractmethod
    def get_skills(self, config: Dict[str, Any]) -> List[Skill]:
        """Compile and return list of skill definitions for the registry."""
        pass
