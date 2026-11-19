"""
Hospital Census and Capacity Analytics Tool.
"""

from typing import Dict, Any, List
from ..framework.tool_registry import BaseTool, ToolResult
from ..models.hospital_state import HospitalState
from ..models.patient import UnitType
from ..models.bed import BedStatus


class CensusTool(BaseTool):
    name = "census_analyzer"
    description = "Analyzes hospital bed census, unit-level occupancy, and reserve margins."
    required_parameters = []

    def execute(self, state: HospitalState, **kwargs) -> ToolResult:
        unit_analysis = {}
        total_beds = 0
        total_occupied = 0
        total_cleaning = 0
        total_available = 0
        total_blocked = 0

        for unit_id, unit in state.units.items():
            if unit.unit_type == UnitType.DISCHARGED:
                continue
                
            occ = unit.occupied_count
            avail = unit.available_count
            clean = unit.cleaning_count
            blocked = unit.blocked_count
            cap = unit.total_physical_beds
            
            total_beds += cap
            total_occupied += occ
            total_cleaning += clean
            total_available += avail
            total_blocked += blocked

            occ_pct = (occ / cap * 100) if cap > 0 else 0.0
            
            unit_analysis[unit_id] = {
                "unit_name": unit.name,
                "unit_type": unit.unit_type.value,
                "capacity": cap,
                "occupied": occ,
                "available": avail,
                "cleaning": clean,
                "blocked": blocked,
                "occupancy_rate_pct": round(occ_pct, 1),
                "status": "CRITICAL" if occ_pct >= 95 else "SURGE" if occ_pct >= 85 else "NORMAL"
            }

        overall_occ_pct = (total_occupied / total_beds * 100) if total_beds > 0 else 0.0

        # Critical care sub-analysis
        icu_beds = sum(u["capacity"] for u in unit_analysis.values() if u["unit_type"] in ["MICU", "SICU"])
        icu_occupied = sum(u["occupied"] for u in unit_analysis.values() if u["unit_type"] in ["MICU", "SICU"])
        icu_occ_pct = (icu_occupied / icu_beds * 100) if icu_beds > 0 else 0.0

        data = {
            "overall": {
                "total_beds": total_beds,
                "total_occupied": total_occupied,
                "total_available": total_available,
                "total_cleaning": total_cleaning,
                "total_blocked": total_blocked,
                "overall_occupancy_pct": round(overall_occ_pct, 1),
                "icu_capacity": icu_beds,
                "icu_occupied": icu_occupied,
                "icu_available": icu_beds - icu_occupied,
                "icu_occupancy_pct": round(icu_occ_pct, 1)
            },
            "units": unit_analysis
        }

        return ToolResult(
            success=True,
            data=data,
            message=f"Hospital census: {total_occupied}/{total_beds} beds occupied ({overall_occ_pct:.1f}%). ICU at {icu_occ_pct:.1f}%."
        )
