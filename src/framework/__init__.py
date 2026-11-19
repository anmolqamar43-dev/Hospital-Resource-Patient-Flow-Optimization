"""
Framework Package for Hospital Multi-Agent Decision System.
"""

from .message_bus import AgentMessage, MessageBus, MessageIntent, MessagePriority
from .blackboard import Blackboard
from .tool_registry import BaseTool, ToolRegistry, ToolResult
from .agent_base import BaseAgent, AgentThought
from .coordinator import HospitalOrchestrator

__all__ = [
    "AgentMessage",
    "MessageBus",
    "MessageIntent",
    "MessagePriority",
    "Blackboard",
    "BaseTool",
    "ToolRegistry",
    "ToolResult",
    "BaseAgent",
    "AgentThought",
    "HospitalOrchestrator"
]
