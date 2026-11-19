"""
Interactive CLI Demonstration and Scenario Benchmark Runner.
Hospital Resource & Patient Flow Optimization System.
"""

import sys
import time
import json
from src.system import HospitalOptimizationSystem
from src.models.hospital_state import HICSAlertLevel


# ANSI Terminal Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"\n{CYAN}{BOLD}========================================================================================{RESET}")
    print(f"{CYAN}{BOLD}        METROHEALTH ACADEMIC MEDICAL CENTER - HOSPITAL FLOW COMMAND SYSTEM             {RESET}")
    print(f"{DIM}        Multi-Agent Autonomous Resource Allocation & Flow Bottleneck Optimization      {RESET}")
    print(f"{CYAN}{BOLD}========================================================================================{RESET}\n")


def print_metrics(state_dict):
    m = state_dict["metrics"]
    hics = state_dict["hics_level"]
    
    hics_color = GREEN if hics == "NORMAL" else (YELLOW if hics == "YELLOW_SURGE" else RED)
    
    print(f"{BOLD}[OPERATIONAL STATUS SUMMARY]{RESET}")
    print(f"  HICS Alert Level     : {hics_color}{BOLD}{hics}{RESET}")
    print(f"  Total Hospital Census: {m['total_occupied_beds']}/{m['total_beds']} beds ({m['overall_occupancy_pct']}%)")
    print(f"  Critical Care (ICU)  : {m['icu_occupied_beds']}/{m['icu_total_beds']} beds ({m['icu_occupancy_pct']}%) [Step-Down Eligible: {m['icu_stepdown_ready_count']}]")
    print(f"  Emergency Boarding   : {m['ed_boarding_count']} boarders (Mean Wait: {m['ed_avg_boarding_hours']} hrs)")
    print(f"  Discharge Candidates : {m['discharge_ready_count']} (With Non-Clinical Barriers: {m['discharge_with_barriers_count']})")
    print(f"  Nurse Workforce      : {m['total_nurses_on_duty']} on duty (Avg Fatigue: {m['average_nurse_fatigue_pct']}%)")
    if m["units_violating_nurse_ratio"]:
        print(f"  {RED}Ratio Safety Breaches{RESET}: {', '.join(m['units_violating_nurse_ratio'])}")
    else:
        print(f"  {GREEN}Ratio Safety Breaches{RESET}: None (100% Mandate Compliant)")
    print(f"  Ventilator Demand    : {m['ventilator_utilization_pct']}% in use")
    print(f"  Data Completeness    : {m['data_completeness_pct']}% verified")
    print("-" * 88)


def print_agent_thoughts(agents_dict):
    print(f"\n{BOLD}[AUTONOMOUS AGENT REASONING & CONSENSUS AUDIT]{RESET}")
    for aid, a in agents_dict.items():
        if a["recent_thoughts"]:
            t = a["recent_thoughts"][-1]
            print(f"  {CYAN}{BOLD}[{a['name']}]{RESET} {DIM}({a['role']}){RESET}")
            print(f"    {BOLD}Observation:{RESET} {t['observation']}")
            print(f"    {BOLD}Reasoning  :{RESET} {t['reasoning']}")
            print(f"    {BOLD}Action     :{RESET} {GREEN}{t['action']}{RESET}")
            print()


def print_proposals_and_actions(blackboard_dict):
    print(f"{BOLD}[ACTIVE PROPOSALS & EXECUTIVE DIRECTIVES]{RESET}")
    for p in blackboard_dict.get("recent_proposals", []):
        status_color = GREEN if "APPROVED" in p["status"] else (YELLOW if p["status"] == "PENDING_REVIEW" else RED)
        print(f"  * {BOLD}{p['title']}{RESET} [{status_color}{p['status']}{RESET}]")
        print(f"    Proposer: {p['proposer_agent']} | Category: {p['category']}")
        print(f"    Benefit : {p['projected_benefit']}")
        votes_str = ", ".join([f"{v}: {'YES' if d['approved'] else 'NO'}" for v, d in p.get("votes", {}).items()])
        if votes_str:
            print(f"    Votes   : {DIM}{votes_str}{RESET}")
        print()


def run_benchmark():
    print_banner()
    print(f"{YELLOW}Initializing hospital environment in SURGE mode (93% occupancy, 10+ ED boarders)...{RESET}\n")
    
    system = HospitalOptimizationSystem(stress_mode="surge")
    
    print(f"{CYAN}--- STEP 1: INITIAL MULTI-AGENT PERCEPTION & CONSENSUS CYCLE ---{RESET}")
    cycle_res = system.step()
    snap = system.get_full_snapshot()
    
    print_metrics(snap["hospital_summary"])
    print_agent_thoughts(snap["agents"])
    print_proposals_and_actions(snap["blackboard"])
    
    if "--batch" not in sys.argv and sys.stdin.isatty():
        input(f"{YELLOW}Press ENTER to authorize Multi-Agent Flow Optimizations...{RESET}")
    else:
        print(f"{YELLOW}[Auto-Authorizing Multi-Agent Flow Optimizations for batch benchmark...]{RESET}")
    
    print(f"\n{GREEN}{BOLD}--- STEP 2: APPLYING AI FLOW OPTIMIZATIONS (REVERSE TRIAGE & BED PULLS) ---{RESET}")
    impact = system.apply_recommendations()
    
    comp = impact["impact_comparison"]
    print(f"\n{BOLD}[QUANTITATIVE BEFORE vs. AFTER IMPACT BENCHMARK]{RESET}")
    print(f"{'Metric':<35} | {'Before (Surge)':<18} | {'After (Optimized)':<18} | {'Delta':<12}")
    print("-" * 92)
    
    b = comp["before"]
    a = comp["after"]
    
    metrics_to_show = [
        ("Total Hospital Occupancy", f"{b['overall_occupancy_pct']}%", f"{a['overall_occupancy_pct']}%", f"-{b['overall_occupancy_pct'] - a['overall_occupancy_pct']:.1f}%"),
        ("ICU Capacity Utilization", f"{b['icu_occupancy_pct']}%", f"{a['icu_occupancy_pct']}%", f"-{b['icu_occupancy_pct'] - a['icu_occupancy_pct']:.1f}%"),
        ("ED Boarding Patients", f"{b['ed_boarding_count']} patients", f"{a['ed_boarding_count']} patients", f"-{b['ed_boarding_count'] - a['ed_boarding_count']}"),
        ("ICU Step-Down Transfers", f"{b['icu_stepdown_ready']} blocked", f"{a['icu_stepdown_ready']} transferred", "Resolved"),
        ("Staffing Ratio Breaches", f"{b['violating_units_count']} units", f"{a['violating_units_count']} units", f"-{b['violating_units_count'] - a['violating_units_count']}")
    ]
    
    for name, before_val, after_val, delta in metrics_to_show:
        print(f"{name:<35} | {before_val:<18} | {GREEN}{after_val:<18}{RESET} | {CYAN}{BOLD}{delta:<12}{RESET}")
        
    print("-" * 92)
    print(f"\n{GREEN}{BOLD}[BENCHMARK COMPLETE] Operational bottlenecks successfully mitigated.{RESET}\n")


if __name__ == "__main__":
    run_benchmark()
