"""
Shared Blackboard for Situational Awareness and Multi-Agent Collaboration.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import threading
from ..models.hospital_state import HospitalState, HICSAlertLevel


class Blackboard:
    """
    Central blackboard shared among all agents in the hospital ecosystem.
    Maintains situational ground truth, active alerts, bottlenecks, proposals, and logs.
    """

    def __init__(self, initial_state: Optional[HospitalState] = None):
        self._lock = threading.RLock()
        self.state: HospitalState = initial_state or HospitalState()
        self.alerts: List[Dict[str, Any]] = []
        self.bottlenecks: List[Dict[str, Any]] = []
        self.proposals: Dict[str, Dict[str, Any]] = {}
        self.executed_actions: List[Dict[str, Any]] = []
        self.uncertainty_log: List[Dict[str, Any]] = []
        self.cycle_count: int = 0

    def update_state(self, state: HospitalState):
        with self._lock:
            self.state = state

    def post_alert(self, alert_id: str, title: str, severity: str, unit: str, details: str, source_agent: str):
        with self._lock:
            # Check if alert already exists to prevent duplicate spam
            for a in self.alerts:
                if a["alert_id"] == alert_id and a["status"] == "ACTIVE":
                    a["details"] = details
                    a["updated_at"] = datetime.now().strftime("%H:%M:%S")
                    return
            self.alerts.append({
                "alert_id": alert_id,
                "title": title,
                "severity": severity,
                "unit": unit,
                "details": details,
                "source_agent": source_agent,
                "status": "ACTIVE",
                "created_at": datetime.now().strftime("%H:%M:%S"),
                "updated_at": datetime.now().strftime("%H:%M:%S")
            })

    def clear_resolved_alerts(self, active_alert_ids: List[str]):
        with self._lock:
            for a in self.alerts:
                if a["alert_id"] not in active_alert_ids:
                    a["status"] = "RESOLVED"

    def record_bottleneck(self, bottleneck_id: str, category: str, location: str, severity: str, impact: str, root_cause: str):
        with self._lock:
            for b in self.bottlenecks:
                if b["bottleneck_id"] == bottleneck_id:
                    b["severity"] = severity
                    b["impact"] = impact
                    return
            self.bottlenecks.append({
                "bottleneck_id": bottleneck_id,
                "category": category,
                "location": location,
                "severity": severity,
                "impact": impact,
                "root_cause": root_cause,
                "detected_at": datetime.now().strftime("%H:%M:%S")
            })

    def post_proposal(self, proposal_id: str, agent_id: str, title: str, category: str, actions: List[Dict[str, Any]], rationale: str, projected_benefit: str):
        with self._lock:
            self.proposals[proposal_id] = {
                "proposal_id": proposal_id,
                "proposer_agent": agent_id,
                "title": title,
                "category": category,
                "actions": actions,
                "rationale": rationale,
                "projected_benefit": projected_benefit,
                "status": "PENDING_REVIEW",  # PENDING_REVIEW, APPROVED, REJECTED, EXECUTED
                "votes": {},                 # agent_id -> {approved: bool, reason: str}
                "created_at": datetime.now().strftime("%H:%M:%S")
            }

    def cast_vote(self, proposal_id: str, voter_agent_id: str, approved: bool, reason: str):
        with self._lock:
            if proposal_id in self.proposals:
                self.proposals[proposal_id]["votes"][voter_agent_id] = {
                    "approved": approved,
                    "reason": reason,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }

    def commit_action(self, action_id: str, executor_agent: str, summary: str, impact_details: Dict[str, Any]):
        with self._lock:
            self.executed_actions.append({
                "action_id": action_id,
                "executor": executor_agent,
                "summary": summary,
                "impact": impact_details,
                "executed_at": datetime.now().strftime("%H:%M:%S")
            })

    def log_uncertainty(self, item_id: str, item_type: str, missing_aspects: List[str], risk_level: str, mitigation: str):
        with self._lock:
            self.uncertainty_log.append({
                "item_id": item_id,
                "type": item_type,
                "missing_aspects": missing_aspects,
                "risk_level": risk_level,
                "mitigation": mitigation,
                "timestamp": datetime.now().strftime("%H:%M:%S")
            })

    def get_summary(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "cycle": self.cycle_count,
                "hics_level": self.state.hics_level.value,
                "active_alerts_count": sum(1 for a in self.alerts if a["status"] == "ACTIVE"),
                "bottlenecks_count": len(self.bottlenecks),
                "pending_proposals_count": sum(1 for p in self.proposals.values() if p["status"] == "PENDING_REVIEW"),
                "approved_proposals_count": sum(1 for p in self.proposals.values() if p["status"] == "APPROVED"),
                "executed_actions_count": len(self.executed_actions),
                "uncertainty_items_count": len(self.uncertainty_log),
                "alerts": [a for a in self.alerts if a["status"] == "ACTIVE"][-10:],
                "bottlenecks": self.bottlenecks[-10:],
                "recent_proposals": list(self.proposals.values())[-6:],
                "recent_actions": self.executed_actions[-6:]
            }
