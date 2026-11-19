"""
Hospital State Generator for MetroHealth Academic Medical Center.
Generates comprehensive, clinically realistic data for 450 beds across 8 units.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from ..models.patient import Patient, AcuityLevel, UnitType, DischargeBarrier, Vitals
from ..models.bed import Bed, HospitalUnit, BedStatus
from ..models.staff import StaffMember, StaffRole, ShiftType
from ..models.resources import EquipmentInventory, CleaningTask
from ..models.hospital_state import HospitalState, HICSAlertLevel


DIAGNOSES = {
    UnitType.ED: [
        ("Chest Pain - Rule out ACS", AcuityLevel.ESI_2_EMERGENT),
        ("Acute Dyspnea / COPD Exacerbation", AcuityLevel.ESI_2_EMERGENT),
        ("Abdominal Pain - Rule out Appendicitis", AcuityLevel.ESI_3_URGENT),
        ("Severe Sepsis secondary to UTI", AcuityLevel.ESI_2_EMERGENT),
        ("Fractured Femur s/p Fall", AcuityLevel.ESI_3_URGENT),
        ("Altered Mental Status in Elderly", AcuityLevel.ESI_2_EMERGENT),
        ("Mild Asthma Exacerbation", AcuityLevel.ESI_4_LESS_URGENT)
    ],
    UnitType.MICU: [
        ("Septic Shock on Norepinephrine", AcuityLevel.ESI_1_RESUSCITATION),
        ("Acute Respiratory Distress Syndrome (ARDS) on Vent", AcuityLevel.ESI_1_RESUSCITATION),
        ("Acute Hypoxemic Respiratory Failure", AcuityLevel.ESI_2_EMERGENT),
        ("Severe DKA with Acidosis", AcuityLevel.ESI_2_EMERGENT),
        ("Post-Cardiac Arrest Hypothermia Protocol", AcuityLevel.ESI_1_RESUSCITATION)
    ],
    UnitType.SICU: [
        ("Post-Op Abdominal Aortic Aneurysm Repair", AcuityLevel.ESI_1_RESUSCITATION),
        ("Multisystem Polytrauma s/p Motor Vehicle Crash", AcuityLevel.ESI_1_RESUSCITATION),
        ("Post-Op Whipple Procedure", AcuityLevel.ESI_2_EMERGENT),
        ("Intracranial Hemorrhage with ICP Monitor", AcuityLevel.ESI_1_RESUSCITATION)
    ],
    UnitType.STEP_DOWN: [
        ("Weaned ARDS on High-Flow Nasal Cannula", AcuityLevel.ESI_3_URGENT),
        ("Resolving DKA on Subcutaneous Insulin", AcuityLevel.ESI_3_URGENT),
        ("Non-ST Elevation Myocardial Infarction (NSTEMI)", AcuityLevel.ESI_2_EMERGENT),
        ("Post-Op Thoracic Lobectomy Day 2", AcuityLevel.ESI_3_URGENT)
    ],
    UnitType.TELEMETRY: [
        ("Atrial Fibrillation with Rapid Ventricular Response", AcuityLevel.ESI_3_URGENT),
        ("Congestive Heart Failure Exacerbation", AcuityLevel.ESI_3_URGENT),
        ("Syncope Workup with Telemetry Monitoring", AcuityLevel.ESI_3_URGENT),
        ("Hypertensive Emergency Stabilized", AcuityLevel.ESI_3_URGENT)
    ],
    UnitType.MED_SURG: [
        ("Community-Acquired Pneumonia on IV Ceftriaxone", AcuityLevel.ESI_3_URGENT),
        ("Cellulitis lower extremity", AcuityLevel.ESI_4_LESS_URGENT),
        ("Acute Pyelonephritis resolving", AcuityLevel.ESI_3_URGENT),
        ("Acute Pancreatitis mild", AcuityLevel.ESI_3_URGENT),
        ("Dehydration in elderly", AcuityLevel.ESI_4_LESS_URGENT)
    ],
    UnitType.SURGICAL_WARD: [
        ("Post-Laparoscopic Cholecystectomy Day 1", AcuityLevel.ESI_3_URGENT),
        ("Post-Total Hip Arthroplasty Day 2", AcuityLevel.ESI_4_LESS_URGENT),
        ("Post-Op Small Bowel Resection Day 3", AcuityLevel.ESI_3_URGENT),
        ("Post-Open Reduction Internal Fixation (ORIF)", AcuityLevel.ESI_3_URGENT)
    ],
    UnitType.PEDIATRIC: [
        ("Pediatric Bronchiolitis (RSV)", AcuityLevel.ESI_3_URGENT),
        ("Pediatric Dehydration secondary to Viral Gastroenteritis", AcuityLevel.ESI_3_URGENT),
        ("Post-Op Pediatric Appendectomy", AcuityLevel.ESI_3_URGENT),
        ("Pediatric Asthma Exacerbation", AcuityLevel.ESI_3_URGENT)
    ]
}

NURSE_FIRST_NAMES = ["Sarah", "Michael", "Elena", "Marcus", "Jessica", "David", "Amina", "Robert", "Chloe", "James", "Maria", "Kenji", "Fatima", "Carlos", "Emma", "Daniel"]
NURSE_LAST_NAMES = ["Chen", "Johnson", "Rodriguez", "O'Connor", "Patel", "Washington", "Kowalski", "Kim", "Taylor", "Santos", "Smith", "Al-Mansoor"]


def create_initial_hospital_state(stress_mode: str = "baseline") -> HospitalState:
    """
    Constructs a calibrated HospitalState.
    stress_mode options:
      - 'baseline': 82% ward occupancy, 80% ICU, normal operations.
      - 'surge': 93% ward occupancy, 95% ICU, 10 ED boarders, 3 staff deficits.
      - 'icu_crisis': 100% ICU occupancy, 4 step-down ready blocked, 0 available ICU beds.
      - 'staffing_crisis': High census with 6 nurse call-outs causing ratio breaches.
    """
    random.seed(42)  # Deterministic seed for reproducible evaluation

    state = HospitalState(
        timestamp=datetime.now(),
        hics_level=HICSAlertLevel.NORMAL
    )

    # 1. Define Units
    unit_configs = [
        ("unit_ed", "Emergency Department", UnitType.ED, 40, 0.25),
        ("unit_micu", "Medical ICU", UnitType.MICU, 24, 0.5),
        ("unit_sicu", "Surgical ICU", UnitType.SICU, 16, 0.5),
        ("unit_step_down", "Step-Down Unit (SDU)", UnitType.STEP_DOWN, 30, 0.33),
        ("unit_telemetry", "Telemetry Cardiac Ward", UnitType.TELEMETRY, 80, 0.25),
        ("unit_med_surg", "General Medical Ward", UnitType.MED_SURG, 120, 0.20),
        ("unit_surgical_ward", "General Surgical Ward", UnitType.SURGICAL_WARD, 100, 0.20),
        ("unit_pediatric", "Pediatric Ward", UnitType.PEDIATRIC, 40, 0.25)
    ]

    for uid, name, utype, total_beds, ratio in unit_configs:
        unit = HospitalUnit(
            unit_id=uid,
            name=name,
            unit_type=utype,
            total_physical_beds=total_beds,
            target_nurse_ratio=ratio
        )
        
        # Populate beds
        prefix = utype.value[:3]
        for b_idx in range(1, total_beds + 1):
            bid = f"{uid}_b{b_idx:03d}"
            bed = Bed(
                bed_id=bid,
                unit_id=uid,
                unit_type=utype,
                bed_number=f"{prefix}-{b_idx:02d}",
                status=BedStatus.AVAILABLE,
                ventilator_capable=(utype in [UnitType.MICU, UnitType.SICU, UnitType.ED]),
                telemetry_equipped=(utype in [UnitType.MICU, UnitType.SICU, UnitType.STEP_DOWN, UnitType.TELEMETRY, UnitType.ED])
            )
            unit.beds[bid] = bed
            
        state.units[uid] = unit

    # 2. Configure Occupancy Targets based on stress_mode
    target_occupancy = {
        "unit_ed": 0.70,
        "unit_micu": 0.83,
        "unit_sicu": 0.75,
        "unit_step_down": 0.80,
        "unit_telemetry": 0.85,
        "unit_med_surg": 0.86,
        "unit_surgical_ward": 0.82,
        "unit_pediatric": 0.65
    }

    if stress_mode in ["surge", "icu_crisis"]:
        target_occupancy["unit_micu"] = 0.96 if stress_mode == "surge" else 1.00
        target_occupancy["unit_sicu"] = 0.94 if stress_mode == "surge" else 1.00
        target_occupancy["unit_step_down"] = 0.97
        target_occupancy["unit_med_surg"] = 0.94
        target_occupancy["unit_telemetry"] = 0.95
        target_occupancy["unit_ed"] = 0.95

    # 3. Populate Patients
    patient_counter = 1
    for uid, unit in state.units.items():
        utype = unit.unit_type
        target_pts = int(unit.total_physical_beds * target_occupancy.get(uid, 0.80))
        diag_list = DIAGNOSES.get(utype, [("Acute Illness", AcuityLevel.ESI_3_URGENT)])
        
        beds_list = list(unit.beds.values())
        random.shuffle(beds_list)

        for i in range(target_pts):
            bed = beds_list[i]
            diag, def_acuity = random.choice(diag_list)
            
            # Critical care indicators
            is_icu = utype in [UnitType.MICU, UnitType.SICU]
            vent = is_icu and (random.random() < 0.65)
            pressor = is_icu and (random.random() < 0.50)
            sofa = round(random.uniform(4.0, 9.0), 1) if is_icu else round(random.uniform(0.0, 2.0), 1)
            
            # Step-down ready cohort in ICU
            is_stepdown_ready = False
            if is_icu and (i >= target_pts - 4):  # last few patients are stabilizing
                vent = False
                pressor = False
                sofa = round(random.uniform(1.0, 2.5), 1)
                is_stepdown_ready = True

            # Discharge candidates in wards
            is_ward = utype in [UnitType.MED_SURG, UnitType.TELEMETRY, UnitType.SURGICAL_WARD]
            is_discharge = False
            barrier = DischargeBarrier.NONE
            if is_ward and (i >= target_pts - 6):
                is_discharge = True
                barriers = [
                    DischargeBarrier.PENDING_MED_RECONCILIATION,
                    DischargeBarrier.PENDING_TRANSPORT,
                    DischargeBarrier.PENDING_PHYSICIAN_SIGNOFF,
                    DischargeBarrier.AWAITING_SNF_BED
                ]
                barrier = random.choice(barriers) if random.random() < 0.70 else DischargeBarrier.NONE

            # Incomplete data cohort (5% of patients)
            is_data_complete = True
            missing_fields = []
            conf = 1.0
            if random.random() < 0.06:
                is_data_complete = False
                missing_fields = ["spo2_telemetry_missing"] if random.random() < 0.5 else ["sofa_score_missing"]
                conf = 0.60
                if "sofa_score_missing" in missing_fields:
                    sofa = None

            # ED boarders
            is_ed = (utype == UnitType.ED)
            is_boarder = False
            boarding_hours = 0.0
            if is_ed:
                if stress_mode in ["surge", "icu_crisis"]:
                    is_boarder = True
                    boarding_hours = round(random.uniform(2.5, 7.5), 1)
                elif stress_mode == "baseline":
                    if i < 2:  # Only 2 boarders in baseline operations
                        is_boarder = True
                        boarding_hours = round(random.uniform(1.0, 2.0), 1)
                elif random.random() < 0.15:
                    is_boarder = True
                    boarding_hours = round(random.uniform(1.5, 3.5), 1)

            pid = f"pt_{patient_counter:04d}"
            pt = Patient(
                patient_id=pid,
                name=f"Patient {patient_counter:04d}",
                age=random.randint(18, 88),
                gender=random.choice(["M", "F"]),
                acuity=def_acuity,
                diagnosis=diag,
                admission_pathway="ED" if is_ed else random.choice(["ED", "ELECTIVE", "DIRECT_TRANSFER"]),
                current_unit=utype,
                assigned_bed_id=bed.bed_id,
                length_of_stay_hours=round(random.uniform(12.0, 140.0), 1),
                expected_los_hours=72.0,
                sofa_score=sofa,
                mechanical_ventilation=vent,
                vasopressor_support=pressor,
                telemetry_required=(utype in [UnitType.TELEMETRY, UnitType.STEP_DOWN, UnitType.MICU, UnitType.SICU]),
                is_ed_boarder=is_boarder,
                ed_boarding_hours=boarding_hours,
                is_icu_stepdown_ready=is_stepdown_ready,
                is_discharge_candidate=is_discharge,
                discharge_barrier=barrier,
                is_data_complete=is_data_complete,
                missing_fields=missing_fields,
                confidence_score=conf,
                vitals=Vitals(
                    heart_rate=random.randint(62, 108),
                    bp_systolic=random.randint(100, 155),
                    bp_diastolic=random.randint(60, 95),
                    spo2=round(random.uniform(92.0, 99.0), 1) if "spo2_telemetry_missing" not in missing_fields else None,
                    resp_rate=random.randint(14, 24)
                )
            )

            state.patients[pid] = pt
            bed.status = BedStatus.OCCUPIED
            bed.current_patient_id = pid
            patient_counter += 1

        # A few beds in cleaning status
        for k in range(target_pts, min(target_pts + 2, len(beds_list))):
            beds_list[k].status = BedStatus.CLEANING_IN_PROGRESS
            beds_list[k].cleaning_minutes_remaining = random.randint(15, 45)
            state.cleaning_queue.append(CleaningTask(
                task_id=f"clean_{beds_list[k].bed_id}",
                bed_id=beds_list[k].bed_id,
                unit_id=uid,
                priority=1 if utype in [UnitType.MICU, UnitType.SICU, UnitType.ED] else 2,
                minutes_remaining=beds_list[k].cleaning_minutes_remaining
            ))

    # 4. Populate Staff & Rosters
    staff_counter = 1
    for uid, unit in state.units.items():
        utype = unit.unit_type
        pts_in_unit = sum(1 for p in state.patients.values() if p.current_unit == utype)
        mandated_ratio = unit.target_nurse_ratio  # e.g. 0.5 (1:2)
        needed_nurses = max(1, int(pts_in_unit * mandated_ratio + 0.99))
        
        # In staffing_crisis mode or surge mode, introduce targeted deficits
        actual_nurses = needed_nurses
        if stress_mode in ["surge", "staffing_crisis"] and utype in [UnitType.MED_SURG, UnitType.TELEMETRY]:
            actual_nurses = max(1, needed_nurses - 2)  # ratio breach!

        for n_idx in range(actual_nurses):
            sid = f"stf_{staff_counter:03d}"
            name = f"{random.choice(NURSE_FIRST_NAMES)} {random.choice(NURSE_LAST_NAMES)}, RN"
            staff = StaffMember(
                staff_id=sid,
                name=name,
                role=StaffRole.CHARGE_NURSE if n_idx == 0 else StaffRole.REGISTERED_NURSE,
                assigned_unit=utype,
                shift=ShiftType.DAY,
                consecutive_hours_worked=round(random.uniform(4.0, 10.5), 1),
                fatigue_level=round(random.uniform(0.2, 0.75), 2),
                is_available=True
            )
            state.staff[sid] = staff
            staff_counter += 1

    # Add Float Pool & On-Call Staff
    for f_idx in range(6):
        sid = f"stf_float_{f_idx+1:02d}"
        state.staff[sid] = StaffMember(
            staff_id=sid,
            name=f"Float RN {f_idx+1}",
            role=StaffRole.REGISTERED_NURSE,
            assigned_unit=UnitType.MED_SURG,
            is_float_pool=True,
            is_available=True,
            can_float_to=[UnitType.MED_SURG, UnitType.TELEMETRY, UnitType.STEP_DOWN, UnitType.ED]
        )

    for oc_idx in range(4):
        sid = f"stf_oncall_{oc_idx+1:02d}"
        state.staff[sid] = StaffMember(
            staff_id=sid,
            name=f"On-Call RN {oc_idx+1}",
            role=StaffRole.REGISTERED_NURSE,
            assigned_unit=UnitType.MED_SURG,
            is_on_call=True,
            is_available=True
        )

    # 5. Equipment Inventory calibration
    total_vents_in_use = sum(1 for p in state.patients.values() if p.mechanical_ventilation)
    state.equipment = EquipmentInventory(
        ventilators_total=40,
        ventilators_in_use=total_vents_in_use,
        ventilators_reserved=4,
        telemetry_monitors_total=100,
        telemetry_monitors_in_use=sum(1 for p in state.patients.values() if p.telemetry_required),
        dialysis_stations_total=12,
        dialysis_stations_in_use=8
    )

    return state
