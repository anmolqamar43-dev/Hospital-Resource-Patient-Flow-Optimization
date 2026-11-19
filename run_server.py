"""
Hospital Operations Command Center - HTTP Web Server & REST API.
Serves interactive dashboard and provides real-time multi-agent API endpoints.
"""

import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import sys

from src.system import HospitalOptimizationSystem

# Global singleton system instance for web session
system = HospitalOptimizationSystem(stress_mode="surge")
system.step()  # Run initial perception cycle


class CommandCenterHandler(BaseHTTPRequestHandler):

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
            self._serve_static_file("src/web/index.html", "text/html")
        elif path == "/styles.css":
            self._serve_static_file("src/web/styles.css", "text/css")
        elif path == "/app.js":
            self._serve_static_file("src/web/app.js", "application/javascript")
        elif path == "/api/status":
            self._set_headers(200, "application/json")
            data = system.get_full_snapshot()
            self.wfile.write(json.dumps(data).encode("utf-8"))
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

        elif path == "/api/optimize":
            impact = system.apply_recommendations()
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(impact).encode("utf-8"))

        elif path == "/api/scenario":
            scenario_type = payload.get("type", "surge")
            if scenario_type == "reset":
                system = HospitalOptimizationSystem(stress_mode="baseline")
                system.step()
                res = {"success": True, "message": "System reset to baseline operations."}
            else:
                res = system.trigger_stress_scenario(scenario_type)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps(res).encode("utf-8"))

        else:
            self.send_error(404, "API endpoint not found")

    def _serve_static_file(self, filepath: str, content_type: str):
        if not os.path.exists(filepath):
            self.send_error(404, f"File {filepath} not found")
            return

        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self._set_headers(200, content_type)
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Error reading file: {str(e)}")

    def log_message(self, format, *args):
        # Concise logging
        pass


def run_server(port: int = 8080):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, CommandCenterHandler)
    print(f"\n[METROHEALTH COMMAND CENTER] Server running at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop the server.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Command Center server...")
        httpd.server_close()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
