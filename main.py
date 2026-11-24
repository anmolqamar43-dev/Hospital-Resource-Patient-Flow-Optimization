
"""
Hospital Resource & Patient Flow Optimization
FastAPI entry point for Vercel deployment.
"""

import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Body, HTTPException
from fastapi.responses import FileResponse

# Project root
BASE_DIR = Path(__file__).resolve().parent
os.chdir(BASE_DIR)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.system import HospitalOptimizationSystem
from src.framework.chatbot import HospitalOperationsChatbot
from src.framework.llm_client import llm_client


app = FastAPI(
    title="Hospital Resource & Patient Flow Optimization",
    version="1.0.0"
)

# Initial hospital state
system = HospitalOptimizationSystem(stress_mode="surge")
system.step()

chatbot = HospitalOperationsChatbot(system)


# ---------------- FRONTEND ----------------

@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/style.css", include_in_schema=False)
def styles():
    return FileResponse(
        BASE_DIR / "style.css",
        media_type="text/css"
    )


@app.get("/app.js", include_in_schema=False)
def javascript():
    return FileResponse(
        BASE_DIR / "app.js",
        media_type="application/javascript"
    )


# ---------------- API ENDPOINTS ----------------

@app.get("/api/status")
def get_status():
    return system.get_full_snapshot()


@app.get("/api/export")
def export_status():
    return system.get_full_snapshot()


@app.post("/api/step")
def run_step():
    return system.step()


@app.post("/api/agent/step")
def run_agent(payload: dict[str, Any] = Body(default={})):
    agent_id = payload.get("agent_id", "triage_influx_agent")
    return system.step_single_agent(agent_id)


@app.post("/api/config/llm")
def configure_llm(payload: dict[str, Any] = Body(default={})):
    """
    API keys should be configured through Vercel Environment Variables,
    not stored from browser requests.
    """
    return {
        "success": True,
        "llm_config": llm_client.get_status_summary(),
        "message": "Configure API keys in Vercel Environment Variables."
    }


@app.post("/api/optimize")
def optimize_resources():
    return system.apply_recommendations()


@app.post("/api/chat")
def chat(payload: dict[str, Any] = Body(default={})):
    user_msg = payload.get("message", "").strip()

    if not user_msg:
        raise HTTPException(
            status_code=400,
            detail="Empty message"
        )

    return chatbot.handle_message(user_msg)


@app.post("/api/scenario")
def change_scenario(payload: dict[str, Any] = Body(default={})):
    global system, chatbot

    scenario_type = payload.get("type", "surge")

    if scenario_type == "reset":
        system = HospitalOptimizationSystem(stress_mode="baseline")
        system.step()
        chatbot.system = system

        return {
            "success": True,
            "message": "Hospital state reset to baseline operations."
        }

    return system.trigger_stress_scenario(scenario_type)
