"""
Discrete-Event Scenario and What-If Stress Simulator Tool.
Allows simulating operational disruptions and demonstrating resolution impact.
"""

from typing import Dict, Any, List
import copy
from ..framework.tool_registry import BaseTool, ToolResult
from ..models.hospital_state import HospitalState
from ..models.patient import Patient, AcuityLevel, UnitType, DischargeBarrier, Vitals
from ..models.bed import BedStatus
from ..models.staff import StaffRole, ShiftType, StaffMember


class ScenarioSimulatorTool(BaseTool):
    name = "scenario_simulator"
    description = "Simulates hospital stress scenarios (surges, staffing cuts, mass casualty) and tests intervention impacts."
    required_parameters = ["action"]

    def execute(self, state: HospitalState, **kwargs) -> ToolResult:
        action = kwargs.get("action")
        
        if action == "APPLY_RECOMMENDED_FLOW_OPTIMIZATIONS":
            return self._apply_flow_optimizations(state)
        elif action == "SIMULATE_ED_SURGE":
            count = kwargs.get("count", 15)
            return self._simulate_ed_surge(state, count)
        elif action == "SIMULATE_STAFFING_CALL_OUT":
            count = kwargs.get("count", 4)
            return self._simulate_staffing_callout(state, count)
        elif action == "SIMULATE_MASS_CASUALTY":
            count = kwargs.get("count", 18)
            return self._simulate_mass_casualty(state, count)
        else:
            return ToolResult(success=False, data=None, error=f"Unknown simulation action: {action}")

    def _apply_flow_optimizations(self, state: HospitalState) -> ToolResult:
        """
        Executes the full flow chain reaction:
        1. Resolve discharge barriers & discharge ready patients
        2. Clean and free up beds
        3. Step down ICU candidates to Step-Down / Telemetry
        4. Place ED boarders into vacated Med-Surg / Telemetry beds
        5. Dispatch float pool nurses to fix ratio violations
        """
        changes = []
        beds_freed = 0
        icu_decompressed = 0
        ed_boarders_placed = 0
        nurses_reassigned = 0

        # Step 1: Discharge ready patients in wards
        discharge_candidates = [
            p for p in list(state.patients.values())
            if p.evaluate_discharge_readiness() and p.current_unit not in [UnitType.ED, UnitType.MICU, UnitType.SICU]
        ]
        
        for p in discharge_candidates:
            old_unit_id = f"unit_{p.current_unit.value.lower()}"
            unit = state.units.get(old_unit_id)
            if unit and p.assigned_bed_id and p.assigned_bed_id in unit.beds:
                bed = unit.beds[p.assigned_bed_id]
                bed.status = BedStatus.AVAILABLE  # expedited cleaning completed
                bed.current_patient_id = None
                p.current_unit = UnitType.DISCHARGED
                p.assigned_bed_id = None
                p.discharge_barrier = DischargeBarrier.NONE
                beds_freed += 1
                changes.append(f"Discharged patient {p.name} from {unit.name}, freeing bed {bed.bed_number}.")

        # Step 2: Step down ICU patients
        icu_ready = [
            p for p in list(state.patients.values())
            if p.current_unit in [UnitType.MICU, UnitType.SICU] and p.evaluate_stepdown_readiness()
        ]
        sdu_unit = state.units.get("unit_step_down")
        tele_unit = state.units.get("unit_telemetry")
        
        target_units = [sdu_unit, tele_unit]
        for p in icu_ready:
            # find available bed in step-down or telemetry
            placed = False
            for target_u in target_units:
                if not target_u:
                    continue
                avail_beds = [b for b in target_u.beds.values() if b.status == BedStatus.AVAILABLE]
                if avail_beds:
                    target_bed = avail_beds[0]
                    # Free up ICU bed
                    old_unit = state.units.get(f"unit_{p.current_unit.value.lower()}")
                    if old_unit and p.assigned_bed_id in old_unit.beds:
                        old_bed = old_unit.beds[p.assigned_bed_id]
                        old_bed.status = BedStatus.AVAILABLE
                        old_bed.current_patient_id = None
                        
                    # Place in step-down
                    target_bed.status = BedStatus.OCCUPIED
                    target_bed.current_patient_id = p.patient_id
                    p.current_unit = target_u.unit_type
                    p.assigned_bed_id = target_bed.bed_id
                    p.is_icu_stepdown_ready = False
                    icu_decompressed += 1
                    placed = True
                    changes.append(f"Transferred stabilized patient {p.name} from ICU to {target_u.name} (Bed {target_bed.bed_number}).")
                    break

        # Step 3: Place ED Boarders into freed inpatient beds
        ed_boarders = [
            p for p in list(state.patients.values())
            if p.current_unit == UnitType.ED and p.is_ed_boarder
        ]
        
        # Candidate inpatient units
        inpatient_units = [
            state.units.get("unit_med_surg"),
            state.units.get("unit_telemetry"),
            state.units.get("unit_surgical_ward")
        ]

        for p in ed_boarders:
            for u in inpatient_units:
                if not u:
                    continue
                avail_beds = [b for b in u.beds.values() if b.status == BedStatus.AVAILABLE]
                if avail_beds:
                    target_bed = avail_beds[0]
                    # Free ED bed
                    ed_unit = state.units.get("unit_ed")
                    if ed_unit and p.assigned_bed_id in ed_unit.beds:
                        ed_bed = ed_unit.beds[p.assigned_bed_id]
                        ed_bed.status = BedStatus.AVAILABLE
                        ed_bed.current_patient_id = None

                    target_bed.status = BedStatus.OCCUPIED
                    target_bed.current_patient_id = p.patient_id
                    p.current_unit = u.unit_type
                    p.assigned_bed_id = target_bed.bed_id
                    p.is_ed_boarder = False
                    p.ed_boarding_hours = 0.0
                    ed_boarders_placed += 1
                    changes.append(f"Admitted ED boarder {p.name} into {u.name} (Bed {target_bed.bed_number}).")
                    break

        # Step 4: Dispatch available float pool nurses
        float_nurses = [
            s for s in state.staff.values()
            if s.is_float_pool and s.is_available and len(s.assigned_patient_ids) == 0
        ]
        # Check units in deficit
        for u in state.units.values():
            if u.unit_type == UnitType.DISCHARGED:
                continue
            unit_pts = [p for p in state.patients.values() if p.current_unit == u.unit_type]
            unit_nurses = [s for s in state.staff.values() if "NURSE" in s.role.value and s.assigned_unit == u.unit_type and s.is_available]
            needed = int((len(unit_pts) + 3.99) // 4)
            deficit = needed - len(unit_nurses)
            while deficit > 0 and float_nurses:
                n = float_nurses.pop(0)
                n.assigned_unit = u.unit_type
                nurses_reassigned += 1
                changes.append(f"Reassigned Float Nurse {n.name} to {u.name} to resolve ratio breach.")
                deficit -= 1

        data = {
            "beds_freed": beds_freed,
            "icu_decompressed": icu_decompressed,
            "ed_boarders_placed": ed_boarders_placed,
            "nurses_reassigned": nurses_reassigned,
            "change_log": changes
        }

        return ToolResult(
            success=True,
            data=data,
            message=f"Optimizations applied successfully: {beds_freed} beds freed, {icu_decompressed} ICU transfers, {ed_boarders_placed} ED boarders placed, {nurses_reassigned} nurses deployed."
        )

    def _simulate_ed_surge(self, state: HospitalState, count: int) -> ToolResult:
        ed_unit = state.units.get("unit_ed")
        if not ed_unit:
            return ToolResult(success=False, data=None, error="ED unit not found")

        created = []
        import uuid
        for i in range(count):
            pid = f"pt_surge_{uuid.uuid4().hex[:6]}"
            acuity = AcuityLevel.ESI_2_EMERGENT if i % 3 == 0 else AcuityLevel.ESI_3_URGENT
            pt = Patient(
                patient_id=pid,
                name=f"Surge Arrival #{i+1}",
                age=35 + (i * 3) % 45,
                gender="M" if i % 2 == 0 else "F",
                acuity=acuity,
                diagnosis="Acute Exacerbation / Trauma / Respiratory Distress",
                admission_pathway="ED",
                current_unit=UnitType.ED,
                is_ed_boarder=True,
                ed_boarding_hours=2.5 + (i * 0.4)
            )
            state.patients[pid] = pt
            created.append(pid)

        return ToolResult(
            success=True,
            data={"new_patients_count": len(created), "patient_ids": created},
            message=f"Simulated ED influx surge: {len(created)} acute patients arrived in Emergency Department."
        )

    def _simulate_staffing_callout(self, state: HospitalState, count: int) -> ToolResult:
        available_nurses = [
            s for s in state.staff.values()
            if "NURSE" in s.role.value and s.is_available and not s.is_on_call
        ]
        
        called_out = []
        for i in range(min(count, len(available_nurses))):
            nurse = available_nurses[i]
            nurse.is_available = False
            nurse.assigned_patient_ids.clear()
            called_out.append(f"{nurse.name} ({nurse.assigned_unit.value})")

        return ToolResult(
            success=True,
            data={"called_out_count": len(called_out), "nurses": called_out},
            message=f"Simulated unplanned staffing shortage: {len(called_out)} nurses called out sick."
        )

    def _simulate_mass_casualty(self, state: HospitalState, count: int) -> ToolResult:
        import uuid
        trauma_pts = []
        for i in range(count):
            pid = f"pt_mci_{uuid.uuid4().hex[:6]}"
            is_critical = (i % 2 == 0)
            pt = Patient(
                patient_id=pid,
                name=f"MCI Trauma Victim #{i+1}",
                age=20 + (i * 4) % 60,
                gender="M" if i % 2 == 0 else "F",
                acuity=AcuityLevel.ESI_1_RESUSCITATION if is_critical else AcuityLevel.ESI_2_EMERGENT,
                diagnosis="Multisystem Blunt Trauma / Blast Injury",
                admission_pathway="AMBULANCE",
                current_unit=UnitType.ED,
                sofa_score=6.0 if is_critical else 2.0,
                mechanical_ventilation=is_critical,
                vasopressor_support=is_critical,
                is_ed_boarder=True,
                ed_boarding_hours=0.5
            )
            state.patients[pid] = pt
            trauma_pts.append(pid)
            
            if is_critical and state.equipment.ventilators_available > 0:
                state.equipment.ventilators_in_use += 1

        return ToolResult(
            success=True,
            data={"mass_casualty_patients": len(trauma_pts)},
            message=f"Mass Casualty Incident simulated: {len(trauma_pts)} trauma victims admitted under Code Orange protocol."
        )
