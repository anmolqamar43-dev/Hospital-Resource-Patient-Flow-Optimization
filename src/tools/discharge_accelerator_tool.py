"""
Discharge Accelerator and Reverse Triage Intervention Tool.
"""

from typing import Dict, Any, List
from ..framework.tool_registry import BaseTool, ToolResult
from ..models.hospital_state import HospitalState
from ..models.patient import UnitType, DischargeBarrier, Patient


class DischargeAcceleratorTool(BaseTool):
    name = "discharge_accelerator"
    description = "Identifies discharge barriers and generates targeted operational interventions to expedite bed turnover."
    required_parameters = []

    def execute(self, state: HospitalState, **kwargs) -> ToolResult:
        candidates = [
            p for p in state.patients.values()
            if p.evaluate_discharge_readiness() and p.current_unit not in [UnitType.ED, UnitType.MICU, UnitType.SICU]
        ]

        interventions = []
        immediate_discharges = []

        for p in candidates:
            if p.discharge_barrier == DischargeBarrier.NONE:
                immediate_discharges.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "unit": p.current_unit.value,
                    "bed_id": p.assigned_bed_id,
                    "status": "READY_FOR_IMMEDIATE_DISCHARGE"
                })
            elif p.discharge_barrier == DischargeBarrier.PENDING_MED_RECONCILIATION:
                interventions.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "unit": p.current_unit.value,
                    "bed_id": p.assigned_bed_id,
                    "barrier": p.discharge_barrier.value,
                    "intervention": "Trigger 'Meds-to-Beds' expedited bedside pharmacy delivery.",
                    "estimated_time_saved_minutes": 75,
                    "priority": "HIGH"
                })
            elif p.discharge_barrier == DischargeBarrier.PENDING_TRANSPORT:
                interventions.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "unit": p.current_unit.value,
                    "bed_id": p.assigned_bed_id,
                    "barrier": p.discharge_barrier.value,
                    "intervention": "Dispatch contracted on-demand wheelchair/stretcher van transport service.",
                    "estimated_time_saved_minutes": 90,
                    "priority": "HIGH"
                })
            elif p.discharge_barrier == DischargeBarrier.PENDING_PHYSICIAN_SIGNOFF:
                interventions.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "unit": p.current_unit.value,
                    "bed_id": p.assigned_bed_id,
                    "barrier": p.discharge_barrier.value,
                    "intervention": "Page attending hospitalist for expedited digital discharge summary sign-off.",
                    "estimated_time_saved_minutes": 60,
                    "priority": "HIGH"
                })
            elif p.discharge_barrier == DischargeBarrier.AWAITING_SNF_BED:
                interventions.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "unit": p.current_unit.value,
                    "bed_id": p.assigned_bed_id,
                    "barrier": p.discharge_barrier.value,
                    "intervention": "Activate secondary regional SNF network liaison and expedite auth verification.",
                    "estimated_time_saved_minutes": 180,
                    "priority": "MEDIUM"
                })
            elif p.discharge_barrier == DischargeBarrier.PENDING_LAB_RESULT:
                interventions.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "unit": p.current_unit.value,
                    "bed_id": p.assigned_bed_id,
                    "barrier": p.discharge_barrier.value,
                    "intervention": "Flag pending discharge confirmation lab panel as STAT in Core Laboratory.",
                    "estimated_time_saved_minutes": 45,
                    "priority": "HIGH"
                })

        data = {
            "total_discharge_candidates": len(candidates),
            "immediate_discharge_count": len(immediate_discharges),
            "interventions_count": len(interventions),
            "immediate_discharges": immediate_discharges,
            "recommended_interventions": interventions,
            "potential_beds_unlocked": len(candidates)
        }

        return ToolResult(
            success=True,
            data=data,
            message=f"Analyzed {len(candidates)} discharge candidates. {len(immediate_discharges)} ready immediately; {len(interventions)} actionable interventions generated."
        )
