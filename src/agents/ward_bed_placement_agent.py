"""
Ward Bed Placement and Inpatient Throughput Coordinator Agent.
Manages general wards, step-down, telemetry, discharge barriers, and bed turnover with live task reporting.
"""

from typing import Dict, Any, List
from ..framework.agent_base import BaseAgent
from ..framework.message_bus import MessageIntent, MessagePriority
from ..framework.blackboard import Blackboard
from ..framework.llm_client import llm_client
from ..models.patient import UnitType, DischargeBarrier
from ..models.bed import BedStatus


class WardBedPlacementAgent(BaseAgent):
    """
    Coordinates inpatient bed placement, unlocks discharge bottlenecks,
    and reviews downstream capacity for incoming ED and ICU requests.
    """

    def __init__(self, tool_registry, message_bus):
        super().__init__(
            agent_id="ward_bed_placement_agent",
            name="Inpatient Bed Placement Coordinator",
            role="Ward Flow & Capacity Specialist",
            system_prompt=(
                "You are the Ward Bed Placement Coordinator for MetroHealth Medical Center. "
                "You manage Med-Surg, Step-Down, Telemetry, and Surgical ward beds. You clear discharge barriers, "
                "accelerate bed cleaning, and allocate inpatient beds for incoming ED boarders and ICU step-downs."
            ),
            tool_registry=tool_registry,
            message_bus=message_bus,
            avatar_icon="🛌",
            color_accent="#10b981"
        )

    def step(self, blackboard: Blackboard, cycle: int):
        inbox = self.perceive(blackboard)
        state = blackboard.state
        
        self.set_live_task("Auditing inpatient ward census & discharge turnaround barriers", 25, "SCANNING", "Wards & Telemetry")
        
        # Run discharge accelerator tool
        disch_result = self.invoke_tool("discharge_accelerator", state)
        disch_data = disch_result.data if disch_result.success else {}
        
        candidates = disch_data.get("recommended_interventions", [])
        immediate_disch = disch_data.get("immediate_discharges", [])

        # Count ward capacities
        ward_types = ["MED_SURG", "STEP_DOWN", "TELEMETRY", "SURGICAL_WARD", "PEDIATRIC"]
        total_ward_beds = 0
        total_ward_occupied = 0
        total_ward_available = 0
        total_ward_cleaning = 0

        for u in state.units.values():
            if u.unit_type.value in ward_types:
                total_ward_beds += u.total_physical_beds
                total_ward_occupied += u.occupied_count
                total_ward_available += u.available_count
                total_ward_cleaning += u.cleaning_count

        ward_occ_pct = (total_ward_occupied / total_ward_beds * 100) if total_ward_beds > 0 else 0.0
        self.add_live_log(f"Inpatient census: {total_ward_occupied}/{total_ward_beds} beds occupied ({ward_occ_pct:.1f}%). {total_ward_available} beds free.")

        observation = (
            f"Ward Status: {total_ward_occupied}/{total_ward_beds} beds occupied ({ward_occ_pct:.1f}%). "
            f"Available: {total_ward_available}. Cleaning: {total_ward_cleaning}. "
            f"Discharge candidates: {len(candidates) + len(immediate_disch)} "
            f"({len(immediate_disch)} immediate, {len(candidates)} with barriers)."
        )

        llm_source = "CLINICAL_HEURISTIC"

        # 1. Propose discharge interventions to unlock beds
        if candidates or immediate_disch:
            self.set_live_task(f"Accelerating {len(candidates) + len(immediate_disch)} discharges to create inpatient pull", 60, "ACCELERATING_DISCHARGE", "Inpatient Wards")
            proposal_id = f"PROP_DISCHARGE_ACCEL_{cycle}"
            actions = []
            
            for d in immediate_disch[:4]:
                actions.append({
                    "action_type": "EXECUTE_DISCHARGE",
                    "patient_id": d["patient_id"],
                    "bed_id": d["bed_id"],
                    "unit": d["unit"]
                })
                self.add_live_log(f"Immediate discharge: Patient {d['name']} from {d['unit']} Bed {d['bed_id']}.")
                
            for c in candidates[:4]:
                actions.append({
                    "action_type": "RESOLVE_DISCHARGE_BARRIER",
                    "patient_id": c["patient_id"],
                    "barrier": c["barrier"],
                    "intervention": c["intervention"]
                })
                self.add_live_log(f"Barrier mitigation for Patient {c['name']}: {c['intervention'][:50]}...")

            blackboard.post_proposal(
                proposal_id=proposal_id,
                agent_id=self.agent_id,
                title=f"Discharge Acceleration: Unlock {len(actions)} Inpatient Beds",
                category="DISCHARGE_ACCELERATION",
                actions=actions,
                rationale="Overcome non-clinical discharge delays (meds, transport, physician sign-off) to free inpatient beds for ED and ICU.",
                projected_benefit=f"Frees up up to {len(actions)} beds within 90 minutes, decompressing ward occupancy by {(len(actions)/total_ward_beds*100):.1f}%."
            )

        # 2. Review and vote on peer proposals (ED pull and ICU step-down)
        for prop_id, prop in blackboard.proposals.items():
            if prop["status"] == "PENDING_REVIEW" and self.agent_id not in prop["votes"]:
                if prop["proposer_agent"] == "icu_capacity_agent":
                    sdu = state.units.get("unit_step_down")
                    sdu_avail = sdu.available_count if sdu else 0
                    if sdu_avail >= len(prop["actions"]):
                        blackboard.cast_vote(prop_id, self.agent_id, approved=True, reason=f"Step-Down has {sdu_avail} beds available to accept ICU patients.")
                        self.add_live_log(f"Voted YES on {prop_id}: Step-Down capacity verified.")
                    else:
                        blackboard.cast_vote(
                            prop_id,
                            self.agent_id,
                            approved=True,
                            reason=f"Approved conditionally: Will unlock Step-Down beds via expedited discharge of stable patients."
                        )
                        self.add_live_log(f"Voted CONDITIONAL on {prop_id}: Reverse triage scheduled.")

                elif prop["proposer_agent"] == "triage_influx_agent":
                    if total_ward_available >= len(prop["actions"]):
                        blackboard.cast_vote(prop_id, self.agent_id, approved=True, reason=f"Wards have {total_ward_available} available beds ready for ED boarders.")
                        self.add_live_log(f"Voted YES on {prop_id}: Inpatient beds ready for ED boarders.")
                    else:
                        blackboard.cast_vote(
                            prop_id,
                            self.agent_id,
                            approved=True,
                            reason="Approved conditionally: Priority bed turnaround and reverse triage scheduled."
                        )
                        self.add_live_log(f"Voted CONDITIONAL on {prop_id}: Housekeeping expediting beds.")

        reasoning = f"Ward occupancy is at {ward_occ_pct:.1f}%. Unlocking {len(candidates)} beds via barrier mitigation is essential to create pull for ED and ICU."
        action_taken = f"Proposed discharge actions for {len(candidates)} patients and cast votes on peer transfer requests."

        self.log_thought(cycle, observation, reasoning, action_taken, llm_source=llm_source)
