"""
Unit tests for Autonomous Multi-Agent Behaviors and Messaging.
"""

import unittest
from src.system import HospitalOptimizationSystem
from src.framework.message_bus import MessageIntent


class TestAgentCoordination(unittest.TestCase):

    def setUp(self):
        self.system = HospitalOptimizationSystem(stress_mode="surge")

    def test_multi_agent_cycle_execution(self):
        summary = self.system.step()
        self.assertEqual(summary["cycle"], 1)
        self.assertIn(summary["hics_level"], ["YELLOW_SURGE", "ORANGE_DIVERT", "RED_CRISIS"])
        
        # Verify each agent executed
        completed_agents = [e["agent"] for e in summary["agent_events"] if e["status"] == "COMPLETED"]
        self.assertEqual(len(completed_agents), 6)

    def test_proposals_and_voting(self):
        self.system.step()
        blackboard = self.system.blackboard
        
        # Verify proposals were posted
        self.assertGreater(len(blackboard.proposals), 0)
        
        # Verify chief orchestrator approved or adjudicated
        approved = [p for p in blackboard.proposals.values() if "APPROVED" in p["status"]]
        self.assertGreater(len(approved), 0)

    def test_uncertainty_auditor_flags_missing_data(self):
        self.system.step()
        bb = self.system.blackboard
        
        # Confirm uncertainty log has entries for incomplete data
        self.assertGreater(len(bb.uncertainty_log), 0)


if __name__ == "__main__":
    unittest.main()
