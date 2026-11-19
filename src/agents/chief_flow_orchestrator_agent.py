"""
Chief Flow Orchestrator and Operations Director Agent.
Synthesizes hospital-wide situational intelligence, arbitrates cross-unit disputes,
manages HICS alert levels, and authorizes coordinated operational directives with live task reporting.
"""

from typing import Dict, Any, List
from ..framework.agent_base import BaseAgent
from ..framework.message_bus import MessageIntent, MessagePriority
from ..framework.blackboard import Blackboard
from ..framework.llm_client import llm_client
from ..models.hospital_state import HICSAlertLevel


class ChiefFlowOrchestratorAgent(BaseAgent):
    """
    Hospital Operations Director and Flow Incident Commander.
    Makes definitive executive decisions, resolves conflicts, and executes optimal flow bundles.
    """

    def __init__(self, tool_registry, message_bus):
        super().__init__(
            agent_id="chief_flow_orchestrator",
            name="Chief Flow Orchestrator",
            role="Hospital Operations Director & Incident Commander",
            system_prompt=(
                "You are the Chief Flow Orchestrator and Hospital Operations Director for MetroHealth Medical Center. "
                "You synthesize intelligence from ED, ICU, Inpatient Wards, Staffing, and Uncertainty agents. "
                "You arbitrate conflicting priorities, determine the HICS operational status, "
                "and approve coordinated action plans."
            ),
            tool_registry=tool_registry,
            message_bus=message_bus,
            avatar_icon="⚖️",
            color_accent="#3b82f6"
        )

    def step(self, blackboard: Blackboard, cycle: int):
        inbox = self.perceive(blackboard)
        state = blackboard.state
        
        self.set_live_task("Synthesizing situational intelligence & auditing active bottlenecks", 30, "SYNTHESIZING", "Hospital Command")
        
        # Run bottleneck detection tool for full situational picture
        bn_result = self.invoke_tool("bottleneck_detector", state)
        bottlenecks = bn_result.data.get("bottlenecks", []) if bn_result.success else []

        # Recalculate operational metrics
        metrics = state.calculate_metrics()

        # 1. Determine HICS Alert Level
        new_level = HICSAlertLevel.NORMAL
        
        if (
            metrics.icu_occupancy_rate >= 0.98 and
            metrics.ed_boarding_count >= 10 and
            state.equipment.ventilators_available <= 2
        ):
            new_level = HICSAlertLevel.RED_CRISIS
        elif (
            metrics.icu_occupancy_rate >= 0.92 or
            metrics.overall_occupancy_rate >= 0.90 or
            metrics.ed_boarding_count >= 8 or
            len(metrics.units_violating_nurse_ratio) >= 2
        ):
            new_level = HICSAlertLevel.ORANGE_DIVERT
        elif (
            metrics.icu_occupancy_rate >= 0.85 or
            metrics.overall_occupancy_rate >= 0.82 or
            metrics.ed_boarding_count >= 4
        ):
            new_level = HICSAlertLevel.YELLOW_SURGE

        old_level = state.hics_level
        state.hics_level = new_level

        level_changed = (old_level != new_level)
        if level_changed:
            self.add_live_log(f"HICS Posture Escalation: Transitioned from {old_level.value} -> {new_level.value}!")
            blackboard.post_alert(
                alert_id="ALT_HICS_STATUS_CHANGE",
                title=f"Hospital Status Escalation: {new_level.value}",
                severity="CRITICAL" if new_level in [HICSAlertLevel.ORANGE_DIVERT, HICSAlertLevel.RED_CRISIS] else "HIGH",
                unit="HOSPITAL_WIDE",
                details=f"Command center transitioned from {old_level.value} to {new_level.value} based on multi-agent clinical flow analytics.",
                source_agent=self.name
            )
        else:
            self.add_live_log(f"Current HICS Posture confirmed: {new_level.value}")

        # 2. Review all pending proposals and execute coordinated bundling
        self.set_live_task(f"Conducting consensus voting arbitration for {len(blackboard.proposals)} proposals", 65, "ARBITRATING", "Executive Command")
        approved_proposals = []
        pending_props = [p for p in blackboard.proposals.values() if p["status"] == "PENDING_REVIEW"]

        for prop in pending_props:
            prop_id = prop["proposal_id"]
            votes = prop["votes"]
            rejections = [v for v in votes.values() if not v["approved"]]
            
            if not rejections:
                prop["status"] = "APPROVED"
                approved_proposals.append(prop)
                self.add_live_log(f"Executive Approval: {prop['title']} [Unanimous peer consensus].")
                blackboard.commit_action(
                    action_id=f"ACT_{prop_id}",
                    executor_agent=self.name,
                    summary=f"Approved and ordered execution: {prop['title']}",
                    impact_details={
                        "category": prop["category"],
                        "projected_benefit": prop["projected_benefit"],
                        "actions_count": len(prop["actions"])
                    }
                )
            else:
                if new_level in [HICSAlertLevel.YELLOW_SURGE, HICSAlertLevel.ORANGE_DIVERT, HICSAlertLevel.RED_CRISIS]:
                    prop["status"] = "APPROVED_WITH_OVERRIDE"
                    approved_proposals.append(prop)
                    self.add_live_log(f"Executive Override Authorized: {prop['title']} under {new_level.value} protocol.")
                    blackboard.commit_action(
                        action_id=f"ACT_{prop_id}_OVERRIDE",
                        executor_agent=self.name,
                        summary=f"Executive Incident Commander Override: Authorized {prop['title']} under {new_level.value} protocol.",
                        impact_details={
                            "category": prop["category"],
                            "override_reason": "Emergency surge mandates bed clearing; pairing with float pool nurse support.",
                            "actions_count": len(prop["actions"])
                        }
                    )
                else:
                    prop["status"] = "REJECTED"
                    self.add_live_log(f"Proposal Rejected: {prop['title']} failed safety consensus.")

        # 3. Formulate Executive Directive Broadcast
        observation = (
            f"Hospital Status: {new_level.value}. Occupancy: {metrics.overall_occupancy_rate*100:.1f}%. "
            f"ICU: {metrics.icu_occupancy_rate*100:.1f}%. ED Boarders: {metrics.ed_boarding_count}. "
            f"Bottlenecks detected: {len(bottlenecks)}. Approved proposals: {len(approved_proposals)}."
        )

        raw_reasoning = (
            f"Under {new_level.value} conditions, synchronized reverse triage is required: "
            f"Accelerating ward discharges simultaneously frees capacity for ICU step-downs and ED boarders."
        )

        llm_source = "CLINICAL_HEURISTIC"
        reasoning = raw_reasoning
        if llm_client.is_api_configured():
            llm_eval = llm_client.generate_reasoning(
                self.system_prompt,
                f"As Hospital Operations Incident Commander under HICS {new_level.value}, occupancy {metrics.overall_occupancy_rate*100:.1f}%, ICU {metrics.icu_occupancy_rate*100:.1f}%, ED boarders {metrics.ed_boarding_count}. Issue executive strategic flow directive."
            )
            if llm_eval and llm_eval.get("text"):
                reasoning = llm_eval["text"]
                llm_source = llm_eval.get("source", "CLINICAL_HEURISTIC")

        action_taken = (
            f"Set HICS level to {new_level.value}. Approved {len(approved_proposals)} strategic proposals. "
            f"Issued executive flow directive to department leads."
        )

        self.set_live_task(f"HICS {new_level.value} Strategic Directives Active & Broadcasted", 100, "DIRECTIVE_ACTIVE", "Hospital-Wide")

        self.broadcast(
            intent=MessageIntent.DIRECTIVE,
            subject=f"Executive Flow Directive - HICS {new_level.value}",
            content=(
                f"Operations Directive: Execute approved discharge accelerations, ICU step-downs, "
                f"and ED boarder pulls. Current hospital occupancy: {metrics.overall_occupancy_rate*100:.1f}%, "
                f"ICU: {metrics.icu_occupancy_rate*100:.1f}%."
            ),
            payload={
                "hics_level": new_level.value,
                "approved_proposals": [p["proposal_id"] for p in approved_proposals],
                "active_bottlenecks": len(bottlenecks)
            },
            priority=MessagePriority.CRITICAL if new_level != HICSAlertLevel.NORMAL else MessagePriority.NORMAL
        )

        self.log_thought(cycle, observation, reasoning, action_taken, llm_source=llm_source)
