"""
Triage and Emergency Department Influx Forecaster Agent.
Monitors ED velocity, arrival acuity, and boarding buildup with live task visualization.
"""

from typing import Dict, Any, List
from ..framework.agent_base import BaseAgent
from ..framework.message_bus import MessageIntent, MessagePriority
from ..framework.blackboard import Blackboard
from ..framework.llm_client import llm_client
from ..models.patient import UnitType, AcuityLevel


class TriageInfluxAgent(BaseAgent):
    """
    Monitors ED throughput, identifies boarders, and requests inpatient bed pulls.
    """

    def __init__(self, tool_registry, message_bus):
        super().__init__(
            agent_id="triage_influx_agent",
            name="ED Triage & Influx Forecaster",
            role="Emergency Flow Specialist",
            system_prompt=(
                "You are the ED Triage & Influx Forecaster Agent for MetroHealth Medical Center. "
                "You monitor ED arrivals, ESI 1-5 acuity distribution, and detect hallway boarding delays. "
                "You formulate inpatient bed pull requests to prevent ambulance diversion."
            ),
            tool_registry=tool_registry,
            message_bus=message_bus,
            avatar_icon="🚑",
            color_accent="#f59e0b"
        )

    def step(self, blackboard: Blackboard, cycle: int):
        inbox = self.perceive(blackboard)
        state = blackboard.state
        
        self.set_live_task("Scanning ED arrival bays and triaging acuity", 25, "SCANNING_ARRIVALS", "Emergency Department")
        
        ed_patients = [p for p in state.patients.values() if p.current_unit == UnitType.ED]
        boarders = [p for p in ed_patients if p.is_ed_boarder]
        
        esi_counts = {
            "ESI_1": sum(1 for p in ed_patients if p.acuity == AcuityLevel.ESI_1_RESUSCITATION),
            "ESI_2": sum(1 for p in ed_patients if p.acuity == AcuityLevel.ESI_2_EMERGENT),
            "ESI_3": sum(1 for p in ed_patients if p.acuity == AcuityLevel.ESI_3_URGENT),
            "ESI_4": sum(1 for p in ed_patients if p.acuity == AcuityLevel.ESI_4_LESS_URGENT),
            "ESI_5": sum(1 for p in ed_patients if p.acuity == AcuityLevel.ESI_5_NON_URGENT)
        }

        self.add_live_log(f"Census check: {len(ed_patients)} patients in ED ({esi_counts['ESI_1']} ESI-1, {esi_counts['ESI_2']} ESI-2). {len(boarders)} boarding.")

        observation = (
            f"ED Census: {len(ed_patients)} patients. Boarders: {len(boarders)}. "
            f"Acuity: {esi_counts['ESI_1']} ESI-1, {esi_counts['ESI_2']} ESI-2, {esi_counts['ESI_3']} ESI-3."
        )

        llm_source = "CLINICAL_HEURISTIC"

        if len(boarders) >= 4:
            self.set_live_task(f"Formulating emergency bed pull for {len(boarders)} boarders", 65, "FORMULATING_PROPOSAL", "ED Hallways")
            avg_wait = sum(p.ed_boarding_hours for p in boarders) / len(boarders) if boarders else 0
            
            raw_reasoning = (
                f"Severe ED boarding detected ({len(boarders)} patients waiting avg {avg_wait:.1f} hrs). "
                f"Treatment bays occupied; incoming ambulance offload delay is critical."
            )
            
            # Optional live LLM enhancement if key is provided in .env
            reasoning = raw_reasoning
            if llm_client.is_api_configured():
                llm_eval = llm_client.generate_reasoning(
                    self.system_prompt,
                    f"Given {len(boarders)} admitted patients boarding in ED (mean wait {avg_wait:.1f}h) and ESI-2 count of {esi_counts['ESI_2']}, provide immediate tactical recommendation."
                )
                if llm_eval and llm_eval.get("text"):
                    reasoning = llm_eval["text"]
                    llm_source = llm_eval.get("source", "CLINICAL_HEURISTIC")

            # Post alert on blackboard
            blackboard.post_alert(
                alert_id="ALT_ED_BOARDING",
                title="Critical ED Boarding Buildup",
                severity="CRITICAL" if len(boarders) >= 8 else "HIGH",
                unit="ED",
                details=f"{len(boarders)} admitted patients waiting for inpatient beds. Mean wait: {avg_wait:.1f}h.",
                source_agent=self.name
            )

            # Record bottleneck
            blackboard.record_bottleneck(
                bottleneck_id="BN_ED_BOARDING",
                category="EMERGENCY_FLOW",
                location="Emergency Department",
                severity="CRITICAL" if len(boarders) >= 8 else "HIGH",
                impact=f"{len(boarders)} patients boarding. Ambulance offload delay risk.",
                root_cause="Inpatient beds occupied or pending cleaning turnaround."
            )

            # Sample the top boarders
            sample_boarder_names = ", ".join([p.name for p in boarders[:3]])
            self.add_live_log(f"Queued bed pulls for: {sample_boarder_names}...")

            # Issue proposal to pull patients to wards
            proposal_id = f"PROP_PULL_ED_{cycle}"
            actions = [
                {
                    "action_type": "PULL_ED_BOARDER_TO_WARD",
                    "patient_id": p.patient_id,
                    "target_unit": "MED_SURG" if not p.telemetry_required else "TELEMETRY",
                    "priority": 1 if p.acuity in [AcuityLevel.ESI_1_RESUSCITATION, AcuityLevel.ESI_2_EMERGENT] else 2
                } for p in boarders[:6]
            ]

            blackboard.post_proposal(
                proposal_id=proposal_id,
                agent_id=self.agent_id,
                title=f"Expedited Bed Pull for {len(actions)} ED Boarders",
                category="BED_ALLOCATION",
                actions=actions,
                rationale="Decompress ED bays to accommodate incoming ambulances and prevent divert.",
                projected_benefit="Frees up 6 ED bays, reducing ambulance offload delay by an estimated 45 mins."
            )

            self.set_live_task(f"Broadcasting proposal {proposal_id} to Ward & Chief Orchestrator", 90, "COLLABORATING", "Inpatient Wards")
            
            # Broadcast proposal to Ward Bed Placement and Chief Orchestrator
            self.broadcast(
                intent=MessageIntent.PROPOSAL,
                subject=f"Urgent Bed Request: {len(actions)} ED Boarders",
                content=f"Requesting immediate placement for {len(actions)} admitted boarders currently stuck in ED treatment bays.",
                payload={"proposal_id": proposal_id, "boarders_count": len(boarders)},
                priority=MessagePriority.HIGH
            )

            action_taken = f"Posted proposal {proposal_id} to transfer {len(actions)} boarders to inpatient beds."
        else:
            self.set_live_task("Monitoring ED triage velocity and ambulance intake", 100, "MONITORING", "ED Triage")
            reasoning = f"ED flow within acceptable limits ({len(boarders)} boarders). Normal operations."
            action_taken = "Monitoring triage queue and arrival velocity."

        self.log_thought(cycle, observation, reasoning, action_taken, llm_source=llm_source)
