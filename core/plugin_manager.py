"""
ADgents Plugin Manager.
Autoloads subclass definitions of BasePlugin and manages active tool registrations.
"""
import importlib
import inspect
from pathlib import Path
from core.plugins.base_plugin import BasePlugin
from core.plugin_db import list_plugins
from core.skills import SKILL_REGISTRY

PLUGINS_DIR = Path(__file__).parent / "plugins"

def load_all_plugins() -> dict:
    """Scan and instantiate all plugins found in core/plugins/"""
    # Plugin discovery disabled. Return empty provider list.
    return {}

def register_active_plugin_tools():
    """Query db for connected plugins, load config, and register skills in SKILL_REGISTRY."""
    # Integrations disabled — do nothing
    return

# Plugins disabled in this deployment. No auto-registration performed.
