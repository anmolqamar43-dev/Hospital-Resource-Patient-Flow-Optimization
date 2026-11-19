"""
Base Agent architecture for Hospital Multi-Agent Decision System.
Equipped with live task monitoring, cognitive traces, and LLM reasoning integration.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .message_bus import AgentMessage, MessageBus, MessageIntent, MessagePriority
from .blackboard import Blackboard
from .tool_registry import ToolRegistry, ToolResult
from .llm_client import llm_client


@dataclass
class AgentThought:
    timestamp: str
    cycle: int
    observation: str
    reasoning: str
    action_taken: str
    llm_source: str = "CLINICAL_HEURISTIC"


class BaseAgent:
    """
    Abstract Base Agent for specialized hospital role.
    Implements perception-reasoning-action cycle with uncertainty awareness
    and live real-time task reporting.
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        system_prompt: str,
        tool_registry: ToolRegistry,
        message_bus: MessageBus,
        avatar_icon: str = "🩺",
        color_accent: str = "#3b82f6"
    ):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tool_registry = tool_registry
        self.message_bus = message_bus
        self.avatar_icon = avatar_icon
        self.color_accent = color_accent
        
        self.thought_log: List[AgentThought] = []
        self.message_bus.register_agent(self.agent_id)

        # Live Real-Time Task Execution State
        self.live_state = {
            "status": "IDLE",  # IDLE, SCANNING, ANALYZING, COLLABORATING, EXECUTING, COMPLETED
            "active_task": "Awaiting operational dispatch cycle",
            "progress_pct": 0,
            "target_unit_or_patient": "Hospital-wide",
            "live_terminal_logs": [f"Agent {name} initialized and standing by."],
            "last_active_time": datetime.now().strftime("%H:%M:%S"),
            "llm_source": "CLINICAL_HEURISTIC",
            "total_tasks_completed": 0
        }

    def perceive(self, blackboard: Blackboard) -> List[AgentMessage]:
        """
        Pull incoming messages from inbox and observe shared blackboard.
        """
        inbox_messages = self.message_bus.get_inbox(self.agent_id, clear=True)
        return inbox_messages

    def set_live_task(self, task_desc: str, progress_pct: int = 50, status: str = "ANALYZING", target: str = ""):
        self.live_state["active_task"] = task_desc
        self.live_state["progress_pct"] = min(100, max(0, progress_pct))
        self.live_state["status"] = status
        if target:
            self.live_state["target_unit_or_patient"] = target
        self.live_state["last_active_time"] = datetime.now().strftime("%H:%M:%S")

    def add_live_log(self, log_line: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {log_line}"
        self.live_state["live_terminal_logs"].append(entry)
        # Keep last 8 logs
        self.live_state["live_terminal_logs"] = self.live_state["live_terminal_logs"][-8:]

    def log_thought(self, cycle: int, observation: str, reasoning: str, action: str, llm_source: str = "CLINICAL_HEURISTIC"):
        self.thought_log.append(AgentThought(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            cycle=cycle,
            observation=observation,
            reasoning=reasoning,
            action_taken=action,
            llm_source=llm_source
        ))
        self.live_state["llm_source"] = llm_source
        self.live_state["total_tasks_completed"] += 1
        self.live_state["status"] = "COMPLETED"
        self.live_state["progress_pct"] = 100
        self.add_live_log(f"Cycle {cycle} finalized: {action}")

    def invoke_tool(self, tool_name: str, state: Any, **kwargs) -> ToolResult:
        """
        Execute tool through registry with audit logging and live reporting.
        """
        self.add_live_log(f"Invoking analytical solver '{tool_name}'...")
        res = self.tool_registry.invoke(tool_name, state, caller_agent=self.agent_id, **kwargs)
        if res.success:
            self.add_live_log(f"Tool '{tool_name}' returned SUCCESS: {res.message[:65]}...")
        else:
            self.add_live_log(f"Tool '{tool_name}' encountered error: {res.error}")
        return res

    def send_message(
        self,
        recipient_id: str,
        intent: MessageIntent,
        subject: str,
        content: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        confidence: float = 1.0
    ) -> AgentMessage:
        """
        Send structured Agent Communication Protocol message.
        """
        msg = AgentMessage(
            sender_id=self.agent_id,
            sender_role=self.role,
            recipient_id=recipient_id,
            intent=intent,
            priority=priority,
            subject=subject,
            content=content,
            payload=payload or {},
            confidence=confidence
        )
        self.message_bus.send(msg)
        self.add_live_log(f"Sent ACP {intent.value} to '{recipient_id}': {subject}")
        return msg

    def broadcast(
        self,
        intent: MessageIntent,
        subject: str,
        content: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        confidence: float = 1.0
    ) -> AgentMessage:
        return self.send_message(
            recipient_id="broadcast",
            intent=intent,
            subject=subject,
            content=content,
            payload=payload,
            priority=priority,
            confidence=confidence
        )

    def step(self, blackboard: Blackboard, cycle: int):
        """
        Execute one operational cycle. Must be overridden by subclasses.
        """
        raise NotImplementedError("Each specialized agent must implement step().")

    def to_status_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "avatar_icon": self.avatar_icon,
            "color_accent": self.color_accent,
            "live_state": self.live_state,
            "recent_thoughts": [
                {
                    "time": t.timestamp,
                    "cycle": t.cycle,
                    "observation": t.observation,
                    "reasoning": t.reasoning,
                    "action": t.action_taken,
                    "llm_source": t.llm_source
                } for t in self.thought_log[-4:]
            ]
        }
