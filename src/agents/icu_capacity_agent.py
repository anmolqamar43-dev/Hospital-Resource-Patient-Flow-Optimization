"""
ICU and Critical Care Capacity Coordinator Agent.
Protects critical care reserve, tracks ventilators, and coordinates safe step-down transfers with live task visualization.
"""

from typing import Dict, Any, List
from ..framework.agent_base import BaseAgent
from ..framework.message_bus import MessageIntent, MessagePriority
from ..framework.blackboard import Blackboard
from ..framework.llm_client import llm_client
from ..models.patient import UnitType


class ICUCapacityAgent(BaseAgent):
    """
    Manages ICU beds, ventilators, and coordinates patient transitions to step-down units.
    """

    def __init__(self, tool_registry, message_bus):
        super().__init__(
            agent_id="icu_capacity_agent",
            name="ICU & Critical Care Manager",
            role="Critical Care Resource Specialist",
            system_prompt=(
                "You are the ICU Capacity Manager Agent for MetroHealth Medical Center. "
                "You oversee Medical and Surgical ICUs, mechanical ventilators, and critical care reserves. "
                "You identify step-down ready patients based on extubation, low SOFA scores, and absence of vasopressors."
            ),
            tool_registry=tool_registry,
            message_bus=message_bus,
            avatar_icon="🫀",
            color_accent="#ef4444"
        )

    def step(self, blackboard: Blackboard, cycle: int):
        inbox = self.perceive(blackboard)
        state = blackboard.state
        
        self.set_live_task("Auditing ICU bed saturation, ventilators & ECMO circuits", 20, "SCANNING", "MICU & SICU")
        
        # Run ICU triage evaluation tool
        eval_result = self.invoke_tool("icu_stepdown_evaluator", state)
        stepdown_candidates = []
        if eval_result.success and eval_result.data:
            stepdown_candidates = eval_result.data.get("stepdown_candidates", [])

        # Calculate ICU capacity
        micu = state.units.get("unit_micu")
        sicu = state.units.get("unit_sicu")
        
        total_icu_beds = (micu.total_physical_beds if micu else 0) + (sicu.total_physical_beds if sicu else 0)
        occupied_icu_beds = (micu.occupied_count if micu else 0) + (sicu.occupied_count if sicu else 0)
        available_icu_beds = total_icu_beds - occupied_icu_beds
        occ_rate_pct = (occupied_icu_beds / total_icu_beds * 100) if total_icu_beds > 0 else 0.0

        self.add_live_log(f"ICU census: {occupied_icu_beds}/{total_icu_beds} beds ({occ_rate_pct:.1f}%). Ventilators in use: {state.equipment.ventilators_in_use}/{state.equipment.ventilators_total}.")

        observation = (
            f"ICU Status: {occupied_icu_beds}/{total_icu_beds} beds occupied ({occ_rate_pct:.1f}%). "
            f"Available beds: {available_icu_beds}. Step-down ready patients: {len(stepdown_candidates)}. "
            f"Ventilators in use: {state.equipment.ventilators_in_use}/{state.equipment.ventilators_total}."
        )

        llm_source = "CLINICAL_HEURISTIC"

        # Vote on any pending proposals affecting ICU
        for prop_id, prop in blackboard.proposals.items():
            if prop["status"] == "PENDING_REVIEW" and self.agent_id not in prop["votes"]:
                if "ICU" in prop["title"] or any("ICU" in a.get("target_unit", "") for a in prop["actions"]):
                    if available_icu_beds <= 1:
                        blackboard.cast_vote(prop_id, self.agent_id, approved=False, reason="ICU at critical capacity; cannot accept non-emergent transfers.")
                        self.add_live_log(f"Voted NO on {prop_id}: Critical care reserve exhausted.")
                    else:
                        blackboard.cast_vote(prop_id, self.agent_id, approved=True, reason="Sufficient critical care capacity available.")
                        self.add_live_log(f"Voted YES on {prop_id}: Critical care capacity verified.")

        # Check critical thresholds
        if occ_rate_pct >= 85.0 or available_icu_beds < 2:
            self.set_live_task(f"Decompressing ICU: Evaluating {len(stepdown_candidates)} stabilized patients", 60, "EVALUATING_SOFA", "Step-Down Unit")
            severity = "CRITICAL" if available_icu_beds <= 1 else "HIGH"
            
            raw_reasoning = (
                f"ICU capacity under severe strain ({occ_rate_pct:.1f}% occupied, {available_icu_beds} reserve beds). "
                f"Must transfer {len(stepdown_candidates)} stabilized patients to Step-Down to preserve emergency reserve."
            )

            # Optional live LLM enhancement if key is provided in .env
            reasoning = raw_reasoning
            if llm_client.is_api_configured():
                llm_eval = llm_client.generate_reasoning(
                    self.system_prompt,
                    f"ICU occupancy is at {occ_rate_pct:.1f}% with only {available_icu_beds} empty beds. {len(stepdown_candidates)} patients meet extubation and SOFA criteria. Formulate critical care stabilization directive."
                )
                if llm_eval and llm_eval.get("text"):
                    reasoning = llm_eval["text"]
                    llm_source = llm_eval.get("source", "CLINICAL_HEURISTIC")

            # Post alert
            blackboard.post_alert(
                alert_id="ALT_ICU_CAPACITY",
                title="Critical Care Capacity Alert",
                severity=severity,
                unit="ICU",
                details=f"ICU at {occ_rate_pct:.1f}% occupancy ({available_icu_beds} beds left). Reserve margin breached.",
                source_agent=self.name
            )

            # Record bottleneck if exit block
            if stepdown_candidates and available_icu_beds <= 2:
                blackboard.record_bottleneck(
                    bottleneck_id="BN_ICU_EXIT_BLOCK",
                    category="CRITICAL_CARE",
                    location="MICU / SICU",
                    severity=severity,
                    impact=f"{len(stepdown_candidates)} stable patients waiting to transfer out. Blocks incoming cardiac/trauma admissions.",
                    root_cause="Downstream step-down and telemetry beds unavailable."
                )

            # Propose transfers
            if stepdown_candidates:
                proposal_id = f"PROP_ICU_STEPDOWN_{cycle}"
                actions = [
                    {
                        "action_type": "TRANSFER_TO_STEPDOWN",
                        "patient_id": cand["patient_id"],
                        "name": cand["name"],
                        "target_unit": cand["recommended_destination"],
                        "stability_score": cand["stability_score"]
                    } for cand in stepdown_candidates[:4]
                ]

                # Log candidate clinical details
                for cand in actions:
                    self.add_live_log(f"Step-down candidate: {cand['name']} (Stability Score {cand['stability_score']}) -> {cand['target_unit']}")

                blackboard.post_proposal(
                    proposal_id=proposal_id,
                    agent_id=self.agent_id,
                    title=f"Decompress ICU: Transfer {len(actions)} Stabilized Patients",
                    category="PATIENT_TRANSFER",
                    actions=actions,
                    rationale="Restore critical care reserve to >=2 beds by transferring patients meeting extubation and hemodynamic criteria.",
                    projected_benefit=f"Frees up {len(actions)} ICU beds, reducing ICU occupancy from {occ_rate_pct:.1f}% to {((occupied_icu_beds - len(actions))/total_icu_beds*100):.1f}%."
                )

                self.set_live_task(f"Negotiating transfer of {len(actions)} patients with Step-Down & Ward Coordinator", 90, "COLLABORATING", "Step-Down Unit")

                self.broadcast(
                    intent=MessageIntent.PROPOSAL,
                    subject=f"Urgent Transfer Request: {len(actions)} ICU Step-Downs",
                    content=f"Requesting Step-Down and Telemetry bed allocation for {len(actions)} clinically stable ICU patients.",
                    payload={"proposal_id": proposal_id, "candidates": actions},
                    priority=MessagePriority.HIGH
                )
                action_taken = f"Issued proposal {proposal_id} to transfer {len(actions)} patients to Step-Down."
            else:
                action_taken = "No ICU patients meet step-down clinical stability criteria; alerting Chief Orchestrator of critical care block."
        else:
            self.set_live_task("ICU operating within safe buffer; monitoring ventilators & vitals", 100, "MONITORING", "MICU/SICU")
            reasoning = f"ICU operating smoothly within safe thresholds ({available_icu_beds} beds free)."
            action_taken = "Continuous monitoring of ventilator metrics and hemodynamic stability."

        self.log_thought(cycle, observation, reasoning, action_taken, llm_source=llm_source)
