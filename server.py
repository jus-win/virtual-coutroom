"""
server.py
─────────
Lightweight HTTP server for the Virtual Courtroom Defendant Agent.
Uses pure Python standard library (http.server) — zero external web framework dependencies.
Provides REST API endpoints and serves the interactive Courtroom Web UI.

Usage:
    python server.py [--port 8000] [--no-browser]
"""

from __future__ import annotations
import sys
import json
import argparse
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket

# Reconfigure stdout for utf-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from defendant_agent.models import TrialStage, Speaker
from defendant_agent.database import CourtroomDatabase
from defendant_agent.agent import DefendantAgent
from seed_db import seed

WEB_DIR = Path(__file__).parent / "web"
INDEX_FILE = WEB_DIR / "index.html"


class CourtroomServerContext:
    """Global context holding the active DefendantAgent and CourtroomDatabase."""
    db: CourtroomDatabase = None
    agent: DefendantAgent = None


class CourtroomAPIHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for static web assets and REST API endpoints."""

    def _set_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html"):
            if not INDEX_FILE.exists():
                self._set_headers(404, "text/plain")
                self.wfile.write(b"index.html not found")
                return

            with open(INDEX_FILE, "rb") as f:
                content = f.read()
            self._set_headers(200, "text/html; charset=utf-8")
            self.wfile.write(content)

        elif path == "/api/status":
            status = CourtroomServerContext.agent.get_status()
            self._set_headers(200)
            self.wfile.write(json.dumps(status).encode("utf-8"))

        elif path == "/api/history":
            history = CourtroomServerContext.db.get_conversation_history(
                CourtroomServerContext.agent.case_id, limit=50
            )
            history_data = [
                {
                    "speaker": h.speaker.value,
                    "message": h.message,
                    "stage": h.stage.value,
                    "timestamp": h.timestamp,
                }
                for h in history
            ]
            self._set_headers(200)
            self.wfile.write(json.dumps(history_data).encode("utf-8"))

        elif path == "/api/brief":
            brief = CourtroomServerContext.agent.generate_defense_brief()
            self._set_headers(200)
            self.wfile.write(json.dumps(brief).encode("utf-8"))

        else:
            self._set_headers(404, "application/json")
            self.wfile.write(b'{"error": "Endpoint not found"}')

    def do_POST(self):
        path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            data = {}

        if path == "/api/turn":
            incoming_message = data.get("message")
            incoming_speaker = data.get("speaker", "JUDGE")

            response = CourtroomServerContext.agent.take_turn(
                incoming_message=incoming_message,
                incoming_speaker=incoming_speaker,
            )

            self._set_headers(200)
            self.wfile.write(
                json.dumps({
                    "response": response,
                    "stage": CourtroomServerContext.agent.state.current_stage.value,
                    "stage_label": CourtroomServerContext.agent.state.current_stage.label(),
                }).encode("utf-8")
            )

        elif path == "/api/stage":
            new_stage = data.get("stage")
            if new_stage:
                CourtroomServerContext.agent.advance_stage(new_stage)

            current_stage = CourtroomServerContext.agent.state.current_stage
            self._set_headers(200)
            self.wfile.write(
                json.dumps({
                    "stage": current_stage.value,
                    "stage_label": current_stage.label(),
                }).encode("utf-8")
            )

        elif path == "/api/witness":
            witness_id = data.get("witness_id")
            CourtroomServerContext.agent.set_cross_examination_witness(witness_id)
            self._set_headers(200)
            self.wfile.write(json.dumps({"witness_id": witness_id}).encode("utf-8"))

        elif path == "/api/ingest_case":
            file_base64 = data.get("file_base64")
            file_name = data.get("file_name", "uploaded_document")
            mime_type = data.get("mime_type")
            raw_text = data.get("raw_text", "").strip()

            try:
                if file_base64:
                    import base64
                    file_bytes = base64.b64decode(file_base64)
                    new_case = CourtroomServerContext.agent.ingest_case_file(
                        file_input=file_bytes,
                        file_name=file_name,
                        mime_type=mime_type,
                    )
                elif raw_text:
                    new_case = CourtroomServerContext.agent.ingest_new_case(raw_text)
                else:
                    self._set_headers(400, "application/json")
                    self.wfile.write(b'{"error": "Please provide either a file upload or raw_text"}')
                    return

                status = CourtroomServerContext.agent.get_status()
                brief = CourtroomServerContext.agent.generate_defense_brief()

                self._set_headers(200)
                self.wfile.write(
                    json.dumps({
                        "status": "success",
                        "case_id": new_case.case_id,
                        "case": status,
                        "brief": brief,
                    }).encode("utf-8")
                )
            except Exception as e:
                self._set_headers(500, "application/json")
                self.wfile.write(json.dumps({"error": f"Failed to ingest case: {str(e)}"}).encode("utf-8"))


        elif path == "/api/guidance":
            incoming_message = data.get("message")
            incoming_speaker = data.get("speaker")
            guidance = CourtroomServerContext.agent.get_co_counsel_guidance(
                incoming_message=incoming_message,
                incoming_speaker=incoming_speaker,
            )
            self._set_headers(200)
            self.wfile.write(json.dumps(guidance).encode("utf-8"))

        elif path == "/api/evaluate_defense":
            submission = data.get("submission", "").strip()
            feedback = CourtroomServerContext.agent.evaluate_student_defense(submission)
            self._set_headers(200)
            self.wfile.write(json.dumps({"feedback": feedback}).encode("utf-8"))

        else:
            self._set_headers(404, "application/json")
            self.wfile.write(b'{"error": "Endpoint not found"}')


    def log_message(self, format, *args):
        # Concise console logging
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")


def find_free_port(start_port: int = 8000) -> int:
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
            port += 1
    return start_port


def main():
    parser = argparse.ArgumentParser(description="Virtual Courtroom Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run server on")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    parser.add_argument("--case", default=None, help="Path to custom case JSON")
    parser.add_argument("--db", default="courtroom.db", help="Path to SQLite database")
    args = parser.parse_args()

    # 1. Seed & initialize database
    case = seed(args.case, db_path=args.db)
    db = CourtroomDatabase(db_path=args.db)
    agent = DefendantAgent(case_id=case.case_id, db=db)

    CourtroomServerContext.db = db
    CourtroomServerContext.agent = agent

    # 2. Select port
    port = find_free_port(args.port)
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, CourtroomAPIHandler)

    url = f"http://127.0.0.1:{port}"
    print("\n" + "=" * 65)
    print("  ⚖️   VIRTUAL COURTROOM WEB SERVER RUNNING")
    print(f"  Access URL:  {url}")
    print(f"  Case ID:     {case.case_id}")
    print(f"  Defendant:   {case.accused.name} (Age: {case.accused.age})")
    print(f"  Database:    {args.db} (SQLite)")
    print("=" * 65 + "\n")

    if not args.no_browser:
        print("[*] Opening default web browser...")
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down Virtual Courtroom server.")
        httpd.server_close()


if __name__ == "__main__":
    main()
