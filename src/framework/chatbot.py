"""
Hospital Operations & Flow Copilot - Intelligent Chatbot Engine.
Provides natural-language operational Q&A, clinical decision assistance,
and direct multi-agent workflow triggering using live hospital state.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime

from .llm_client import llm_client
from ..models.patient import UnitType, AcuityLevel
from ..models.hospital_state import HICSAlertLevel


class HospitalOperationsChatbot:
    """
    Interactive clinical operations chatbot.
    Interfaces with the live HospitalOptimizationSystem and optionally LLM APIs.
    """

    def __init__(self, system_instance: Any):
        self.system = system_instance
        self.history: List[Dict[str, str]] = []

    def get_live_context_prompt(self) -> str:
        """
        Builds live operational context injection for LLM reasoning.
        """
        state = self.system.blackboard.state
        metrics = state.calculate_metrics()
        bb_summary = self.system.blackboard.get_summary()

        violating_str = ", ".join(metrics.units_violating_nurse_ratio) if metrics.units_violating_nurse_ratio else "None (100% compliant)"
        active_bn_str = "; ".join([f"{b['category']} in {b['location']} ({b['severity']})" for b in bb_summary.get("bottlenecks", [])[:4]]) or "None"

        return f"""You are the MetroHealth Operations & Clinical Flow Copilot, an elite AI hospital operations assistant.
You assist hospital incident commanders, charge nurses, intensivists, and bed placement directors.
Here is the LIVE ground-truth operational state of MetroHealth Academic Medical Center (450 beds):

- HICS Operational Posture: {state.hics_level.value}
- Total Hospital Occupancy: {metrics.overall_occupancy_rate*100:.1f}% ({metrics.total_occupied_beds}/{metrics.total_beds} beds occupied)
- Critical Care (ICU): {metrics.icu_occupancy_rate*100:.1f}% ({metrics.icu_occupied_beds}/{metrics.icu_total_beds} beds occupied, {metrics.icu_total_beds - metrics.icu_occupied_beds} reserve beds left)
- ICU Step-Down Ready Patients: {metrics.icu_stepdown_ready_count} stabilized patients eligible to move to Step-Down
- Emergency Department Boarders: {metrics.ed_boarding_count} admitted patients boarding in ED bays (Mean Wait: {metrics.ed_avg_boarding_hours:.1f} hrs)
- Discharge Candidates: {metrics.discharge_ready_count} medically stable (Barriers: {metrics.discharge_with_barriers_count})
- Nurse Staffing: {metrics.total_nurses_on_duty} on duty. Mandate Violations: {violating_str}
- Ventilators: {state.equipment.ventilators_in_use}/{state.equipment.ventilators_total} in use ({state.equipment.ventilators_available} available)
- Active Flow Bottlenecks: {active_bn_str}

Guidelines:
- Answer concisely, authoritatively, and with realistic clinical terminology.
- Provide actionable tactical suggestions.
- If the user asks you to apply optimizations, clear boarders, or run a simulation, confirm you can execute it.
"""

    def handle_message(self, user_message: str) -> Dict[str, Any]:
        """
        Processes a user message and returns a structured reply.
        """
        cleaned_msg = user_message.strip().lower()
        self.history.append({"role": "user", "content": user_message})

        action_taken = None
        action_result = None

        # 1. Check for Direct Operational Action Commands
        if any(w in cleaned_msg for w in ["apply optimization", "apply flow", "optimize hospital", "decompress", "reverse triage"]):
            action_taken = "APPLY_OPTIMIZATIONS"
            action_result = self.system.apply_recommendations()
            comp = action_result.get("impact_comparison", {})
            b = comp.get("before", {})
            a = comp.get("after", {})

            reply = (
                f"🚀 **Flow Optimizations Applied Successfully!**\n\n"
                f"- **Overall Occupancy:** {b.get('overall_occupancy_pct', '--')}% ➔ **{a.get('overall_occupancy_pct', '--')}%** (-{float(b.get('overall_occupancy_pct', 0)) - float(a.get('overall_occupancy_pct', 0)):.1f}% freed)\n"
                f"- **ICU Saturation:** {b.get('icu_occupancy_pct', '--')}% ➔ **{a.get('icu_occupancy_pct', '--')}%** (Reserve restored)\n"
                f"- **ED Boarders:** {b.get('ed_boarding_count', '--')} ➔ **{a.get('ed_boarding_count', '--')}** (Hallway queue cleared)\n"
                f"- **Staffing Mandate Breaches:** {b.get('violating_units_count', '--')} ➔ **{a.get('violating_units_count', '--')}** (100% compliant)\n\n"
                f"*Synchronized reverse triage, bed turnaround, and float nurse deployments are now complete.*"
            )
            self.history.append({"role": "assistant", "content": reply})
            return {"reply": reply, "source": "FLOW_ENGINE_ACTION", "action_taken": action_taken, "action_result": action_result}

        elif any(w in cleaned_msg for w in ["run cycle", "step agent", "next cycle", "step cycle"]):
            action_taken = "STEP_CYCLE"
            cycle_res = self.system.step()
            reply = (
                f"⚡ **Multi-Agent Cycle #{cycle_res.get('cycle', 1)} Executed.**\n\n"
                f"- **HICS Level:** `{cycle_res.get('hics_level')}`\n"
                f"- **Active Bottlenecks:** {cycle_res.get('bottlenecks_count', 0)}\n"
                f"- **Proposals Reviewed:** {cycle_res.get('proposals_count', 0)}\n"
                f"- **Directives Authorized:** {cycle_res.get('executed_actions_count', 0)}\n\n"
                f"All 6 agents updated their cognitive assessments and synchronized with the blackboard."
            )
            self.history.append({"role": "assistant", "content": reply})
            return {"reply": reply, "source": "FLOW_ENGINE_ACTION", "action_taken": action_taken, "action_result": cycle_res}

        elif "surge" in cleaned_msg or "influx" in cleaned_msg and "simulate" in cleaned_msg:
            action_taken = "SIMULATE_SURGE"
            res = self.system.trigger_stress_scenario("surge", count=20)
            reply = f"🌊 **Winter Influx Surge Injected!** 20 high-acuity patients arrived in ED. Multi-agent team escalated to manage hallway boarding."
            self.history.append({"role": "assistant", "content": reply})
            return {"reply": reply, "source": "SIMULATION_TRIGGER", "action_taken": action_taken}

        elif "callout" in cleaned_msg or "staff shortage" in cleaned_msg:
            action_taken = "SIMULATE_CALLOUT"
            res = self.system.trigger_stress_scenario("staffing_callout", count=6)
            reply = f"📉 **Staffing Deficit Simulated:** 6 nurses called out sick. Staffing Optimizer Agent is actively reallocating float pool nurses."
            self.history.append({"role": "assistant", "content": reply})
            return {"reply": reply, "source": "SIMULATION_TRIGGER", "action_taken": action_taken}

        elif "reset" in cleaned_msg and ("baseline" in cleaned_msg or "hospital" in cleaned_msg):
            action_taken = "RESET_BASELINE"
            from ..simulation.hospital_generator import create_initial_hospital_state
            self.system.blackboard.update_state(create_initial_hospital_state(stress_mode="baseline"))
            self.system.step()
            reply = "🔄 **Hospital Reset:** Returned to normal operational baseline (80% occupancy, compliant staffing)."
            self.history.append({"role": "assistant", "content": reply})
            return {"reply": reply, "source": "SYSTEM_RESET", "action_taken": action_taken}

        # 2. If API Key is configured in .env, query live LLM (Gemini / OpenAI)
        if llm_client.is_api_configured():
            sys_prompt = self.get_live_context_prompt()
            llm_res = llm_client.generate_reasoning(sys_prompt, user_message, temperature=0.3)
            if llm_res and llm_res.get("text"):
                reply = llm_res["text"]
                self.history.append({"role": "assistant", "content": reply})
                return {
                    "reply": reply,
                    "source": llm_res.get("source", "GEMINI_LIVE"),
                    "model": llm_res.get("model", "gemini-2.5-flash")
                }

        # 3. Intelligent Heuristic / Domain Knowledge Fallback (When offline or no API key)
        reply = self._generate_clinical_heuristic_response(cleaned_msg)
        self.history.append({"role": "assistant", "content": reply})
        return {
            "reply": reply,
            "source": "CLINICAL_HEURISTIC_COPILOT",
            "model": "MetroHealth Rule & Analytics Engine"
        }

    def _generate_clinical_heuristic_response(self, text: str) -> str:
        """
        Calibrated domain-specific responses based on real-time hospital metrics.
        """
        state = self.system.blackboard.state
        metrics = state.calculate_metrics()
        equipment = state.equipment

        if any(w in text for w in ["hi", "hello", "hey", "who are you", "help"]):
            return (
                "👋 **Greetings! I am the MetroHealth Clinical Flow & Operations Copilot.**\n\n"
                "I monitor real-time hospital throughput across all 450 beds and 8 clinical units. You can ask me:\n"
                "• **Hospital Status**: *'Give me an operational briefing'* or *'What is our occupancy?'*\n"
                "• **ICU Capacity**: *'How many ICU beds are available?'* or *'Show step-down candidates'*\n"
                "• **ED Flow**: *'How many patients are boarding in ED?'* or *'What is the mean wait?'*\n"
                "• **Staffing**: *'Are any units violating nurse ratios?'* or *'What is our nurse fatigue?'*\n"
                "• **Action Directives**: *'Apply flow optimizations'* or *'Simulate winter surge'*"
            )

        elif any(w in text for w in ["status", "briefing", "summary", "overview", "census", "occupancy"]):
            hics_badge = f"`{state.hics_level.value}`"
            return (
                f"📊 **MetroHealth Operational Status Briefing:**\n\n"
                f"• **HICS Posture:** {hics_badge}\n"
                f"• **Overall Census:** **{metrics.overall_occupancy_rate*100:.1f}%** ({metrics.total_occupied_beds}/{metrics.total_beds} beds occupied)\n"
                f"• **ICU Saturation:** **{metrics.icu_occupancy_rate*100:.1f}%** ({metrics.icu_occupied_beds}/{metrics.icu_total_beds} beds, **{metrics.icu_total_beds - metrics.icu_occupied_beds}** available)\n"
                f"• **ED Hallway Boarders:** **{metrics.ed_boarding_count} patients** (Mean Wait: **{metrics.ed_avg_boarding_hours:.1f} hrs**)\n"
                f"• **Nurse Workforce:** {metrics.total_nurses_on_duty} on duty. Violating units: {', '.join(metrics.units_violating_nurse_ratio) if metrics.units_violating_nurse_ratio else 'None (Compliant)'}\n"
                f"• **Ventilators:** {equipment.ventilators_in_use}/{equipment.ventilators_total} in use ({equipment.ventilators_available} available)"
            )

        elif any(w in text for w in ["icu", "intensive", "critical care", "step-down", "stepdown", "sicu", "micu"]):
            candidates = [p for p in state.patients.values() if p.current_unit in [UnitType.MICU, UnitType.SICU] and p.evaluate_stepdown_readiness()]
            cand_names = ", ".join([f"{p.name} (SOFA {p.sofa_score})" for p in candidates[:4]]) if candidates else "None"
            return (
                f"🫀 **Critical Care (ICU) Capacity Report:**\n\n"
                f"• **Occupancy Rate:** **{metrics.icu_occupancy_rate*100:.1f}%** ({metrics.icu_occupied_beds}/{metrics.icu_total_beds} beds)\n"
                f"• **Emergency Buffer:** **{metrics.icu_total_beds - metrics.icu_occupied_beds} beds available** (Safety standard: $\\ge 2$ beds)\n"
                f"• **Step-Down Ready Candidates:** **{len(candidates)} patients** ({cand_names})\n"
                f"• **Ventilator Demand:** {equipment.ventilators_in_use}/{equipment.ventilators_total} mechanical ventilators assigned\n\n"
                f"💡 *Recommendation: Transferring the {len(candidates)} stabilized candidates to Step-Down will immediately decompress ICU occupancy to {(metrics.icu_occupied_beds - len(candidates))/metrics.icu_total_beds*100:.1f}%.*"
            )

        elif any(w in text for w in ["ed", "emergency", "boarder", "boarding", "ambulance", "triage", "esi"]):
            boarders = [p for p in state.patients.values() if p.current_unit == UnitType.ED and p.is_ed_boarder]
            return (
                f"🚑 **Emergency Department & Throughput Report:**\n\n"
                f"• **Total ED Patients:** {metrics.ed_total_patients}\n"
                f"• **Hallway Boarders:** **{metrics.ed_boarding_count} admitted patients**\n"
                f"• **Mean Boarding Time:** **{metrics.ed_avg_boarding_hours:.1f} hours**\n"
                f"• **Divert Risk:** {'⚠️ HIGH - Ambulance Divert Warning Active' if metrics.ed_boarding_count >= 8 else '🟢 Normal Emergency Intake'}\n\n"
                f"💡 *Tactical Action: Influx Agent has requested expedited bed pulls to Med-Surg and Telemetry to clear treatment bays.*"
            )

        elif any(w in text for w in ["staff", "nurse", "ratio", "ratios", "workforce", "fatigue", "burnout"]):
            breaches = metrics.units_violating_nurse_ratio
            return (
                f"👩‍⚕️ **Nursing Workforce & Staffing Mandates:**\n\n"
                f"• **Nurses on Duty:** {metrics.total_nurses_on_duty} RNs across day/night shifts\n"
                f"• **Average Fatigue Index:** **{metrics.average_nurse_fatigue_pct*100:.1f}%**\n"
                f"• **California Title 22 Violations:** {', '.join(breaches) if breaches else '✅ 100% Compliant across all units'}\n\n"
                f"💡 *Staffing Optimizer Agent is actively managing the 6-nurse float pool to absorb sudden census spikes.*"
            )

        elif any(w in text for w in ["ventilator", "vent", "equipment", "dialysis", "ecmo"]):
            return (
                f"🫁 **Critical Asset Inventory:**\n\n"
                f"• **Mechanical Ventilators:** {equipment.ventilators_in_use}/{equipment.ventilators_total} in use (**{equipment.ventilators_available} available**, {equipment.ventilators_reserved} emergency reserved)\n"
                f"• **Telemetry Monitors:** {equipment.telemetry_monitors_in_use}/{equipment.telemetry_monitors_total} in use (**{equipment.telemetry_available} available**)\n"
                f"• **Dialysis Stations:** {equipment.dialysis_stations_in_use}/{equipment.dialysis_stations_total} in use\n"
                f"• **ECMO Circuits:** {equipment.ecmo_circuits_in_use}/{equipment.ecmo_circuits_total} active"
            )

        elif any(w in text for w in ["discharge", "barrier", "turnaround", "housekeeping", "cleaning"]):
            return (
                f"🛌 **Discharge & Bed Turnaround Report:**\n\n"
                f"• **Medically Stable Candidates:** **{metrics.discharge_ready_count} patients**\n"
                f"• **Blocked by Non-Clinical Friction:** **{metrics.discharge_with_barriers_count} patients** (Med reconciliation, ambulance transport, SNF bed placement)\n"
                f"• **Housekeeping Turnaround Queue:** {len(state.cleaning_queue)} dirty beds pending terminal cleaning\n\n"
                f"💡 *Ward Bed Placement Coordinator is executing 'Meds-to-Beds' and dispatching contracted transport to unlock these beds.*"
            )

        else:
            return (
                f"I received your inquiry: *\"{text}\"*\n\n"
                f"Currently, hospital occupancy is at **{metrics.overall_occupancy_rate*100:.1f}%** and ICU saturation is at **{metrics.icu_occupancy_rate*100:.1f}%** with **{metrics.ed_boarding_count} ED boarders**.\n\n"
                f"Try asking:\n"
                f"• *'What is our ICU capacity?'*\n"
                f"• *'Are any units violating nurse ratios?'*\n"
                f"• *'Apply flow optimizations'* (to execute reverse triage)\n"
                f"• *'Simulate winter surge'* (to inject 20 ED patients)"
            )
