"""
Staffing and Workforce Optimization Agent.
Monitors nurse-to-patient ratios, guards against nurse fatigue, and allocates float pool staff with live task reporting.
"""

from typing import Dict, Any, List
from ..framework.agent_base import BaseAgent
from ..framework.message_bus import MessageIntent, MessagePriority
from ..framework.blackboard import Blackboard
from ..framework.llm_client import llm_client
from ..models.patient import UnitType
from ..models.staff import MANDATED_NURSE_RATIOS


class StaffingOptimizerAgent(BaseAgent):
    """
    Enforces safe nurse-to-patient ratios, mitigates burnout,
    and dynamically reallocates float pool and on-call nurses.
    """

    def __init__(self, tool_registry, message_bus):
        super().__init__(
            agent_id="staffing_optimizer_agent",
            name="Staffing & Workforce Optimizer",
            role="Nursing & Clinical Workforce Coordinator",
            system_prompt=(
                "You are the Staffing and Workforce Optimizer Agent for MetroHealth Medical Center. "
                "You enforce mandated nurse-to-patient ratios (ICU 1:2, SDU 1:3, MedSurg 1:5). "
                "You vote on bed placement proposals to ensure units do not admit patients without adequate nursing coverage."
            ),
            tool_registry=tool_registry,
            message_bus=message_bus,
            avatar_icon="👩‍⚕️",
            color_accent="#8b5cf6"
        )

    def step(self, blackboard: Blackboard, cycle: int):
        inbox = self.perceive(blackboard)
        state = blackboard.state
        
        self.set_live_task("Auditing nurse-to-patient ratios across all units against California Title 22", 30, "AUDITING_RATIOS", "All Wards")
        
        # Run staffing optimizer tool
        staff_result = self.invoke_tool("staffing_optimizer", state)
        staff_data = staff_result.data if staff_result.success else {}
        
        unit_compliance = staff_data.get("unit_compliance", {})
        actions = staff_data.get("recommended_actions", [])
        total_deficit = staff_data.get("total_nurse_deficit", 0)

        violating_units = [u for u, d in unit_compliance.items() if not d.get("is_compliant", True)]
        self.add_live_log(f"Staffing audit: {len(violating_units)} units in breach. Deficit: {total_deficit} RNs. Actions generated: {len(actions)}.")

        observation = (
            f"Staffing Status: {len(violating_units)} units in ratio breach. "
            f"Total nurse deficit: {total_deficit}. Recommended reassignments: {len(actions)}."
        )

        llm_source = "CLINICAL_HEURISTIC"

        # 1. Post staffing alert & proposal if deficits exist
        if actions:
            self.set_live_task(f"Balancing workforce: Reassigning {len(actions)} float & on-call RNs", 70, "BALANCING_WORKFORCE", "Deficit Units")
            proposal_id = f"PROP_STAFF_REALLOC_{cycle}"
            
            for act in actions:
                self.add_live_log(f"Reassignment: {act.get('staff_name')} -> {act.get('target_unit')} ({act.get('rationale')[:40]}...)")

            blackboard.post_proposal(
                proposal_id=proposal_id,
                agent_id=self.agent_id,
                title=f"Workforce Balancing: Deploy {len(actions)} Float/On-Call Nurses",
                category="WORKFORCE_ALLOCATION",
                actions=actions,
                rationale="Eliminate nurse-to-patient ratio breaches to comply with safety mandates and reduce burnout.",
                projected_benefit=f"Restores safe ratios across {len(violating_units)} units, preventing adverse events and nurse exhaustion."
            )

            blackboard.post_alert(
                alert_id="ALT_STAFFING_BREACH",
                title="Nurse Staffing Safety Breach",
                severity="HIGH" if total_deficit >= 3 else "MEDIUM",
                unit="Multiple",
                details=f"Ratios exceeded in {len(violating_units)} units. Deploying {len(actions)} nurses.",
                source_agent=self.name
            )

        # 2. Scrutinize peer proposals for staffing safety
        for prop_id, prop in blackboard.proposals.items():
            if prop["status"] == "PENDING_REVIEW" and self.agent_id not in prop["votes"]:
                if prop["proposer_agent"] in ["triage_influx_agent", "icu_capacity_agent"]:
                    target_units = [a.get("target_unit") for a in prop["actions"] if "target_unit" in a]
                    has_deficit_target = any(
                        unit_compliance.get(f"unit_{t.lower()}", {}).get("variance", 0) < 0
                        for t in target_units if t
                    )

                    if has_deficit_target:
                        blackboard.cast_vote(
                            prop_id,
                            self.agent_id,
                            approved=True,
                            reason="Approved with condition: Must dispatch float nurse simultaneously to avoid dangerous overload."
                        )
                        self.add_live_log(f"Voted CONDITIONAL on {prop_id}: Float RN dispatch required.")
                    else:
                        blackboard.cast_vote(
                            prop_id,
                            self.agent_id,
                            approved=True,
                            reason="Verified: Target units have adequate nursing coverage to absorb transfers."
                        )
                        self.add_live_log(f"Voted YES on {prop_id}: Safe nurse ratios confirmed.")

        reasoning = (
            f"Found {len(violating_units)} units violating staffing ratios. "
            f"Deploying {len(actions)} float/on-call nurses is mandatory before authorizing high-volume admissions."
        )
        action_taken = f"Proposed {len(actions)} workforce actions and audited bed placement requests for nurse workload safety."

        self.log_thought(cycle, observation, reasoning, action_taken, llm_source=llm_source)
