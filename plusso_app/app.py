import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from svs import SvsInput, compute_svs

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
}


class PlussoHandler(BaseHTTPRequestHandler):
    def _send_bytes(self, content: bytes, content_type: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: dict, status: int = 200):
        self._send_bytes(json.dumps(payload).encode("utf-8"), "application/json; charset=utf-8", status)

    def _serve_file(self, file_path: Path):
        ext = file_path.suffix.lower()
        content_type = MIME_TYPES.get(ext, "application/octet-stream")
        return self._send_bytes(file_path.read_bytes(), content_type)

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            return self._serve_file(TEMPLATES_DIR / "index.html")

        if path == "/api/health":
            return self._send_json({"status": "ok", "service": "plusso-mvp"})

        if path.startswith("/static/"):
            relative_path = path.replace("/static/", "", 1)
            file_path = (STATIC_DIR / relative_path).resolve()
            if not str(file_path).startswith(str(STATIC_DIR.resolve())) or not file_path.exists():
                return self._send_json({"error": "Datei nicht gefunden"}, 404)
            return self._serve_file(file_path)

        return self._send_json({"error": "Route nicht gefunden"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/api/calculate":
            return self._send_json({"error": "Route nicht gefunden"}, 404)

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body or "{}")

            result = compute_svs(
                SvsInput(
                    total_costs=float(payload.get("total_costs", 0)),
                    productive_hours_per_employee=float(payload.get("productive_hours", 0)),
                    employee_count=int(payload.get("employee_count", 0)),
                    risk_buffer_pct=float(payload.get("risk_buffer_pct", 0)),
                    regional_avg=float(payload.get("regional_avg", 0)),
                )
            )

            return self._send_json(
                {
                    "svs": result.final_svs,
                    "base_svs": result.base_svs,
                    "risk_buffer_amount": result.risk_buffer_amount,
                    "benchmark_delta": result.benchmark_delta,
                    "benchmark_trend": result.benchmark_trend,
                }
            )
        except ValueError as err:
            return self._send_json({"error": str(err)}, 400)
        except json.JSONDecodeError:
            return self._send_json({"error": "Ungültiges JSON"}, 400)
        except Exception:
            return self._send_json({"error": "Interner Fehler"}, 500)


def run(host: str = "0.0.0.0", port: int = 5050):
    server = HTTPServer((host, port), PlussoHandler)
    print(f"Plusso MVP läuft auf http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
