"""
Staffing Optimization and Nurse-to-Patient Ratio Solver Tool.
"""

from typing import Dict, Any, List
from ..framework.tool_registry import BaseTool, ToolResult
from ..models.hospital_state import HospitalState
from ..models.patient import UnitType
from ..models.staff import StaffRole, MANDATED_NURSE_RATIOS, StaffMember


class StaffingOptimizerTool(BaseTool):
    name = "staffing_optimizer"
    description = "Evaluates nurse staffing compliance and computes optimal float pool reassignments."
    required_parameters = []

    def execute(self, state: HospitalState, **kwargs) -> ToolResult:
        unit_compliance = {}
        deficit_units = []
        surplus_units = []
        
        nurses: List[StaffMember] = [
            s for s in state.staff.values()
            if "NURSE" in s.role.value and s.is_available
        ]

        float_pool_available = [s for s in nurses if s.is_float_pool and len(s.assigned_patient_ids) == 0]
        on_call_available = [s for s in state.staff.values() if s.is_on_call and "NURSE" in s.role.value and s.is_available]

        for unit_id, unit in state.units.items():
            if unit.unit_type == UnitType.DISCHARGED:
                continue

            unit_nurses = [s for s in nurses if s.assigned_unit == unit.unit_type]
            patient_count = sum(1 for p in state.patients.values() if p.current_unit == unit.unit_type)
            mandated_ratio = MANDATED_NURSE_RATIOS.get(unit.unit_type, 4.0)

            # Needed nurses = ceil(patient_count / mandated_ratio)
            needed_nurses = 0
            if patient_count > 0:
                needed_nurses = int((patient_count + mandated_ratio - 0.001) // mandated_ratio)

            current_nurses = len(unit_nurses)
            variance = current_nurses - needed_nurses  # negative means deficit
            current_ratio = (patient_count / current_nurses) if current_nurses > 0 else 99.0

            avg_fatigue = (
                sum(n.fatigue_level for n in unit_nurses) / current_nurses
            ) if current_nurses > 0 else 0.0

            unit_compliance[unit_id] = {
                "unit_name": unit.name,
                "unit_type": unit.unit_type.value,
                "patient_count": patient_count,
                "nurses_on_duty": current_nurses,
                "needed_nurses": needed_nurses,
                "variance": variance,
                "actual_ratio": f"1:{current_ratio:.1f}",
                "mandated_ratio": f"1:{mandated_ratio:.0f}",
                "is_compliant": current_ratio <= mandated_ratio and current_nurses > 0,
                "avg_nurse_fatigue_pct": round(avg_fatigue * 100, 1)
            }

            if variance < 0:
                deficit_units.append({
                    "unit_id": unit_id,
                    "unit_type": unit.unit_type,
                    "deficit": abs(variance),
                    "priority": 1 if unit.unit_type in [UnitType.MICU, UnitType.SICU, UnitType.ED] else 2
                })
            elif variance > 0:
                surplus_units.append({
                    "unit_id": unit_id,
                    "unit_type": unit.unit_type,
                    "surplus": variance
                })

        # Sort deficit units by priority
        deficit_units.sort(key=lambda x: x["priority"])

        # Formulate optimal reassignment actions
        recommended_actions = []
        floats_to_dispatch = list(float_pool_available)
        
        for def_info in deficit_units:
            needed = def_info["deficit"]
            utype = def_info["unit_type"]
            
            # Step A: Assign from float pool
            while needed > 0 and floats_to_dispatch:
                nurse = floats_to_dispatch.pop(0)
                recommended_actions.append({
                    "action_type": "DISPATCH_FLOAT_NURSE",
                    "staff_id": nurse.staff_id,
                    "staff_name": nurse.name,
                    "target_unit": utype.value,
                    "rationale": f"Cover deficit in {utype.value} to meet 1:{MANDATED_NURSE_RATIOS[utype]:.0f} ratio."
                })
                needed -= 1

            # Step B: If still deficit, call in on-call nurses
            while needed > 0 and on_call_available:
                on_call_nurse = on_call_available.pop(0)
                recommended_actions.append({
                    "action_type": "ACTIVATE_ON_CALL_NURSE",
                    "staff_id": on_call_nurse.staff_id,
                    "staff_name": on_call_nurse.name,
                    "target_unit": utype.value,
                    "rationale": f"Call-in required for {utype.value}: float pool exhausted."
                })
                needed -= 1

        total_deficits = sum(d["deficit"] for d in deficit_units)

        data = {
            "unit_compliance": unit_compliance,
            "total_nurse_deficit": total_deficits,
            "float_pool_available_count": len(float_pool_available),
            "on_call_available_count": len(on_call_available),
            "recommended_actions": recommended_actions
        }

        return ToolResult(
            success=True,
            data=data,
            message=f"Staffing analysis complete. {len(deficit_units)} units with nurse deficits. Generated {len(recommended_actions)} mitigation actions."
        )
