"""
Agent Communication Protocol (ACP v1.0) and Message Bus.
Enables asynchronous, structured, verifiable multi-agent communication.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import uuid


class MessageIntent(str, Enum):
    ALERT = "ALERT"                      # Urgent state alert (e.g. ICU saturation, ratio breach)
    QUERY = "QUERY"                      # Request information from another agent or blackboard
    RESPONSE = "RESPONSE"                # Reply to a query
    PROPOSAL = "PROPOSAL"                # Proposed action (e.g. step down patient P12, call in float nurse)
    COUNTER_PROPOSAL = "COUNTER_PROPOSAL"# Alternative when constraints conflict
    VOTE = "VOTE"                        # Approval/Rejection with reasoning
    DIRECTIVE = "DIRECTIVE"              # Executive command issued by Chief Orchestrator
    STATUS_UPDATE = "STATUS_UPDATE"      # Routine operational broadcast


class MessagePriority(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class AgentMessage:
    message_id: str = field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    sender_id: str = ""
    sender_role: str = ""
    recipient_id: str = "broadcast"  # "broadcast" or target agent_id
    intent: MessageIntent = MessageIntent.STATUS_UPDATE
    priority: MessagePriority = MessagePriority.NORMAL
    subject: str = ""
    content: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0          # Confidence in the message assertions (0.0 to 1.0)
    requires_ack: bool = False
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "sender_role": self.sender_role,
            "recipient_id": self.recipient_id,
            "intent": self.intent.value,
            "priority": self.priority.value,
            "subject": self.subject,
            "content": self.content,
            "payload": self.payload,
            "confidence": round(self.confidence, 2),
            "timestamp": self.timestamp.strftime("%H:%M:%S")
        }


class MessageBus:
    """
    Central hub for agent communication with topic subscription, direct routing,
    and complete audit logging.
    """

    def __init__(self):
        self._history: List[AgentMessage] = []
        self._subscribers: Dict[str, List[Callable[[AgentMessage], None]]] = {}
        self._inboxes: Dict[str, List[AgentMessage]] = {}

    def register_agent(self, agent_id: str):
        if agent_id not in self._inboxes:
            self._inboxes[agent_id] = []

    def subscribe(self, topic: str, callback: Callable[[AgentMessage], None]):
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)

    def send(self, message: AgentMessage):
        self._history.append(message)
        
        # Deliver to direct recipient inbox
        if message.recipient_id != "broadcast":
            if message.recipient_id in self._inboxes:
                self._inboxes[message.recipient_id].append(message)
        else:
            # Broadcast to all registered agents except sender
            for agt_id, inbox in self._inboxes.items():
                if agt_id != message.sender_id:
                    inbox.append(message)

        # Notify topic listeners (intent as topic)
        if message.intent.value in self._subscribers:
            for cb in self._subscribers[message.intent.value]:
                try:
                    cb(message)
                except Exception:
                    pass

    def get_inbox(self, agent_id: str, clear: bool = True) -> List[AgentMessage]:
        if agent_id not in self._inboxes:
            return []
        messages = list(self._inboxes[agent_id])
        if clear:
            self._inboxes[agent_id].clear()
        return messages

    def get_history(self, limit: int = 50) -> List[AgentMessage]:
        return self._history[-limit:]

    def clear(self):
        self._history.clear()
        for inbox in self._inboxes.values():
            inbox.clear()
