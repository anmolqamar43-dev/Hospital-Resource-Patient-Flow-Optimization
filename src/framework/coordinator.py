"""
Multi-Agent Orchestrator and Consensus Coordinator.
Drives the cyclic sense-think-collaborate-act loop across all hospital agents.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .agent_base import BaseAgent
from .blackboard import Blackboard
from .message_bus import MessageBus
from .tool_registry import ToolRegistry


class HospitalOrchestrator:
    """
    Coordinates multi-agent execution, structured consensus, and blackboard progression.
    """

    def __init__(
        self,
        blackboard: Blackboard,
        message_bus: MessageBus,
        tool_registry: ToolRegistry
    ):
        self.blackboard = blackboard
        self.message_bus = message_bus
        self.tool_registry = tool_registry
        self.agents: Dict[str, BaseAgent] = {}
        self.cycle_count: int = 0
        self.execution_log: List[Dict[str, Any]] = []

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.agent_id] = agent

    def run_cycle(self) -> Dict[str, Any]:
        """
        Runs one end-to-end multi-agent coordination cycle:
        Phase 1: Situational Assessment & Agent Perception
        Phase 2: Analysis & Proposal Generation
        Phase 3: Peer Review & Consensus Voting
        Phase 4: Executive Decision & Directive Execution
        Phase 5: State Reconciliation & Metric Recalculation
        """
        self.cycle_count += 1
        self.blackboard.cycle_count = self.cycle_count
        cycle_start = datetime.now()
        
        # Phase 1 & 2: Step domain agents (Uncertainty, Influx, ICU, Ward, Staffing)
        # Note: Uncertainty auditor steps first to tag any missing or corrupted data
        agent_execution_order = [
            "uncertainty_auditor",
            "triage_influx_agent",
            "icu_capacity_agent",
            "ward_bed_placement_agent",
            "staffing_optimizer_agent",
            "chief_flow_orchestrator"
        ]
        
        cycle_events = []
        for agt_id in agent_execution_order:
            agent = self.agents.get(agt_id)
            if agent:
                try:
                    agent.step(self.blackboard, self.cycle_count)
                    cycle_events.append({"agent": agt_id, "status": "COMPLETED"})
                except Exception as e:
                    cycle_events.append({"agent": agt_id, "status": "ERROR", "error": str(e)})

        # Recalculate metrics on updated state
        metrics = self.blackboard.state.calculate_metrics()
        
        summary = {
            "cycle": self.cycle_count,
            "timestamp": cycle_start.strftime("%H:%M:%S"),
            "hics_level": self.blackboard.state.hics_level.value,
            "agent_events": cycle_events,
            "active_alerts_count": sum(1 for a in self.blackboard.alerts if a["status"] == "ACTIVE"),
            "bottlenecks_count": len(self.blackboard.bottlenecks),
            "proposals_count": len(self.blackboard.proposals),
            "executed_actions_count": len(self.blackboard.executed_actions),
            "metrics": {
                "occupancy_rate_pct": round(metrics.overall_occupancy_rate * 100, 1),
                "icu_occupancy_pct": round(metrics.icu_occupancy_rate * 100, 1),
                "ed_boarding_count": metrics.ed_boarding_count,
                "icu_stepdown_ready": metrics.icu_stepdown_ready_count,
                "discharge_ready": metrics.discharge_ready_count,
                "violating_units": metrics.units_violating_nurse_ratio
            }
        }
        self.execution_log.append(summary)
        return summary
