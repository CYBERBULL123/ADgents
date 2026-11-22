"""
ADgents MCP Server - Entry point for running as a module.
Invoke with: python -m core
"""
import sys
import os
from pathlib import Path

# Load .env environment variables FIRST
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=True)
    except ImportError:
        # dotenv not installed, load manually
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")

# Add parent directory to path so we can import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.mcp_server import MCPServer
from core.agent_store import load_all_personas
from core.skills import SkillRegistry
from core.agent import Agent

def main():
    """Run MCP server in stdio mode."""
    try:
        # Load agents from persisted personas
        print("Loading agent personas...", file=sys.stderr)
        personas = load_all_personas()
        print(f"✓ Loaded {len(personas)} agent personas", file=sys.stderr)
        
        # Create agent instances
        print("Initializing agents...", file=sys.stderr)
        agents = []
        for persona in personas:
            try:
                agent = Agent(persona=persona)
                agents.append(agent)
                print(f"  ✓ {persona.name} initialized", file=sys.stderr)
            except Exception as e:
                print(f"  ✗ Failed to initialize {persona.name}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
        
        if not agents:
            print("⚠ Warning: No agents initialized. Check if API keys are set.", file=sys.stderr)
        
        # Load skills registry
        print("Loading skills...", file=sys.stderr)
        skill_registry = SkillRegistry()
        skills = skill_registry.list()
        print(f"✓ Loaded {len(skills)} skills", file=sys.stderr)
        
        # Create and run MCP server
        print(f"Starting MCP server with {len(agents)} agents and {len(skills)} skills", file=sys.stderr)
        server = MCPServer(skill_registry=skill_registry, agents=agents)
        server.run_stdio()
        
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
