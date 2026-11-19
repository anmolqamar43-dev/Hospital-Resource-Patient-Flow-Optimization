"""
Operational Bottleneck Detection and Root-Cause Diagnostics Tool.
"""

from typing import Dict, Any, List
from ..framework.tool_registry import BaseTool, ToolResult
from ..models.hospital_state import HospitalState
from ..models.patient import UnitType, DischargeBarrier
from ..models.bed import BedStatus


class BottleneckDetectorTool(BaseTool):
    name = "bottleneck_detector"
    description = "Detects operational flow bottlenecks across ED, ICU, Wards, Housekeeping, and Staffing."
    required_parameters = []

    def execute(self, state: HospitalState, **kwargs) -> ToolResult:
        bottlenecks = []

        # 1. ED Boarding Bottleneck
        ed_boarders = [
            p for p in state.patients.values()
            if p.current_unit == UnitType.ED and p.is_ed_boarder
        ]
        if len(ed_boarders) >= 4:
            avg_wait = sum(p.ed_boarding_hours for p in ed_boarders) / len(ed_boarders) if ed_boarders else 0
            severity = "CRITICAL" if len(ed_boarders) >= 8 or avg_wait > 6 else "HIGH"
            bottlenecks.append({
                "bottleneck_id": "BN_ED_BOARDING",
                "category": "EMERGENCY_FLOW",
                "location": "Emergency Department",
                "severity": severity,
                "impact": f"{len(ed_boarders)} admitted patients boarding in ED (average wait: {avg_wait:.1f} hrs). Consuming ED treatment bays and delaying incoming ambulance offloads.",
                "root_cause": "Inpatient bed unavailability in Med-Surg and Telemetry units; delayed morning discharges.",
                "affected_patient_ids": [p.patient_id for p in ed_boarders]
            })

        # 2. ICU Exit Block Bottleneck
        icu_stepdown_ready = [
            p for p in state.patients.values()
            if p.current_unit in [UnitType.MICU, UnitType.SICU] and p.evaluate_stepdown_readiness()
        ]
        sdu_unit = state.units.get("unit_sdu")
        sdu_available = sdu_unit.available_count if sdu_unit else 0
        
        if len(icu_stepdown_ready) > sdu_available and len(icu_stepdown_ready) > 0:
            severity = "CRITICAL" if len(icu_stepdown_ready) >= 3 and sdu_available == 0 else "HIGH"
            bottlenecks.append({
                "bottleneck_id": "BN_ICU_EXIT_BLOCK",
                "category": "CRITICAL_CARE",
                "location": "Medical & Surgical ICUs",
                "severity": severity,
                "impact": f"{len(icu_stepdown_ready)} stable ICU patients ready to transfer down, but only {sdu_available} Step-Down beds available. Artificially inflating ICU occupancy.",
                "root_cause": "Downstream Step-Down and Med-Surg beds at capacity; delayed ward discharges preventing step-down transfers.",
                "affected_patient_ids": [p.patient_id for p in icu_stepdown_ready]
            })

        # 3. Discharge Turnaround Delays
        discharge_barriers_count = sum(
            1 for p in state.patients.values()
            if p.evaluate_discharge_readiness() and p.discharge_barrier != DischargeBarrier.NONE
        )
        if discharge_barriers_count >= 3:
            bottlenecks.append({
                "bottleneck_id": "BN_DISCHARGE_FRICTION",
                "category": "DISCHARGE_PROCESS",
                "location": "Inpatient Wards",
                "severity": "MODERATE" if discharge_barriers_count < 6 else "HIGH",
                "impact": f"{discharge_barriers_count} medically stable patients delayed by non-clinical discharge barriers (transport, meds, SNF placement).",
                "root_cause": "Pharmacy medication reconciliation lag, medical transport dispatch queues, or post-acute SNF placement delays."
            })

        # 4. Bed Turnover / Housekeeping Lag
        dirty_beds = [
            b for u in state.units.values()
            for b in u.beds.values()
            if b.status == BedStatus.CLEANING_IN_PROGRESS or b.cleaning_minutes_remaining > 0
        ]
        if len(dirty_beds) >= 5 or len(state.cleaning_queue) >= 5:
            bottlenecks.append({
                "bottleneck_id": "BN_HOUSEKEEPING_LAG",
                "category": "ENVIRONMENTAL_SERVICES",
                "location": "Central Housekeeping Queue",
                "severity": "MODERATE",
                "impact": f"{len(dirty_beds)} beds pending sanitation turnaround while patients wait in ED and PACU.",
                "root_cause": "Housekeeping staff surge demand during peak morning discharge window."
            })

        # 5. Staffing Ratio Violations
        metrics = state.calculate_metrics()
        if metrics.units_violating_nurse_ratio:
            bottlenecks.append({
                "bottleneck_id": "BN_STAFFING_BREACH",
                "category": "WORKFORCE_CONSTRAINTS",
                "location": "Multiple Units",
                "severity": "HIGH",
                "impact": f"Nurse-to-patient ratio safety mandates violated in: {', '.join(metrics.units_violating_nurse_ratio)}.",
                "root_cause": "Unplanned patient census spikes and unallocated float pool staffing."
            })

        # 6. Critical Equipment Reserve Squeeze
        if state.equipment.ventilators_available <= 3 and state.equipment.ventilators_total > 0:
            bottlenecks.append({
                "bottleneck_id": "BN_VENTILATOR_SHORTAGE",
                "category": "EQUIPMENT_RESERVE",
                "location": "Central Respiratory Therapy",
                "severity": "CRITICAL" if state.equipment.ventilators_available <= 1 else "HIGH",
                "impact": f"Only {state.equipment.ventilators_available} ventilator(s) remain unassigned. Hospital vulnerable to immediate respiratory arrest or multi-trauma arrivals.",
                "root_cause": "High volume of mechanically ventilated ICU patients; pending weaning evaluations."
            })

        data = {
            "total_bottlenecks_detected": len(bottlenecks),
            "critical_count": sum(1 for b in bottlenecks if b["severity"] == "CRITICAL"),
            "high_count": sum(1 for b in bottlenecks if b["severity"] == "HIGH"),
            "bottlenecks": bottlenecks
        }

        return ToolResult(
            success=True,
            data=data,
            message=f"Bottleneck detection complete: {len(bottlenecks)} active operational bottlenecks identified."
        )
