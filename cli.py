#!/usr/bin/env python
"""
ADgents CLI — Command-line interface for the agent platform.
Run agents from the terminal without any UI.

Usage:
    python cli.py serve                    # Start the API server
    python cli.py chat researcher          # Chat with a researcher agent
    python cli.py run researcher "task"    # Run autonomous task
    python cli.py agents                   # List all agents
    python cli.py create --template engineer
"""
import sys
import json
import time
from pathlib import Path

# Add root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import typer
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text
except ImportError:
    print("Install CLI deps: python -m pip install typer rich")
    sys.exit(1)

app = typer.Typer(name="adgents", help="⚡ ADgents — Autonomous AI Agent Platform")
console = Console()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to listen on"),
    reload: bool = typer.Option(False, help="Enable auto-reload")
):
    """🚀 Start the ADgents API server."""
    import uvicorn
    console.print(Panel.fit(
        "[bold cyan]⚡ ADgents Server Starting[/bold cyan]\n\n"
        f"[green]API:[/green] http://{host}:{port}\n"
        f"[green]Studio:[/green] http://{host}:{port}/studio\n"
        f"[green]Docs:[/green] http://{host}:{port}/docs",
        title="ADgents", border_style="cyan"
    ))
    uvicorn.run("server:app", host=host, port=port, reload=reload)


@app.command()
def chat(
    template: str = typer.Argument("assistant", help="Agent template to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show agent thoughts")
):
    """💬 Start an interactive chat session with an agent."""
    from core.persona import PERSONA_TEMPLATES
    from core.agent import Agent
    from core.llm import LLM_ROUTER
    
    if template not in PERSONA_TEMPLATES:
        console.print(f"[red]Unknown template '{template}'. Available: {', '.join(PERSONA_TEMPLATES.keys())}[/red]")
        raise typer.Exit(1)
    
    persona = PERSONA_TEMPLATES[template]
    agent = Agent(persona=persona)
    
    console.print(Panel.fit(
        f"[bold]{persona.avatar} {persona.name}[/bold]\n"
        f"[dim]{persona.role}[/dim]\n\n"
        f"[italic]{persona.backstory[:150]}...[/italic]",
        title=f"Chat with {persona.name}", border_style="purple"
    ))
    console.print("[dim]Type 'quit' to exit, 'reset' to clear memory, 'help' for commands[/dim]\n")
    
    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break
        
        if not user_input:
            continue
        if user_input.lower() == 'quit':
            break
        if user_input.lower() == 'reset':
            agent.reset_session()
            console.print("[dim]Session reset.[/dim]")
            continue
        if user_input.lower() == 'help':
            console.print("[dim]Commands: quit, reset, help, stats[/dim]")
            continue
        if user_input.lower() == 'stats':
            stats = agent.stats()
            console.print_json(json.dumps(stats, indent=2))
            continue
        
        with console.status(f"[dim]{persona.name} is thinking...[/dim]"):
            response = agent.think(user_input)
        
        console.print(f"\n[bold purple]{persona.avatar} {persona.name}:[/bold purple]")
        console.print(Markdown(response))
        console.print()


@app.command()
def run(
    template: str = typer.Argument("assistant", help="Agent template"),
    task: str = typer.Argument(..., help="Task description"),
    verbose: bool = typer.Option(True, "--verbose", "-v")
):
    """⚡ Run an autonomous task with an agent."""
    from core.persona import PERSONA_TEMPLATES
    from core.agent import Agent, ThoughtStep
    
    if template not in PERSONA_TEMPLATES:
        console.print(f"[red]Unknown template: {template}[/red]")
        raise typer.Exit(1)
    
    persona = PERSONA_TEMPLATES[template]
    agent = Agent(persona=persona)
    
    console.print(Panel(
        f"[bold]{task}[/bold]",
        title=f"{persona.avatar} {persona.name} — Autonomous Task", border_style="cyan"
    ))
    
    step_icons = {"thought": "💭", "action": "⚡", "observation": "👁️", "reflection": "🔮"}
    step_colors = {"thought": "purple", "action": "blue", "observation": "green", "reflection": "yellow"}
    
    def on_thought(step: ThoughtStep):
        if verbose:
            icon = step_icons.get(step.step_type, "•")
            color = step_colors.get(step.step_type, "white")
            console.print(f"[{color}]{icon} [{step.step_type.upper()}][/{color}] {step.content[:200]}")
    
    agent.on_thought(on_thought)
    
    with console.status("[dim]Running...[/dim]"):
        agent_task = agent.run(task)
    
    console.print("\n")
    if agent_task.result:
        console.print(Panel(
            Markdown(agent_task.result),
            title="✅ Result", border_style="green"
        ))
    elif agent_task.error:
        console.print(Panel(agent_task.error, title="❌ Error", border_style="red"))


@app.command()
def templates():
    """📋 List all available agent templates."""
    from core.persona import PERSONA_TEMPLATES
    
    table = Table(title="Agent Templates", border_style="purple")
    table.add_column("Key", style="cyan")
    table.add_column("Avatar")
    table.add_column("Name", style="bold")
    table.add_column("Role", style="dim")
    table.add_column("Expertise")
    
    for key, persona in PERSONA_TEMPLATES.items():
        table.add_row(
            key, persona.avatar, persona.name, persona.role,
            ", ".join(persona.expertise_domains[:3])
        )
    
    console.print(table)


@app.command()
def skills():
    """🛠️ List all available skills."""
    from core.skills import SKILL_REGISTRY
    
    table = Table(title="Available Skills", border_style="blue")
    table.add_column("Name", style="cyan bold")
    table.add_column("Category", style="green")
    table.add_column("Description")
    
    for skill in SKILL_REGISTRY.list():
        table.add_row(skill.name, skill.category, skill.description[:60] + "...")
    
    console.print(table)


@app.command()
def status():
    """📡 Check system status."""
    from core.llm import LLM_ROUTER
    from core.skills import SKILL_REGISTRY
    
    table = Table(title="System Status", border_style="green")
    table.add_column("Component")
    table.add_column("Status")
    table.add_column("Details")
    
    # LLM providers
    for name, info in LLM_ROUTER.status().items():
        status_str = "[green]✓ Available[/green]" if info["available"] else "[red]✗ Not configured[/red]"
        default = " [yellow](default)[/yellow]" if info["default"] else ""
        table.add_row(f"LLM: {name}", f"{status_str}{default}", "")
    
    # Skills
    table.add_row("Skills Engine", "[green]✓ Active[/green]", f"{len(SKILL_REGISTRY.list())} skills")
    table.add_row("Memory System", "[green]✓ Active[/green]", "SQLite")
    
    console.print(table)


if __name__ == "__main__":
    app()
