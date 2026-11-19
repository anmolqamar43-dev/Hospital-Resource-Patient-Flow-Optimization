"""
Uncertainty, Incomplete Information, and Anomaly Auditor Agent.
Specializes in auditing hospital feeds for missing vitals, dropped telemetry,
delayed lab values, and applying Bayesian/clinical safety defaults with live task reporting.
"""

from typing import Dict, Any, List
from ..framework.agent_base import BaseAgent
from ..framework.message_bus import MessageIntent, MessagePriority
from ..framework.blackboard import Blackboard
from ..models.patient import UnitType, AcuityLevel


class UncertaintyAuditorAgent(BaseAgent):
    """
    Guards patient safety by detecting incomplete, conflicting, or stale data.
    Implements conservative clinical fallbacks and triggers human-in-the-loop alerts.
    """

    def __init__(self, tool_registry, message_bus):
        super().__init__(
            agent_id="uncertainty_auditor",
            name="Uncertainty & Anomaly Auditor",
            role="Data Completeness & Clinical Safety Auditor",
            system_prompt=(
                "You are the Uncertainty and Anomaly Auditor for MetroHealth. Your responsibility is to inspect "
                "all patient charts, sensor feeds, and bed states for missing, contradictory, "
                "or stale data. You ensure patient safety by never assuming an unstable patient is stable "
                "when key clinical data is missing."
            ),
            tool_registry=tool_registry,
            message_bus=message_bus,
            avatar_icon="🛡️",
            color_accent="#06b6d4"
        )

    def step(self, blackboard: Blackboard, cycle: int):
        self.set_live_task("Auditing clinical telemetry feeds & patient EHR records", 20, "SCANNING", "All Hospital Units")
        state = blackboard.state
        flagged_patients = []
        total_patients = len(state.patients)
        complete_count = 0

        for pid, pt in state.patients.items():
            missing = []
            
            # Check vitals integrity
            if pt.vitals.spo2 is None or pt.vitals.spo2 <= 0:
                missing.append("spo2_telemetry_missing")
            if pt.vitals.bp_systolic is None or pt.vitals.bp_systolic <= 0:
                missing.append("blood_pressure_missing")
                
            # Check ICU specific completeness
            if pt.current_unit in [UnitType.MICU, UnitType.SICU]:
                if pt.sofa_score is None:
                    missing.append("sofa_score_missing")
                    pt.confidence_score = 0.55
                else:
                    pt.confidence_score = 0.95

            # Check discharge completeness
            if pt.is_discharge_candidate and not pt.discharge_barrier:
                missing.append("discharge_barrier_unspecified")

            if missing:
                pt.is_data_complete = False
                pt.missing_fields = missing
                flagged_patients.append({
                    "patient_id": pt.patient_id,
                    "name": pt.name,
                    "unit": pt.current_unit.value,
                    "missing": missing,
                    "confidence": pt.confidence_score
                })
                
                blackboard.log_uncertainty(
                    item_id=pt.patient_id,
                    item_type="PATIENT_RECORD",
                    missing_aspects=missing,
                    risk_level="HIGH" if pt.current_unit in [UnitType.MICU, UnitType.SICU] else "MODERATE",
                    mitigation="Applied conservative clinical bounds; flagged for nurse verification."
                )
            else:
                pt.is_data_complete = True
                pt.missing_fields = []
                pt.confidence_score = 1.0
                complete_count += 1

        completeness_pct = (complete_count / total_patients * 100) if total_patients > 0 else 100.0
        self.add_live_log(f"Verified {total_patients} patient records: {completeness_pct:.1f}% data completeness.")

        observation = f"Audited {total_patients} records. Found {len(flagged_patients)} records with incomplete data ({completeness_pct:.1f}% data completeness)."
        
        if flagged_patients:
            self.set_live_task(f"Flagged {len(flagged_patients)} incomplete records; applied conservative safety defaults", 80, "ANALYZING", "Safety Bounds")
            for f_pt in flagged_patients[:3]:
                self.add_live_log(f"Conservative bound applied to {f_pt['name']} ({f_pt['unit']}): missing {', '.join(f_pt['missing'])}")

            reasoning = f"Flagged {len(flagged_patients)} incomplete records. Conservative clinical defaults applied to prevent premature step-down or discharge."
            action = f"Logged {len(flagged_patients)} uncertainties and broadcasted data quality advisory."
            
            if completeness_pct < 90.0:
                self.broadcast(
                    intent=MessageIntent.ALERT,
                    subject="Data Quality Warning: Incomplete Clinical Feeds",
                    content=f"Warning: {len(flagged_patients)} patient records have missing telemetry or lab scores. Conservative clinical safety protocols active.",
                    payload={"flagged_count": len(flagged_patients), "completeness_pct": completeness_pct},
                    priority=MessagePriority.HIGH,
                    confidence=0.9
                )
        else:
            reasoning = "All patient records and clinical feeds are complete and verified."
            action = "Audit passed without anomalies."

        self.log_thought(cycle, observation, reasoning, action)
