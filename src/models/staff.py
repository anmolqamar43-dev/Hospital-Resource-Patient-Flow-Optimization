"""
Staff and Workforce domain models with regulatory ratios and burnout analytics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from .patient import UnitType


class StaffRole(str, Enum):
    REGISTERED_NURSE = "REGISTERED_NURSE"
    CHARGE_NURSE = "CHARGE_NURSE"
    INTENSIVIST = "INTENSIVIST"
    HOSPITALIST = "HOSPITALIST"
    RESIDENT = "RESIDENT"
    HOUSEKEEPING = "HOUSEKEEPING"


class ShiftType(str, Enum):
    DAY = "DAY"          # 07:00 - 19:00
    NIGHT = "NIGHT"      # 19:00 - 07:00


# Standard regulatory/mandated max patients per nurse
MANDATED_NURSE_RATIOS: Dict[UnitType, float] = {
    UnitType.ED: 4.0,           # 1:4 max in ED
    UnitType.MICU: 2.0,         # 1:2 max in ICU (1:1 if unstable)
    UnitType.SICU: 2.0,         # 1:2 max in SICU
    UnitType.STEP_DOWN: 3.0,    # 1:3 max in Step-Down
    UnitType.TELEMETRY: 4.0,    # 1:4 max in Telemetry
    UnitType.MED_SURG: 5.0,     # 1:5 max in Med-Surg
    UnitType.PEDIATRIC: 4.0,    # 1:4 max in Pediatrics
    UnitType.SURGICAL_WARD: 5.0 # 1:5 max in Surgical Ward
}


@dataclass
class StaffMember:
    staff_id: str
    name: str
    role: StaffRole
    assigned_unit: UnitType
    shift: ShiftType = ShiftType.DAY
    assigned_patient_ids: List[str] = field(default_factory=list)
    
    # Workforce Health & Constraints
    consecutive_hours_worked: float = 0.0
    fatigue_level: float = 0.2           # 0.0 (fresh) to 1.0 (exhausted)
    is_on_call: bool = False
    is_float_pool: bool = False
    is_available: bool = True
    can_float_to: List[UnitType] = field(default_factory=list)

    @property
    def current_patient_load(self) -> int:
        return len(self.assigned_patient_ids)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "staff_id": self.staff_id,
            "name": self.name,
            "role": self.role.value,
            "assigned_unit": self.assigned_unit.value,
            "shift": self.shift.value,
            "assigned_patient_ids": self.assigned_patient_ids,
            "patient_load": self.current_patient_load,
            "consecutive_hours_worked": round(self.consecutive_hours_worked, 1),
            "fatigue_level": round(self.fatigue_level, 2),
            "is_on_call": self.is_on_call,
            "is_float_pool": self.is_float_pool,
            "is_available": self.is_available,
            "can_float_to": [u.value for u in self.can_float_to]
        }
