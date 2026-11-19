"""
Hospital Resource & Patient Flow Optimization - Web Server & REST API.
Serves index.html, style.css, app.js and exposes real-time multi-agent API endpoints.
"""

import os
import sys
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from src.system import HospitalOptimizationSystem
from src.framework.chatbot import HospitalOperationsChatbot

# Global singleton hospital operations system instance
# Starts in surge state to immediately demonstrate flow bottlenecks and multi-agent coordination
system = HospitalOptimizationSystem(stress_mode="surge")
system.step()  # Initial sense-think cycle

# Initialize operations copilot chatbot
chatbot = HospitalOperationsChatbot(system)


class HospitalAppHandler(BaseHTTPRequestHandler):

    def _set_headers(self, status_code=200, content_type="application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html"]:
            self._serve_static_file("index.html", "text/html")
        elif path == "/style.css":
            self._serve_static_file("style.css", "text/css")
        elif path == "/app.js":
            self._serve_static_file("app.js", "application/javascript")
        elif path == "/api/status":
            self._set_headers(200, "application/json")
            data = system.get_full_snapshot()
            self.wfile.write(json.dumps(data).encode("utf-8"))
        elif path == "/api/export":
            self._set_headers(200, "application/json")
            data = system.get_full_snapshot()
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        global system

        if path == "/api/step":
            cycle_res = system.step()
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(cycle_res).encode("utf-8"))

        elif path == "/api/agent/step":
            agent_id = payload.get("agent_id", "triage_influx_agent")
            res = system.step_single_agent(agent_id)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(res).encode("utf-8"))

        elif path == "/api/config/llm":
            # Update key in .env and reload
            gemini_key = payload.get("gemini_api_key", "").strip()
            openai_key = payload.get("openai_api_key", "").strip()
            
            from src.framework.llm_client import llm_client
            if gemini_key:
                os.environ["GEMINI_API_KEY"] = gemini_key
                llm_client.gemini_key = gemini_key
            if openai_key:
                os.environ["OPENAI_API_KEY"] = openai_key
                llm_client.openai_key = openai_key

            summary = llm_client.get_status_summary()
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"success": True, "llm_config": summary}).encode("utf-8"))

        elif path == "/api/optimize":
            impact = system.apply_recommendations()
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(impact).encode("utf-8"))

        elif path == "/api/chat":
            user_msg = payload.get("message", "").strip()
            if not user_msg:
                self._set_headers(400, "application/json")
                self.wfile.write(json.dumps({"error": "Empty message"}).encode("utf-8"))
                return
            
            chat_res = chatbot.handle_message(user_msg)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(chat_res).encode("utf-8"))

        elif path == "/api/scenario":
            scenario_type = payload.get("type", "surge")
            if scenario_type == "reset":
                system = HospitalOptimizationSystem(stress_mode="baseline")
                system.step()
                chatbot.system = system
                res = {"success": True, "message": "Hospital state reset to baseline operations."}
            else:
                res = system.trigger_stress_scenario(scenario_type)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(res).encode("utf-8"))

        else:
            self.send_error(404, "API endpoint not found")

    def _serve_static_file(self, filepath: str, content_type: str):
        # Resolve path relative to current script directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(base_dir, filepath)

        if not os.path.exists(full_path):
            self.send_error(404, f"File {filepath} not found")
            return

        try:
            with open(full_path, "rb") as f:
                content = f.read()
            self._set_headers(200, content_type)
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {str(e)}")

    def log_message(self, format, *args):
        # Keep console output clean
        pass


def start_app(port: int = 8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, HospitalAppHandler)
    print("=" * 80)
    print("  METROHEALTH ACADEMIC MEDICAL CENTER - COMMAND CENTER SERVER")
    print(f"  Web UI is running at: http://localhost:{port}")
    print(f"  Serving: index.html, style.css, app.js, app.py")
    print("  Press Ctrl+C to stop the server.")
    print("=" * 80)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCommand Center server shutdown successfully.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    start_app(port)
