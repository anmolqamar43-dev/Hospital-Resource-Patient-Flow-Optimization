"""
Unit tests for Hospital Operations Copilot Chatbot.
"""

import unittest
from src.system import HospitalOptimizationSystem
from src.framework.chatbot import HospitalOperationsChatbot


class TestHospitalOperationsChatbot(unittest.TestCase):

    def setUp(self):
        self.system = HospitalOptimizationSystem(stress_mode="surge")
        self.system.step()
        self.chatbot = HospitalOperationsChatbot(self.system)

    def test_greeting_intent(self):
        res = self.chatbot.handle_message("Hello, who are you and what can you do?")
        self.assertIn("MetroHealth", res["reply"])
        self.assertIn("reply", res)

    def test_status_briefing_query(self):
        res = self.chatbot.handle_message("Give me an operational census briefing")
        self.assertIn("MetroHealth Operational Status Briefing", res["reply"])
        self.assertIn("Overall Census", res["reply"])

    def test_icu_capacity_query(self):
        res = self.chatbot.handle_message("What is our ICU capacity and step-down candidates?")
        self.assertIn("Critical Care (ICU) Capacity Report", res["reply"])
        self.assertIn("Step-Down Ready Candidates", res["reply"])

    def test_action_command_apply_optimizations(self):
        res = self.chatbot.handle_message("Apply flow optimizations now")
        self.assertEqual(res["action_taken"], "APPLY_OPTIMIZATIONS")
        self.assertIn("Flow Optimizations Applied Successfully", res["reply"])


if __name__ == "__main__":
    unittest.main()
