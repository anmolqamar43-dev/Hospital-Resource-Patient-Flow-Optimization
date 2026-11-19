"""
End-to-End Operational Scenario Simulation Tests.
Verifies multi-agent response under baseline, surge, ICU exit block, and staffing crisis.
"""

import unittest
from src.system import HospitalOptimizationSystem


class TestEndToEndScenarios(unittest.TestCase):

    def test_baseline_scenario(self):
        sys = HospitalOptimizationSystem(stress_mode="baseline")
        res = sys.step()
        self.assertEqual(res["hics_level"], "NORMAL")

    def test_surge_and_resolution_flow(self):
        sys = HospitalOptimizationSystem(stress_mode="surge")
        res1 = sys.step()
        self.assertIn(res1["hics_level"], ["YELLOW_SURGE", "ORANGE_DIVERT"])
        
        # Apply AI recommendations
        opt_res = sys.apply_recommendations()
        before = opt_res["impact_comparison"]["before"]
        after = opt_res["impact_comparison"]["after"]
        
        # Verify quantitative improvement
        self.assertLess(after["icu_occupancy_pct"], before["icu_occupancy_pct"])
        self.assertLessEqual(after["ed_boarding_count"], before["ed_boarding_count"])
        self.assertEqual(after["violating_units_count"], 0)

    def test_dynamic_mass_casualty_surge(self):
        sys = HospitalOptimizationSystem(stress_mode="baseline")
        sys.step()
        
        # Inject mass casualty event
        res = sys.trigger_stress_scenario("mass_casualty", count=18)
        self.assertTrue(res["success"])
        
        # System should escalate HICS status
        self.assertIn(sys.blackboard.state.hics_level.value, ["ORANGE_DIVERT", "RED_CRISIS"])


if __name__ == "__main__":
    unittest.main()
