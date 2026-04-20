"""
Crew Manager - Team-based Agent Organization & Coordination
Manages crews, templates, real-time coordination and agent communication.
"""
import json
import uuid
import asyncio
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

CREWS_DIR = Path(__file__).parent.parent / "data" / "crews"
TEMPLATES_DIR = Path(__file__).parent.parent / "data" / "templates"
COMMS_FILE = CREWS_DIR / "communications.json"
CREWS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


# ─── Agent Template System ───────────────────────────────────────────────────

@dataclass
class AgentTemplate:
    """Agent template for quick creation of common agent types."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    role: str = ""
    expertise: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    instructions: str = ""
    model: str = "gemini-2.0-flash"
    temperature: float = 0.7
    tools: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentTemplate":
        return cls(**data)


# ─── Crew Management System ──────────────────────────────────────────────────

@dataclass
class CrewMember:
    """Member of a crew with role and responsibilities."""
    agent_id: str
    agent_name: str
    role: str
    status: str = "idle"  # idle, active, communicating, waiting
    current_task: Optional[str] = None
    last_update: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class CrewConfig:
    """Configuration for a Crew."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    organization: str = "default"  # Organization this crew belongs to
    members: List[CrewMember] = field(default_factory=list)
    communication_protocol: str = "a2a"  # a2a, rest, websocket
    max_parallel_tasks: int = 3
    task_queue_size: int = 10
    auto_sync: bool = True
    sync_interval: int = 1000  # ms
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "organization": self.organization,
            "members": [m.to_dict() for m in self.members],
            "communication_protocol": self.communication_protocol,
            "max_parallel_tasks": self.max_parallel_tasks,
            "task_queue_size": self.task_queue_size,
            "auto_sync": self.auto_sync,
            "sync_interval": self.sync_interval,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CrewConfig":
        data_copy = data.copy()
        if "members" in data_copy:
            data_copy["members"] = [
                CrewMember(**m) if isinstance(m, dict) else m 
                for m in data_copy["members"]
            ]
        return cls(**data_copy)


class CrewManager:
    """
    Manages crew creation, configuration, and orchestration.
    
    Supports:
    - Creating crews from templates
    - Real-time agent coordination
    - Agent-to-Agent communication
    - Task distribution and synchronization
    - Organization management
    """

    def __init__(self):
        """Initialize crew manager."""
        self.crews: Dict[str, CrewConfig] = {}
        self.templates: Dict[str, AgentTemplate] = {}
        self.organizations: Dict[str, Dict[str, Any]] = {}
        self.active_communications: Dict[str, Dict] = {}  # Track agent communications
        self.load_crews()
        self.load_templates()
        self._load_communications()
        logger.info("✓ CrewManager initialized")

    # ─── Templates ───────────────────────────────────────────────────────────

    def create_template(self, name: str, description: str, role: str,
                       expertise: List[str], skills: List[str],
                       instructions: str = "", model: str = "gemini-2.0-flash") -> AgentTemplate:
        """Create a new agent template."""
        template = AgentTemplate(
            name=name,
            description=description,
            role=role,
            expertise=expertise,
            skills=skills,
            instructions=instructions,
            model=model
        )
        self.templates[template.id] = template
        self._save_template(template)
        logger.info(f"✓ Created template: {name}")
        return template

    def get_templates(self) -> List[AgentTemplate]:
        """Get all available templates."""
        return list(self.templates.values())

    def get_template(self, template_id: str) -> Optional[AgentTemplate]:
        """Get a specific template."""
        return self.templates.get(template_id)

    def list_templates_by_role(self, role: str) -> List[AgentTemplate]:
        """List templates by role."""
        return [t for t in self.templates.values() if t.role == role]

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self.templates:
            del self.templates[template_id]
            template_path = TEMPLATES_DIR / f"{template_id}.json"
            if template_path.exists():
                template_path.unlink()
            return True
        return False

    # ─── Crews ──────────────────────────────────────────────────────────────

    def create_crew(self, name: str, description: str = "", 
                   organization: str = "default", members: List[Dict] = None,
                   communication_protocol: str = "a2a") -> CrewConfig:
        """Create a new crew."""
        crew = CrewConfig(
            name=name,
            description=description,
            organization=organization,
            communication_protocol=communication_protocol
        )

        # Add members if provided
        if members:
            for member_data in members:
                crew_member = CrewMember(
                    agent_id=member_data.get("agent_id"),
                    agent_name=member_data.get("agent_name"),
                    role=member_data.get("role", "contributor")
                )
                crew.members.append(crew_member)

        self.crews[crew.id] = crew
        self._save_crew(crew)
        logger.info(f"✓ Created crew: {name} with {len(crew.members)} members")
        return crew

    def get_crew(self, crew_id: str) -> Optional[CrewConfig]:
        """Get a crew by ID."""
        return self.crews.get(crew_id)

    def get_crews_by_organization(self, org: str) -> List[CrewConfig]:
        """Get all crews in an organization."""
        return [c for c in self.crews.values() if c.organization == org]

    def list_crews(self) -> List[CrewConfig]:
        """List all crews."""
        return list(self.crews.values())

    def add_member_to_crew(self, crew_id: str, agent_id: str, 
                          agent_name: str, role: str = "contributor") -> bool:
        """Add a member to a crew."""
        crew = self.crews.get(crew_id)
        if not crew:
            return False

        # Check if already a member
        if any(m.agent_id == agent_id for m in crew.members):
            return False

        member = CrewMember(
            agent_id=agent_id,
            agent_name=agent_name,
            role=role
        )
        crew.members.append(member)
        crew.updated_at = datetime.now().isoformat()
        self._save_crew(crew)
        logger.info(f"✓ Added {agent_name} to crew {crew.name}")
        return True

    def remove_member_from_crew(self, crew_id: str, agent_id: str) -> bool:
        """Remove a member from a crew."""
        crew = self.crews.get(crew_id)
        if not crew:
            return False

        original_len = len(crew.members)
        crew.members = [m for m in crew.members if m.agent_id != agent_id]

        if len(crew.members) < original_len:
            crew.updated_at = datetime.now().isoformat()
            self._save_crew(crew)
            logger.info(f"✓ Removed agent {agent_id} from crew {crew.name}")
            return True
        return False

    def update_member_status(self, crew_id: str, agent_id: str, 
                            status: str, current_task: Optional[str] = None) -> bool:
        """Update a member's status in real-time."""
        crew = self.crews.get(crew_id)
        if not crew:
            return False

        for member in crew.members:
            if member.agent_id == agent_id:
                member.status = status
                member.current_task = current_task
                member.last_update = datetime.now().isoformat()
                self._save_crew(crew)
                return True

        return False

    def delete_crew(self, crew_id: str) -> bool:
        """Delete a crew."""
        if crew_id in self.crews:
            del self.crews[crew_id]
            crew_path = CREWS_DIR / f"{crew_id}.json"
            if crew_path.exists():
                crew_path.unlink()
            return True
        return False

    # ─── Organizations ──────────────────────────────────────────────────────

    def create_organization(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new organization."""
        org_id = str(uuid.uuid4())
        org = {
            "id": org_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "crew_count": 0,
            "agent_count": 0
        }
        self.organizations[org_id] = org
        logger.info(f"✓ Created organization: {name}")
        return org

    def get_organization(self, org_id: str) -> Optional[Dict]:
        """Get organization details."""
        return self.organizations.get(org_id)

    def list_organizations(self) -> List[Dict]:
        """List all organizations."""
        return list(self.organizations.values())

    def get_organization_stats(self, org_id: str) -> Dict[str, Any]:
        """Get organization statistics."""
        org_crews = self.get_crews_by_organization(org_id)
        total_members = sum(len(c.members) for c in org_crews)

        return {
            "organization_id": org_id,
            "crew_count": len(org_crews),
            "total_agents": total_members,
            "active_agents": sum(
                sum(1 for m in c.members if m.status != "idle")
                for c in org_crews
            ),
            "teams": [{"name": c.name, "member_count": len(c.members)} for c in org_crews]
        }

    # ─── Agent-to-Agent Communication (A2A) ──────────────────────────────────

    async def send_message_between_agents(self, crew_id: str, from_agent: str,
                                         to_agent: str, message: Dict[str, Any],
                                         from_name: str = "", to_name: str = "",
                                         message_type: str = "message") -> Dict:
        """
        Send a message between two agents in a crew via A2A protocol.
        """
        crew = self.crews.get(crew_id)
        if not crew:
            return {"success": False, "error": "Crew not found"}

        # Verify both agents are in the crew
        agent_ids = {m.agent_id for m in crew.members}
        if from_agent not in agent_ids or to_agent not in agent_ids:
            return {"success": False, "error": "Agent not in crew"}

        # Resolve names from members if not provided
        if not from_name:
            m = next((m for m in crew.members if m.agent_id == from_agent), None)
            from_name = m.agent_name if m else from_agent[:8]
        if not to_name:
            m = next((m for m in crew.members if m.agent_id == to_agent), None)
            to_name = m.agent_name if m else to_agent[:8]

        comm_id = str(uuid.uuid4())
        communication = {
            "id": comm_id,
            "crew_id": crew_id,
            "from": from_agent,
            "to": to_agent,
            "from_name": from_name,
            "to_name": to_name,
            "message": message,
            "message_type": message_type,
            "protocol": crew.communication_protocol,
            "timestamp": datetime.now().isoformat(),
            "status": "sent"
        }

        self.active_communications[comm_id] = communication
        self._save_communications()
        logger.info(f"✓ A2A Message: {from_name} → {to_name} [{message_type}]")

        return {
            "success": True,
            "communication_id": comm_id,
            "communication": communication
        }

    async def broadcast_to_crew(self, crew_id: str, from_agent: str,
                               message: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcast a message to all agents in a crew."""
        crew = self.crews.get(crew_id)
        if not crew:
            return {"success": False, "error": "Crew not found"}

        from_member = next((m for m in crew.members if m.agent_id == from_agent), None)
        from_name = from_member.agent_name if from_member else from_agent[:8]

        results = []
        for member in crew.members:
            if member.agent_id != from_agent:
                result = await self.send_message_between_agents(
                    crew_id, from_agent, member.agent_id, message,
                    from_name=from_name, to_name=member.agent_name,
                    message_type="broadcast",
                )
                results.append(result)

        return {
            "success": True,
            "broadcast_count": len(results),
            "messages": results
        }

    def get_crew_communications(self, crew_id: str) -> List[Dict]:
        """Get all communications in a crew."""
        return [
            comm for comm in self.active_communications.values()
            if comm["crew_id"] == crew_id
        ]

    def get_agent_communications(self, agent_id: str) -> List[Dict]:
        """Get all communications for an agent."""
        return [
            comm for comm in self.active_communications.values()
            if comm["from"] == agent_id or comm["to"] == agent_id
        ]

    # ─── Persistence ────────────────────────────────────────────────────────

    def _load_communications(self):
        """Load communications from disk."""
        if COMMS_FILE.exists():
            try:
                with open(COMMS_FILE, "r", encoding="utf-8") as f:
                    self.active_communications = json.load(f)
                logger.info(f"✓ Loaded {len(self.active_communications)} communications")
            except Exception as e:
                logger.error(f"Error loading communications: {e}")

    def _save_communications(self):
        """Persist all communications to disk."""
        try:
            with open(COMMS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.active_communications, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving communications: {e}")

    def _save_crew(self, crew: CrewConfig):
        """Save crew to disk."""
        filepath = CREWS_DIR / f"{crew.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(crew.to_dict(), f, indent=2)

    def _load_crew(self, filepath: Path) -> Optional[CrewConfig]:
        """Load crew from disk."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return CrewConfig.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading crew {filepath}: {e}")
            return None

    def load_crews(self):
        """Load all crews from disk."""
        for filepath in CREWS_DIR.glob("*.json"):
            crew = self._load_crew(filepath)
            if crew:
                self.crews[crew.id] = crew

    def _save_template(self, template: AgentTemplate):
        """Save template to disk."""
        filepath = TEMPLATES_DIR / f"{template.id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(template.to_dict(), f, indent=2)

    def load_templates(self):
        """Load all templates from disk."""
        for filepath in TEMPLATES_DIR.glob("*.json"):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    template = AgentTemplate.from_dict(data)
                    self.templates[template.id] = template
            except Exception as e:
                logger.error(f"Error loading template {filepath}: {e}")


# Global instance
_crew_manager: Optional[CrewManager] = None


def get_crew_manager() -> CrewManager:
    """Get or create global crew manager."""
    global _crew_manager
    if _crew_manager is None:
        _crew_manager = CrewManager()
    return _crew_manager
