"""
Unit tests for Hospital Domain Data Models.
"""

import unittest
from datetime import datetime
from src.models.patient import Patient, AcuityLevel, UnitType, DischargeBarrier, Vitals
from src.models.bed import Bed, HospitalUnit, BedStatus
from src.models.staff import StaffMember, StaffRole, ShiftType, MANDATED_NURSE_RATIOS
from src.models.hospital_state import HospitalState, HICSAlertLevel


class TestPatientModels(unittest.TestCase):

    def test_stepdown_readiness_stable_patient(self):
        pt = Patient(
            patient_id="p1",
            name="John Doe",
            age=55,
            gender="M",
            acuity=AcuityLevel.ESI_2_EMERGENT,
            diagnosis="Resolving ARDS",
            admission_pathway="ED",
            current_unit=UnitType.MICU,
            sofa_score=2.0,
            mechanical_ventilation=False,
            vasopressor_support=False,
            vitals=Vitals(spo2=96.0, heart_rate=78)
        )
        self.assertTrue(pt.evaluate_stepdown_readiness())

    def test_stepdown_readiness_ventilated_patient_rejected(self):
        pt = Patient(
            patient_id="p2",
            name="Jane Smith",
            age=62,
            gender="F",
            acuity=AcuityLevel.ESI_1_RESUSCITATION,
            diagnosis="Septic Shock on Vent",
            admission_pathway="ED",
            current_unit=UnitType.MICU,
            sofa_score=7.0,
            mechanical_ventilation=True,
            vasopressor_support=True
        )
        self.assertFalse(pt.evaluate_stepdown_readiness())

    def test_incomplete_data_flag(self):
        pt = Patient(
            patient_id="p3",
            name="Unknown",
            age=40,
            gender="M",
            acuity=AcuityLevel.ESI_2_EMERGENT,
            diagnosis="Trauma",
            admission_pathway="AMBULANCE",
            current_unit=UnitType.MICU,
            is_data_complete=False,
            missing_fields=["sofa_score_missing"],
            sofa_score=None
        )
        self.assertFalse(pt.is_data_complete)
        self.assertFalse(pt.evaluate_stepdown_readiness())


class TestBedAndUnitModels(unittest.TestCase):

    def test_unit_occupancy_calculations(self):
        unit = HospitalUnit(
            unit_id="u_med",
            name="Medical Ward",
            unit_type=UnitType.MED_SURG,
            total_physical_beds=10,
            target_nurse_ratio=0.2
        )
        for i in range(10):
            status = BedStatus.OCCUPIED if i < 7 else BedStatus.AVAILABLE
            b = Bed(bed_id=f"b_{i}", unit_id="u_med", unit_type=UnitType.MED_SURG, bed_number=f"M-{i}", status=status)
            unit.beds[b.bed_id] = b

        self.assertEqual(unit.occupied_count, 7)
        self.assertEqual(unit.available_count, 3)
        self.assertAlmostEqual(unit.occupancy_rate, 0.70)


class TestStaffModels(unittest.TestCase):

    def test_mandated_ratios(self):
        self.assertEqual(MANDATED_NURSE_RATIOS[UnitType.MICU], 2.0)
        self.assertEqual(MANDATED_NURSE_RATIOS[UnitType.STEP_DOWN], 3.0)
        self.assertEqual(MANDATED_NURSE_RATIOS[UnitType.MED_SURG], 5.0)


if __name__ == "__main__":
    unittest.main()
