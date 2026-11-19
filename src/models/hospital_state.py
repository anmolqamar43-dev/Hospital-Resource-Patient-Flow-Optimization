"""
Global Hospital State snapshot model representing the live operational status.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional
from datetime import datetime

from .patient import Patient, UnitType
from .bed import Bed, HospitalUnit, BedStatus
from .staff import StaffMember, MANDATED_NURSE_RATIOS
from .resources import EquipmentInventory, CleaningTask


class HICSAlertLevel(str, Enum):
    NORMAL = "NORMAL"                # Operations within normal tolerance
    YELLOW_SURGE = "YELLOW_SURGE"    # Elevated admissions, ICU >85%, ED Boarding >5
    ORANGE_DIVERT = "ORANGE_DIVERT"  # ICU >95%, Ward full, staffing strain, divert warning
    RED_CRISIS = "RED_CRISIS"        # Critical care saturation, disaster triage protocol


@dataclass
class HospitalOperationalMetrics:
    total_beds: int = 0
    total_occupied_beds: int = 0
    overall_occupancy_rate: float = 0.0
    
    icu_total_beds: int = 0
    icu_occupied_beds: int = 0
    icu_occupancy_rate: float = 0.0
    icu_stepdown_ready_count: int = 0
    
    ed_total_patients: int = 0
    ed_boarding_count: int = 0
    ed_avg_boarding_hours: float = 0.0
    
    discharge_ready_count: int = 0
    discharge_with_barriers_count: int = 0
    
    total_nurses_on_duty: int = 0
    units_violating_nurse_ratio: List[str] = field(default_factory=list)
    average_nurse_fatigue: float = 0.0
    
    ventilator_utilization_rate: float = 0.0
    data_completeness_rate: float = 1.0


@dataclass
class HospitalState:
    timestamp: datetime = field(default_factory=datetime.now)
    hics_level: HICSAlertLevel = HICSAlertLevel.NORMAL
    units: Dict[str, HospitalUnit] = field(default_factory=dict)
    patients: Dict[str, Patient] = field(default_factory=dict)
    staff: Dict[str, StaffMember] = field(default_factory=dict)
    equipment: EquipmentInventory = field(default_factory=EquipmentInventory)
    cleaning_queue: List[CleaningTask] = field(default_factory=list)
    active_bottlenecks: List[Dict[str, Any]] = field(default_factory=list)
    active_recommendations: List[Dict[str, Any]] = field(default_factory=list)

    def calculate_metrics(self) -> HospitalOperationalMetrics:
        metrics = HospitalOperationalMetrics()
        
        # Bed counts
        total_beds = 0
        occupied_beds = 0
        icu_total = 0
        icu_occupied = 0
        
        for u in self.units.values():
            total_beds += u.total_physical_beds
            occupied_beds += u.occupied_count
            if u.unit_type in [UnitType.MICU, UnitType.SICU]:
                icu_total += u.total_physical_beds
                icu_occupied += u.occupied_count
                
        metrics.total_beds = total_beds
        metrics.total_occupied_beds = occupied_beds
        metrics.overall_occupancy_rate = (occupied_beds / total_beds) if total_beds > 0 else 0.0
        
        metrics.icu_total_beds = icu_total
        metrics.icu_occupied_beds = icu_occupied
        metrics.icu_occupancy_rate = (icu_occupied / icu_total) if icu_total > 0 else 0.0
        
        # Patient-level metrics
        ed_pts = [p for p in self.patients.values() if p.current_unit == UnitType.ED]
        metrics.ed_total_patients = len(ed_pts)
        
        ed_boarders = [p for p in ed_pts if p.is_ed_boarder]
        metrics.ed_boarding_count = len(ed_boarders)
        if ed_boarders:
            metrics.ed_avg_boarding_hours = sum(p.ed_boarding_hours for p in ed_boarders) / len(ed_boarders)
            
        metrics.icu_stepdown_ready_count = sum(
            1 for p in self.patients.values()
            if p.current_unit in [UnitType.MICU, UnitType.SICU] and p.evaluate_stepdown_readiness()
        )
        
        disch_candidates = [p for p in self.patients.values() if p.evaluate_discharge_readiness()]
        metrics.discharge_ready_count = len(disch_candidates)
        metrics.discharge_with_barriers_count = sum(
            1 for p in disch_candidates if p.discharge_barrier.value != "NONE"
        )
        
        # Staff ratios
        nurses = [s for s in self.staff.values() if "NURSE" in s.role.value and s.is_available]
        metrics.total_nurses_on_duty = len(nurses)
        if nurses:
            metrics.average_nurse_fatigue = sum(s.fatigue_level for s in nurses) / len(nurses)
            
        violating_units = []
        for u in self.units.values():
            if u.unit_type == UnitType.DISCHARGED:
                continue
            unit_nurses = [s for s in nurses if s.assigned_unit == u.unit_type]
            unit_pts = [p for p in self.patients.values() if p.current_unit == u.unit_type]
            if len(unit_nurses) == 0 and len(unit_pts) > 0:
                violating_units.append(f"{u.name} (0 nurses for {len(unit_pts)} patients)")
            elif len(unit_nurses) > 0:
                ratio = len(unit_pts) / len(unit_nurses)
                allowed = MANDATED_NURSE_RATIOS.get(u.unit_type, 4.0)
                if ratio > allowed:
                    violating_units.append(f"{u.name} (1:{ratio:.1f} vs mandated 1:{allowed:.0f})")
        metrics.units_violating_nurse_ratio = violating_units
        
        # Ventilator utilization
        if self.equipment.ventilators_total > 0:
            metrics.ventilator_utilization_rate = self.equipment.ventilators_in_use / self.equipment.ventilators_total
            
        # Data completeness
        if self.patients:
            complete = sum(1 for p in self.patients.values() if p.is_data_complete)
            metrics.data_completeness_rate = complete / len(self.patients)
            
        return metrics

    def to_summary_dict(self) -> Dict[str, Any]:
        metrics = self.calculate_metrics()
        return {
            "timestamp": self.timestamp.isoformat(),
            "hics_level": self.hics_level.value,
            "metrics": {
                "overall_occupancy_pct": round(metrics.overall_occupancy_rate * 100, 1),
                "total_occupied_beds": metrics.total_occupied_beds,
                "total_beds": metrics.total_beds,
                "icu_occupancy_pct": round(metrics.icu_occupancy_rate * 100, 1),
                "icu_occupied_beds": metrics.icu_occupied_beds,
                "icu_total_beds": metrics.icu_total_beds,
                "icu_stepdown_ready_count": metrics.icu_stepdown_ready_count,
                "ed_total_patients": metrics.ed_total_patients,
                "ed_boarding_count": metrics.ed_boarding_count,
                "ed_avg_boarding_hours": round(metrics.ed_avg_boarding_hours, 1),
                "discharge_ready_count": metrics.discharge_ready_count,
                "discharge_with_barriers_count": metrics.discharge_with_barriers_count,
                "total_nurses_on_duty": metrics.total_nurses_on_duty,
                "average_nurse_fatigue_pct": round(metrics.average_nurse_fatigue * 100, 1),
                "units_violating_nurse_ratio": metrics.units_violating_nurse_ratio,
                "ventilator_utilization_pct": round(metrics.ventilator_utilization_rate * 100, 1),
                "data_completeness_pct": round(metrics.data_completeness_rate * 100, 1)
            },
            "equipment": self.equipment.to_dict(),
            "cleaning_queue_length": len(self.cleaning_queue),
            "units": {uid: u.to_dict() for uid, u in self.units.items()}
        }
