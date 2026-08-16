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
    plugins = {}
    for f in PLUGINS_DIR.glob("*.py"):
        if f.name in ("__init__.py", "base_plugin.py"):
            continue
            
        module_name = f"core.plugins.{f.stem}"
        try:
            # Force reload to get latest code changes during prototyping
            mod = importlib.import_module(module_name)
            importlib.reload(mod)
            
            # Find classes that subclass BasePlugin
            for name, cls in inspect.getmembers(mod, inspect.isclass):
                if issubclass(cls, BasePlugin) and cls is not BasePlugin:
                    instance = cls()
                    plugins[instance.plugin_id] = instance
        except Exception as e:
            print(f"[PluginManager] Warning: Failed to load plugin module {module_name}: {e}")
    return plugins

def register_active_plugin_tools():
    """Query db for connected plugins, load config, and register skills in SKILL_REGISTRY."""
    # 1. Unregister all existing integration skills to avoid duplicates/stale config
    active_skills = list(SKILL_REGISTRY._skills.values())
    for s in active_skills:
        if s.category == "integration" and s.name not in ("api_call",):
            SKILL_REGISTRY.unregister(s.name)
            
    # 2. Query DB and register connected plugins
    db_plugins = list_plugins()
    available_providers = load_all_plugins()
    
    for p in db_plugins:
        if p["status"] == "connected":
            pid = p["plugin_id"]
            if pid in available_providers:
                provider = available_providers[pid]
                skills = provider.get_skills(p["config"])
                for s in skills:
                    SKILL_REGISTRY.register(s)
                print(f"[PluginManager] Registered {len(skills)} tools for connected plugin '{pid}'")

# Load tools on startup
try:
    register_active_plugin_tools()
except Exception as e:
    print(f"[PluginManager] Failed to auto-register tools at boot: {e}")
