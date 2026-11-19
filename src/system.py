"""
Hospital Flow & Resource Optimization System - Top-Level Orchestration Engine.
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .models.hospital_state import HospitalState
from .framework.message_bus import MessageBus
from .framework.blackboard import Blackboard
from .framework.tool_registry import ToolRegistry
from .framework.coordinator import HospitalOrchestrator

from .tools.census_tool import CensusTool
from .tools.icu_triage_tool import ICUTriageTool
from .tools.staffing_optimizer_tool import StaffingOptimizerTool
from .tools.bottleneck_detector_tool import BottleneckDetectorTool
from .tools.discharge_accelerator_tool import DischargeAcceleratorTool
from .tools.scenario_simulator_tool import ScenarioSimulatorTool

from .agents.uncertainty_auditor_agent import UncertaintyAuditorAgent
from .agents.triage_influx_agent import TriageInfluxAgent
from .agents.icu_capacity_agent import ICUCapacityAgent
from .agents.ward_bed_placement_agent import WardBedPlacementAgent
from .agents.staffing_optimizer_agent import StaffingOptimizerAgent
from .agents.chief_flow_orchestrator_agent import ChiefFlowOrchestratorAgent
from .simulation.hospital_generator import create_initial_hospital_state


class HospitalOptimizationSystem:
    """
    End-to-end multi-agent hospital operations and resource optimization system.
    """

    def __init__(self, stress_mode: str = "baseline"):
        self.message_bus = MessageBus()
        self.tool_registry = ToolRegistry()
        
        # 1. Register analytical and simulation tools
        self.tool_registry.register(CensusTool())
        self.tool_registry.register(ICUTriageTool())
        self.tool_registry.register(StaffingOptimizerTool())
        self.tool_registry.register(BottleneckDetectorTool())
        self.tool_registry.register(DischargeAcceleratorTool())
        self.tool_registry.register(ScenarioSimulatorTool())

        # 2. Initialize hospital ground truth state
        initial_state = create_initial_hospital_state(stress_mode=stress_mode)
        self.blackboard = Blackboard(initial_state=initial_state)

        # 3. Create Multi-Agent team
        self.agents = {
            "uncertainty_auditor": UncertaintyAuditorAgent(self.tool_registry, self.message_bus),
            "triage_influx_agent": TriageInfluxAgent(self.tool_registry, self.message_bus),
            "icu_capacity_agent": ICUCapacityAgent(self.tool_registry, self.message_bus),
            "ward_bed_placement_agent": WardBedPlacementAgent(self.tool_registry, self.message_bus),
            "staffing_optimizer_agent": StaffingOptimizerAgent(self.tool_registry, self.message_bus),
            "chief_flow_orchestrator": ChiefFlowOrchestratorAgent(self.tool_registry, self.message_bus)
        }

        # 4. Initialize Orchestrator
        self.orchestrator = HospitalOrchestrator(
            blackboard=self.blackboard,
            message_bus=self.message_bus,
            tool_registry=self.tool_registry
        )

        for agent in self.agents.values():
            self.orchestrator.register_agent(agent)

    def step(self) -> Dict[str, Any]:
        """
        Execute one complete collaborative multi-agent cycle.
        """
        return self.orchestrator.run_cycle()

    def apply_recommendations(self) -> Dict[str, Any]:
        """
        Applies approved flow recommendations and measures before/after impact.
        """
        pre_metrics = self.blackboard.state.calculate_metrics()
        
        result = self.tool_registry.invoke(
            "scenario_simulator",
            self.blackboard.state,
            action="APPLY_RECOMMENDED_FLOW_OPTIMIZATIONS"
        )
        
        # Step agents once to update situational perception post-optimization
        self.step()
        
        post_metrics = self.blackboard.state.calculate_metrics()
        
        return {
            "execution_result": result.to_dict(),
            "impact_comparison": {
                "before": {
                    "overall_occupancy_pct": round(pre_metrics.overall_occupancy_rate * 100, 1),
                    "icu_occupancy_pct": round(pre_metrics.icu_occupancy_rate * 100, 1),
                    "ed_boarding_count": pre_metrics.ed_boarding_count,
                    "icu_stepdown_ready": pre_metrics.icu_stepdown_ready_count,
                    "discharge_ready": pre_metrics.discharge_ready_count,
                    "violating_units_count": len(pre_metrics.units_violating_nurse_ratio)
                },
                "after": {
                    "overall_occupancy_pct": round(post_metrics.overall_occupancy_rate * 100, 1),
                    "icu_occupancy_pct": round(post_metrics.icu_occupancy_rate * 100, 1),
                    "ed_boarding_count": post_metrics.ed_boarding_count,
                    "icu_stepdown_ready": post_metrics.icu_stepdown_ready_count,
                    "discharge_ready": post_metrics.discharge_ready_count,
                    "violating_units_count": len(post_metrics.units_violating_nurse_ratio)
                }
            }
        }

    def trigger_stress_scenario(self, scenario_type: str, count: int = 15) -> Dict[str, Any]:
        """
        Injects real-time operational stress (surges, nurse call-outs, mass casualty).
        """
        action_map = {
            "surge": "SIMULATE_ED_SURGE",
            "staffing_callout": "SIMULATE_STAFFING_CALL_OUT",
            "mass_casualty": "SIMULATE_MASS_CASUALTY"
        }
        action = action_map.get(scenario_type, "SIMULATE_ED_SURGE")
        
        result = self.tool_registry.invoke(
            "scenario_simulator",
            self.blackboard.state,
            action=action,
            count=count
        )
        
        # Re-run a cycle to let agents react to the newly injected stress
        self.step()
        
        return result.to_dict()

    def step_single_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Executes a targeted task cycle for a single specific agent.
        """
        agent = self.agents.get(agent_id)
        if not agent:
            return {"success": False, "error": f"Agent '{agent_id}' not found"}

        self.blackboard.cycle_count += 1
        agent.step(self.blackboard, self.blackboard.cycle_count)
        return {
            "success": True,
            "agent_id": agent_id,
            "status": agent.live_state["status"],
            "active_task": agent.live_state["active_task"],
            "logs": agent.live_state["live_terminal_logs"]
        }

    def get_full_snapshot(self) -> Dict[str, Any]:
        """
        Complete snapshot for UI and analytical reporting.
        """
        from .framework.llm_client import llm_client
        state_dict = self.blackboard.state.to_summary_dict()
        bb_summary = self.blackboard.get_summary()
        
        # Collect recent agent status and live state
        agents_status = {aid: a.to_status_dict() for aid, a in self.agents.items()}
        
        # Message log
        messages = [m.to_dict() for m in self.message_bus.get_history(limit=25)]
        
        return {
            "hospital_summary": state_dict,
            "blackboard": bb_summary,
            "agents": agents_status,
            "messages": messages,
            "tools": self.tool_registry.list_tools(),
            "llm_config": llm_client.get_status_summary()
        }
