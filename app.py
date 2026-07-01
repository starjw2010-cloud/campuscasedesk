from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import mcp_adapter  # noqa: E402


HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8771"))
MCP_AUTH_MODE = os.environ.get("MCP_AUTH_MODE", "").strip().lower()
MCP_SHARED_SECRET = os.environ.get("MCP_SHARED_SECRET", "")
IMPORT_MARIADB_ON_START = os.environ.get("IMPORT_MARIADB_ON_START", "").strip().lower() in {"1", "true", "yes"}


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class CampusCaseDeskHandler(BaseHTTPRequestHandler):
    server_version = "campuscasedesk/0.1"

    def do_GET(self):
        if self.path == "/health":
            return json_response(self, 200, {"ok": True, "service": "campuscasedesk"})
        if self.path == "/mcp/health":
            return json_response(self, 200, {"ok": True, "service": "campuscasedesk-mcp", "tools": len(mcp_adapter.tool_definitions())})
        return json_response(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self):
        if self.path != "/mcp":
            return json_response(self, 404, {"ok": False, "error": "not_found"})
        if not self._mcp_authorized():
            return json_response(self, 401, {"ok": False, "error": "invalid MCP shared secret"})
        try:
            payload = self._read_json()
            return json_response(self, 200, mcp_adapter.handle_json_rpc(payload))
        except Exception as exc:
            return json_response(self, 500, {"ok": False, "error": f"{type(exc).__name__}: {exc}"})

    def _read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _mcp_authorized(self):
        if MCP_AUTH_MODE in {"no_auth", "public", "demo"}:
            return True
        if not MCP_SHARED_SECRET:
            return True
        return self.headers.get("X-CampusCaseDesk-Secret") == MCP_SHARED_SECRET


def main():
    if IMPORT_MARIADB_ON_START:
        print("IMPORT_MARIADB_ON_START=true; importing JSONL/RAG seed into MariaDB-compatible backend")
        import import_mariadb  # noqa: WPS433

        import_mariadb.main()
    server = ThreadingHTTPServer((HOST, PORT), CampusCaseDeskHandler)
    print(f"campuscasedesk listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
