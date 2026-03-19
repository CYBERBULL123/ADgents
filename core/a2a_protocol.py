"""
Agent-to-Agent (A2A) Protocol Implementation
Enables real-time communication between agents following Google's A2A standard.
"""
import json
import uuid
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict, field
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)


# ─── A2A Protocol Messages ───────────────────────────────────────────────────

@dataclass
class A2AMessage:
    """Base A2A Protocol message."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_id: str = ""
    receiver_id: str = ""
    crew_id: str = ""
    message_type: str = ""  # request, response, broadcast, event
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    headers: Dict[str, str] = field(default_factory=dict)
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "A2AMessage":
        return cls(**data)


@dataclass
class A2ARequest:
    """Request message (agent asking another agent to do something)."""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 30
    priority: str = "normal"  # low, normal, high, critical

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class A2AResponse:
    """Response message (agent responding to request)."""
    request_id: str = ""
    success: bool = False
    result: Any = None
    error: Optional[str] = None
    execution_time_ms: int = 0

    def to_dict(self) -> Dict:
        return asdict(self)


# ─── A2A Protocol Handler ────────────────────────────────────────────────────

class A2AProtocol:
    """
    Agent-to-Agent Protocol Handler
    
    Implements communication between agents with:
    - Request/response patterns
    - Broadcasting
    - Event notifications
    - Message queuing and reliability
    """

    def __init__(self, agent_id: str):
        """Initialize A2A protocol for an agent."""
        self.agent_id = agent_id
        self.inbox: Dict[str, A2AMessage] = {}  # message_id -> message
        self.outbox: Dict[str, A2AMessage] = {}  # message_id -> message
        self.message_handlers: Dict[str, Callable] = {}  # message_type -> handler
        self.pending_requests: Dict[str, Dict] = {}  # request_id -> request_data
        self.message_history: List[A2AMessage] = []
        self.max_history_size = 1000

    # ─── Message Creation ────────────────────────────────────────────────────

    def create_message(self, receiver_id: str, message_type: str,
                      content: Dict[str, Any], crew_id: str = "",
                      reply_to: Optional[str] = None) -> A2AMessage:
        """Create an A2A message."""
        msg = A2AMessage(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            crew_id=crew_id,
            message_type=message_type,
            content=content,
            reply_to=reply_to,
            correlation_id=str(uuid.uuid4())
        )
        return msg

    def create_request(self, receiver_id: str, action: str,
                      parameters: Dict[str, Any] = None,
                      crew_id: str = "",
                      priority: str = "normal",
                      timeout: int = 30) -> tuple[A2AMessage, A2ARequest]:
        """
        Create a request message.
        
        Returns:
            Tuple of (A2AMessage, A2ARequest)
        """
        request = A2ARequest(
            action=action,
            parameters=parameters or {},
            timeout_seconds=timeout,
            priority=priority
        )

        msg = A2AMessage(
            sender_id=self.agent_id,
            receiver_id=receiver_id,
            crew_id=crew_id,
            message_type="request",
            content=request.to_dict(),
            correlation_id=request.message_id
        )

        # Track pending request
        self.pending_requests[request.message_id] = {
            "message": msg,
            "request": request,
            "created_at": datetime.now(),
            "timeout": timeout,
            "status": "pending"
        }

        return msg, request

    def create_response(self, request_message: A2AMessage,
                       success: bool, result: Any = None,
                       error: Optional[str] = None,
                       execution_time_ms: int = 0) -> A2AMessage:
        """Create a response message."""
        response = A2AResponse(
            request_id=request_message.id,
            success=success,
            result=result,
            error=error,
            execution_time_ms=execution_time_ms
        )

        msg = A2AMessage(
            sender_id=self.agent_id,
            receiver_id=request_message.sender_id,
            crew_id=request_message.crew_id,
            message_type="response",
            content=response.to_dict(),
            reply_to=request_message.id
        )

        return msg

    def create_broadcast(self, message_type: str, content: Dict[str, Any],
                        crew_id: str = "") -> A2AMessage:
        """Create a broadcast message (to all agents in crew)."""
        msg = A2AMessage(
            sender_id=self.agent_id,
            receiver_id="*",  # Broadcast indicator
            crew_id=crew_id,
            message_type=message_type,
            content=content
        )
        return msg

    def create_event(self, event_type: str, data: Dict[str, Any],
                    crew_id: str = "") -> A2AMessage:
        """Create an event notification."""
        msg = A2AMessage(
            sender_id=self.agent_id,
            receiver_id="",  # Event - no specific receiver
            crew_id=crew_id,
            message_type="event",
            content={
                "event_type": event_type,
                "data": data
            }
        )
        return msg

    # ─── Message Handling ────────────────────────────────────────────────────

    async def send_message(self, message: A2AMessage) -> Dict[str, Any]:
        """Send a message (outbound)."""
        self.outbox[message.id] = message
        self._add_to_history(message)
        logger.info(f"A2A Send: {self.agent_id} → {message.receiver_id} ({message.message_type})")
        return {
            "success": True,
            "message_id": message.id,
            "timestamp": message.timestamp
        }

    async def receive_message(self, message: A2AMessage) -> Dict[str, Any]:
        """Receive a message (inbound)."""
        self.inbox[message.id] = message
        self._add_to_history(message)
        logger.info(f"A2A Receive: {message.sender_id} → {self.agent_id} ({message.message_type})")

        # Route to handler if registered
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                result = await handler(message) if asyncio.iscoroutinefunction(handler) else handler(message)
                return {
                    "success": True,
                    "message_id": message.id,
                    "handled": True,
                    "handler_result": result
                }
            except Exception as e:
                logger.error(f"Error handling message {message.id}: {e}")
                return {
                    "success": False,
                    "message_id": message.id,
                    "error": str(e)
                }

        return {
            "success": True,
            "message_id": message.id,
            "handled": False
        }

    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a message handler for a message type."""
        self.message_handlers[message_type] = handler
        logger.info(f"✓ Registered A2A handler for: {message_type}")

    async def wait_for_response(self, request_id: str,
                               timeout_seconds: int = 30) -> Optional[A2AMessage]:
        """Wait for a response to a request."""
        start_time = datetime.now()
        timeout_delta = __import__('datetime').timedelta(seconds=timeout_seconds)

        while True:
            # Check if response arrived
            for msg_id, msg in self.inbox.items():
                if msg.reply_to == request_id:
                    del self.inbox[msg_id]  # Remove from inbox
                    return msg

            # Check timeout
            if datetime.now() - start_time > timeout_delta:
                logger.warning(f"Request {request_id} timed out after {timeout_seconds}s")
                return None

            # Wait a bit before checking again
            await asyncio.sleep(0.1)

    # ─── Message Query ──────────────────────────────────────────────────────

    def get_inbox_messages(self, limit: int = 100) -> List[A2AMessage]:
        """Get messages in inbox."""
        return list(self.inbox.values())[-limit:]

    def get_outbox_messages(self, limit: int = 100) -> List[A2AMessage]:
        """Get messages in outbox."""
        return list(self.outbox.values())[-limit:]

    def get_message_history(self, agent_id: Optional[str] = None,
                           message_type: Optional[str] = None,
                           limit: int = 100) -> List[A2AMessage]:
        """Get message history with optional filters."""
        filtered = self.message_history

        if agent_id:
            filtered = [m for m in filtered if m.sender_id == agent_id or m.receiver_id == agent_id]

        if message_type:
            filtered = [m for m in filtered if m.message_type == message_type]

        return filtered[-limit:]

    def get_pending_requests(self) -> Dict[str, Dict]:
        """Get all pending requests."""
        # Clean up expired requests
        now = datetime.now()
        expired = [
            req_id for req_id, req_data in self.pending_requests.items()
            if (now - req_data["created_at"]).total_seconds() > req_data["timeout"]
        ]

        for req_id in expired:
            self.pending_requests[req_id]["status"] = "expired"

        return {
            k: v for k, v in self.pending_requests.items()
            if v["status"] == "pending"
        }

    def get_request_status(self, request_id: str) -> Optional[Dict]:
        """Get status of a specific request."""
        return self.pending_requests.get(request_id)

    # ─── Statistics ─────────────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """Get A2A communication statistics."""
        total_messages = len(self.message_history)
        by_type = {}
        by_agent = {}

        for msg in self.message_history:
            # Count by type
            msg_type = msg.message_type
            by_type[msg_type] = by_type.get(msg_type, 0) + 1

            # Count by agent
            if msg.sender_id != self.agent_id:
                agent = msg.sender_id
            else:
                agent = msg.receiver_id if msg.receiver_id != "*" else "broadcast"

            by_agent[agent] = by_agent.get(agent, 0) + 1

        return {
            "agent_id": self.agent_id,
            "total_messages": total_messages,
            "inbox_count": len(self.inbox),
            "outbox_count": len(self.outbox),
            "pending_requests": len(self.get_pending_requests()),
            "messages_by_type": by_type,
            "messages_by_agent": by_agent
        }

    # ─── Internal Helpers ────────────────────────────────────────────────────

    def _add_to_history(self, message: A2AMessage):
        """Add message to history with size limit."""
        self.message_history.append(message)
        if len(self.message_history) > self.max_history_size:
            self.message_history = self.message_history[-self.max_history_size:]


# ─── Global A2A Protocol Manager ────────────────────────────────────────────

class A2AProtocolManager:
    """Manages A2A protocol instances for all agents."""

    def __init__(self):
        """Initialize A2A manager."""
        self.agents: Dict[str, A2AProtocol] = {}

    def register_agent(self, agent_id: str) -> A2AProtocol:
        """Register an agent with A2A protocol."""
        if agent_id not in self.agents:
            self.agents[agent_id] = A2AProtocol(agent_id)
        return self.agents[agent_id]

    def get_agent_protocol(self, agent_id: str) -> Optional[A2AProtocol]:
        """Get A2A protocol for an agent."""
        return self.agents.get(agent_id)

    async def send_message(self, from_agent: str, to_agent: str,
                          message: A2AMessage) -> Dict[str, Any]:
        """Send a message between agents."""
        from_protocol = self.agents.get(from_agent)
        to_protocol = self.agents.get(to_agent)

        if not from_protocol or not to_protocol:
            return {
                "success": False,
                "error": "Agent protocol not initialized"
            }

        # Send from sender's perspective
        await from_protocol.send_message(message)

        # Receive from receiver's perspective
        return await to_protocol.receive_message(message)

    async def broadcast_message(self, from_agent: str, message: A2AMessage,
                               target_agents: List[str]) -> Dict[str, Any]:
        """Broadcast a message to multiple agents."""
        results = []
        for target_agent in target_agents:
            if target_agent != from_agent:
                result = await self.send_message(from_agent, target_agent, message)
                results.append(result)

        return {
            "success": True,
            "broadcast_count": len(results),
            "results": results
        }

    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global A2A statistics."""
        return {
            "total_agents": len(self.agents),
            "agents": {
                agent_id: protocol.get_statistics()
                for agent_id, protocol in self.agents.items()
            }
        }


# Global instance
_a2a_manager: Optional[A2AProtocolManager] = None


def get_a2a_manager() -> A2AProtocolManager:
    """Get or create global A2A manager."""
    global _a2a_manager
    if _a2a_manager is None:
        _a2a_manager = A2AProtocolManager()
    return _a2a_manager
