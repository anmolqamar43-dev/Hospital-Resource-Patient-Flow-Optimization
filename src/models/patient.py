"""
Patient domain model with clinical acuity scoring and incomplete data tracking.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid


class AcuityLevel(str, Enum):
    ESI_1_RESUSCITATION = "ESI_1"  # Immediate life-saving intervention
    ESI_2_EMERGENT = "ESI_2"       # High risk, confused, severe pain
    ESI_3_URGENT = "ESI_3"         # Multiple resources needed, stable vitals
    ESI_4_LESS_URGENT = "ESI_4"    # One resource needed
    ESI_5_NON_URGENT = "ESI_5"     # No resources needed


class UnitType(str, Enum):
    ED = "ED"
    MICU = "MICU"
    SICU = "SICU"
    STEP_DOWN = "STEP_DOWN"
    MED_SURG = "MED_SURG"
    TELEMETRY = "TELEMETRY"
    PEDIATRIC = "PEDIATRIC"
    SURGICAL_WARD = "SURGICAL_WARD"
    DISCHARGED = "DISCHARGED"


class DischargeBarrier(str, Enum):
    NONE = "NONE"
    PENDING_TRANSPORT = "PENDING_TRANSPORT"
    PENDING_MED_RECONCILIATION = "PENDING_MED_RECONCILIATION"
    AWAITING_SNF_BED = "AWAITING_SNF_BED"
    PENDING_PHYSICIAN_SIGNOFF = "PENDING_PHYSICIAN_SIGNOFF"
    PENDING_LAB_RESULT = "PENDING_LAB_RESULT"
    SOCIAL_WORK_CLEARANCE = "SOCIAL_WORK_CLEARANCE"


@dataclass
class Vitals:
    heart_rate: Optional[int] = 78
    bp_systolic: Optional[int] = 120
    bp_diastolic: Optional[int] = 80
    spo2: Optional[float] = 98.0
    resp_rate: Optional[int] = 16
    temperature: Optional[float] = 37.0


@dataclass
class Patient:
    patient_id: str
    name: str
    age: int
    gender: str
    acuity: AcuityLevel
    diagnosis: str
    admission_pathway: str  # "ED", "ELECTIVE", "DIRECT_TRANSFER", "AMBULANCE"
    current_unit: UnitType
    assigned_bed_id: Optional[str] = None
    admission_time: datetime = field(default_factory=datetime.now)
    length_of_stay_hours: float = 0.0
    expected_los_hours: float = 72.0
    
    # Critical Care Clinical Metrics
    sofa_score: Optional[float] = 0.0           # Sequential Organ Failure Assessment (0-24)
    mechanical_ventilation: bool = False
    vasopressor_support: bool = False
    telemetry_required: bool = False
    isolation_required: bool = False
    
    # Patient Flow Status
    is_ed_boarder: bool = False                 # Admitted in ED waiting for inpatient bed
    ed_boarding_hours: float = 0.0
    is_icu_stepdown_ready: bool = False         # Clinically stable to move from ICU to SDU/Ward
    is_discharge_candidate: bool = False        # Clinically ready for home/facility discharge
    discharge_barrier: DischargeBarrier = DischargeBarrier.NONE
    discharge_barrier_notes: str = ""
    
    # Missing / Incomplete Information Tracking
    is_data_complete: bool = True
    missing_fields: List[str] = field(default_factory=list)
    confidence_score: float = 1.0               # Confidence in patient clinical state assessment (0.0 - 1.0)
    vitals: Vitals = field(default_factory=Vitals)

    def evaluate_stepdown_readiness(self) -> bool:
        """
        Evidence-based step-down criteria:
        Patient in ICU is ready for step-down if:
        - Not on mechanical ventilation (or successfully extubated)
        - Not on continuous high-dose vasopressor support
        - SOFA score <= 3 (or proxy vitals stable)
        - No active life-threatening dysrhythmia
        """
        if not self.is_data_complete or self.sofa_score is None:
            return False

        if self.current_unit not in [UnitType.MICU, UnitType.SICU]:
            return False
            
        if self.mechanical_ventilation:
            return False
            
        if self.vasopressor_support:
            return False
            
        if self.sofa_score is not None and self.sofa_score > 3.0:
            return False
            
        if self.vitals.spo2 is not None and self.vitals.spo2 < 92.0:
            return False
            
        return True

    def evaluate_discharge_readiness(self) -> bool:
        """
        Check if patient in ward is medically stable for discharge.
        """
        if self.current_unit in [UnitType.ED, UnitType.MICU, UnitType.SICU]:
            return False
        
        # Clinical stability
        if self.sofa_score is not None and self.sofa_score > 1.0:
            return False
            
        if self.mechanical_ventilation or self.vasopressor_support:
            return False
            
        if self.length_of_stay_hours >= self.expected_los_hours * 0.8:
            return True
            
        return self.is_discharge_candidate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "acuity": self.acuity.value,
            "diagnosis": self.diagnosis,
            "admission_pathway": self.admission_pathway,
            "current_unit": self.current_unit.value,
            "assigned_bed_id": self.assigned_bed_id,
            "length_of_stay_hours": round(self.length_of_stay_hours, 1),
            "expected_los_hours": self.expected_los_hours,
            "sofa_score": self.sofa_score,
            "mechanical_ventilation": self.mechanical_ventilation,
            "vasopressor_support": self.vasopressor_support,
            "telemetry_required": self.telemetry_required,
            "isolation_required": self.isolation_required,
            "is_ed_boarder": self.is_ed_boarder,
            "ed_boarding_hours": round(self.ed_boarding_hours, 1),
            "is_icu_stepdown_ready": self.is_icu_stepdown_ready,
            "is_discharge_candidate": self.is_discharge_candidate,
            "discharge_barrier": self.discharge_barrier.value,
            "is_data_complete": self.is_data_complete,
            "missing_fields": self.missing_fields,
            "confidence_score": round(self.confidence_score, 2),
            "vitals": {
                "heart_rate": self.vitals.heart_rate,
                "bp_systolic": self.vitals.bp_systolic,
                "bp_diastolic": self.vitals.bp_diastolic,
                "spo2": self.vitals.spo2,
                "resp_rate": self.vitals.resp_rate,
                "temperature": self.vitals.temperature
            }
        }
