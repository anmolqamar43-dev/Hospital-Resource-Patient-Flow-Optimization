"""
Hospital critical equipment and housekeeping resources.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List


@dataclass
class EquipmentInventory:
    ventilators_total: int = 40
    ventilators_in_use: int = 28
    ventilators_reserved: int = 4
    
    telemetry_monitors_total: int = 80
    telemetry_monitors_in_use: int = 65
    
    dialysis_stations_total: int = 12
    dialysis_stations_in_use: int = 8
    
    ecmo_circuits_total: int = 4
    ecmo_circuits_in_use: int = 2

    @property
    def ventilators_available(self) -> int:
        return max(0, self.ventilators_total - self.ventilators_in_use - self.ventilators_reserved)

    @property
    def telemetry_available(self) -> int:
        return max(0, self.telemetry_monitors_total - self.telemetry_monitors_in_use)

    @property
    def dialysis_available(self) -> int:
        return max(0, self.dialysis_stations_total - self.dialysis_stations_in_use)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ventilators": {
                "total": self.ventilators_total,
                "in_use": self.ventilators_in_use,
                "reserved": self.ventilators_reserved,
                "available": self.ventilators_available
            },
            "telemetry_monitors": {
                "total": self.telemetry_monitors_total,
                "in_use": self.telemetry_monitors_in_use,
                "available": self.telemetry_available
            },
            "dialysis_stations": {
                "total": self.dialysis_stations_total,
                "in_use": self.dialysis_stations_in_use,
                "available": self.dialysis_available
            },
            "ecmo_circuits": {
                "total": self.ecmo_circuits_total,
                "in_use": self.ecmo_circuits_in_use
            }
        }


@dataclass
class CleaningTask:
    task_id: str
    bed_id: str
    unit_id: str
    priority: int  # 1 = Highest (ICU/ED demand), 3 = Normal
    minutes_remaining: int = 45
    assigned_staff_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "bed_id": self.bed_id,
            "unit_id": self.unit_id,
            "priority": self.priority,
            "minutes_remaining": self.minutes_remaining,
            "assigned_staff_id": self.assigned_staff_id
        }
