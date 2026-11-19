"""
Unit tests for Clinical & Operational Analytics Tools.
"""

import unittest
from src.simulation.hospital_generator import create_initial_hospital_state
from src.tools.census_tool import CensusTool
from src.tools.icu_triage_tool import ICUTriageTool
from src.tools.staffing_optimizer_tool import StaffingOptimizerTool
from src.tools.bottleneck_detector_tool import BottleneckDetectorTool
from src.tools.discharge_accelerator_tool import DischargeAcceleratorTool
from src.tools.scenario_simulator_tool import ScenarioSimulatorTool


class TestAnalyticalTools(unittest.TestCase):

    def setUp(self):
        self.state = create_initial_hospital_state(stress_mode="surge")

    def test_census_analyzer(self):
        tool = CensusTool()
        result = tool.execute(self.state)
        self.assertTrue(result.success)
        self.assertIn("overall", result.data)
        self.assertGreater(result.data["overall"]["total_beds"], 400)
        self.assertGreater(result.data["overall"]["overall_occupancy_pct"], 80.0)

    def test_icu_stepdown_evaluator(self):
        tool = ICUTriageTool()
        result = tool.execute(self.state)
        self.assertTrue(result.success)
        self.assertIn("stepdown_candidates", result.data)
        self.assertGreaterEqual(result.data["stepdown_ready_count"], 0)

    def test_staffing_optimizer(self):
        tool = StaffingOptimizerTool()
        result = tool.execute(self.state)
        self.assertTrue(result.success)
        self.assertIn("unit_compliance", result.data)
        self.assertIn("recommended_actions", result.data)

    def test_bottleneck_detector(self):
        tool = BottleneckDetectorTool()
        result = tool.execute(self.state)
        self.assertTrue(result.success)
        self.assertIn("bottlenecks", result.data)
        self.assertGreater(result.data["total_bottlenecks_detected"], 0)

    def test_discharge_accelerator(self):
        tool = DischargeAcceleratorTool()
        result = tool.execute(self.state)
        self.assertTrue(result.success)
        self.assertIn("recommended_interventions", result.data)

    def test_scenario_simulator_optimizations(self):
        tool = ScenarioSimulatorTool()
        result = tool.execute(self.state, action="APPLY_RECOMMENDED_FLOW_OPTIMIZATIONS")
        self.assertTrue(result.success)
        self.assertGreater(result.data["beds_freed"], 0)


if __name__ == "__main__":
    unittest.main()
