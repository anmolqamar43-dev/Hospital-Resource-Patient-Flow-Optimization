"""
Bed and Unit domain models.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
from .patient import UnitType


class BedStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"
    CLEANING_IN_PROGRESS = "CLEANING_IN_PROGRESS"
    RESERVED = "RESERVED"
    MAINTENANCE = "MAINTENANCE"
    BLOCKED_NO_STAFF = "BLOCKED_NO_STAFF"


@dataclass
class Bed:
    bed_id: str
    unit_id: str
    unit_type: UnitType
    bed_number: str
    status: BedStatus = BedStatus.AVAILABLE
    current_patient_id: Optional[str] = None
    reserved_for_patient_id: Optional[str] = None
    
    # Bed Capabilities & Features
    ventilator_capable: bool = False
    telemetry_equipped: bool = False
    negative_pressure_isolation: bool = False
    bariatric: bool = False
    
    # Operational tracking
    cleaning_minutes_remaining: int = 0
    occupied_since_hours: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bed_id": self.bed_id,
            "unit_id": self.unit_id,
            "unit_type": self.unit_type.value,
            "bed_number": self.bed_number,
            "status": self.status.value,
            "current_patient_id": self.current_patient_id,
            "reserved_for_patient_id": self.reserved_for_patient_id,
            "ventilator_capable": self.ventilator_capable,
            "telemetry_equipped": self.telemetry_equipped,
            "negative_pressure_isolation": self.negative_pressure_isolation,
            "bariatric": self.bariatric,
            "cleaning_minutes_remaining": self.cleaning_minutes_remaining,
            "occupied_since_hours": round(self.occupied_since_hours, 1)
        }


@dataclass
class HospitalUnit:
    unit_id: str
    name: str
    unit_type: UnitType
    total_physical_beds: int
    target_nurse_ratio: float  # e.g., 0.5 (1:2), 0.25 (1:4), 0.2 (1:5)
    beds: Dict[str, Bed] = field(default_factory=dict)
    
    @property
    def occupied_count(self) -> int:
        return sum(1 for b in self.beds.values() if b.status == BedStatus.OCCUPIED)

    @property
    def available_count(self) -> int:
        return sum(1 for b in self.beds.values() if b.status == BedStatus.AVAILABLE)

    @property
    def cleaning_count(self) -> int:
        return sum(1 for b in self.beds.values() if b.status == BedStatus.CLEANING_IN_PROGRESS)

    @property
    def reserved_count(self) -> int:
        return sum(1 for b in self.beds.values() if b.status == BedStatus.RESERVED)

    @property
    def blocked_count(self) -> int:
        return sum(1 for b in self.beds.values() if b.status in [BedStatus.BLOCKED_NO_STAFF, BedStatus.MAINTENANCE])

    @property
    def occupancy_rate(self) -> float:
        if self.total_physical_beds == 0:
            return 0.0
        return self.occupied_count / self.total_physical_beds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "name": self.name,
            "unit_type": self.unit_type.value,
            "total_physical_beds": self.total_physical_beds,
            "occupied_count": self.occupied_count,
            "available_count": self.available_count,
            "cleaning_count": self.cleaning_count,
            "reserved_count": self.reserved_count,
            "blocked_count": self.blocked_count,
            "occupancy_rate": round(self.occupancy_rate * 100, 1),
            "target_nurse_ratio": self.target_nurse_ratio
        }
