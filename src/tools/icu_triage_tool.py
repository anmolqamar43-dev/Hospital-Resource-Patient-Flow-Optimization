"""
ICU Critical Care Triage and Step-Down Readiness Assessment Tool.
"""

from typing import Dict, Any, List
from ..framework.tool_registry import BaseTool, ToolResult
from ..models.hospital_state import HospitalState
from ..models.patient import UnitType, Patient


class ICUTriageTool(BaseTool):
    name = "icu_stepdown_evaluator"
    description = "Evaluates ICU patients for step-down readiness using clinical stabilization criteria."
    required_parameters = []

    def execute(self, state: HospitalState, **kwargs) -> ToolResult:
        icu_patients: List[Patient] = [
            p for p in state.patients.values()
            if p.current_unit in [UnitType.MICU, UnitType.SICU]
        ]

        stepdown_candidates = []
        high_acuity_patients = []
        incomplete_data_patients = []

        for p in icu_patients:
            # Check completeness
            if not p.is_data_complete or p.sofa_score is None:
                incomplete_data_patients.append({
                    "patient_id": p.patient_id,
                    "name": p.name,
                    "missing": p.missing_fields or ["sofa_score"],
                    "confidence": p.confidence_score
                })

            # Clinical criteria evaluation
            is_ready = p.evaluate_stepdown_readiness()
            
            # Clinical stability score (lower is more stable, scale 0-10)
            stability_score = 0
            if p.sofa_score:
                stability_score += min(p.sofa_score * 1.5, 6)
            if p.mechanical_ventilation:
                stability_score += 4
            if p.vasopressor_support:
                stability_score += 3
            if p.vitals.spo2 and p.vitals.spo2 < 94:
                stability_score += 1
            if p.vitals.heart_rate and (p.vitals.heart_rate > 105 or p.vitals.heart_rate < 55):
                stability_score += 1

            pt_info = {
                "patient_id": p.patient_id,
                "name": p.name,
                "age": p.age,
                "current_unit": p.current_unit.value,
                "assigned_bed": p.assigned_bed_id,
                "los_hours": round(p.length_of_stay_hours, 1),
                "sofa_score": p.sofa_score,
                "vent": p.mechanical_ventilation,
                "pressors": p.vasopressor_support,
                "stability_score": round(stability_score, 1),
                "recommended_destination": "STEP_DOWN" if p.telemetry_required else "MED_SURG",
                "confidence": p.confidence_score
            }

            if is_ready:
                p.is_icu_stepdown_ready = True
                stepdown_candidates.append(pt_info)
            else:
                high_acuity_patients.append(pt_info)

        # Sort stepdown candidates by stability score ascending (most stable first)
        stepdown_candidates.sort(key=lambda x: x["stability_score"])

        data = {
            "total_icu_census": len(icu_patients),
            "stepdown_ready_count": len(stepdown_candidates),
            "high_acuity_count": len(high_acuity_patients),
            "incomplete_records_count": len(incomplete_data_patients),
            "stepdown_candidates": stepdown_candidates,
            "incomplete_records": incomplete_data_patients
        }

        return ToolResult(
            success=True,
            data=data,
            message=f"Found {len(stepdown_candidates)} ICU patients clinically eligible for step-down transfer."
        )
