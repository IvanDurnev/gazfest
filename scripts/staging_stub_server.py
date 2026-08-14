import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

HOST = os.getenv("STUB_HOST", "127.0.0.1")
PORT = int(os.getenv("STUB_PORT", "19001"))
OPENAI_DELAY_SECONDS = float(os.getenv("STUB_OPENAI_DELAY_SECONDS", "0.2"))

COUNTS = {
    "openai_responses": 0,
    "max_actions": 0,
    "max_messages": 0,
}
COUNTS_LOCK = threading.Lock()


class StubHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/metrics":
            with COUNTS_LOCK:
                counts = dict(COUNTS)
            self.send_json(200, counts)
            return
        if path == "/me":
            self.send_json(200, {"username": "gazfest-staging"})
            return
        self.send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length:
            self.rfile.read(content_length)

        if path == "/v1/responses":
            time.sleep(OPENAI_DELAY_SECONDS)
            with COUNTS_LOCK:
                COUNTS["openai_responses"] += 1
                response_number = COUNTS["openai_responses"]
            self.send_json(
                200,
                {
                    "id": f"resp_staging_{response_number}",
                    "object": "response",
                    "created_at": int(time.time()),
                    "status": "completed",
                    "model": "gpt-5.6-terra",
                    "output": [
                        {
                            "id": f"msg_staging_{response_number}",
                            "type": "message",
                            "status": "completed",
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": "Тестовый ответ Гели",
                                    "annotations": [],
                                }
                            ],
                        }
                    ],
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 10,
                        "total_tokens": 110,
                    },
                },
            )
            return

        if path.endswith("/actions"):
            with COUNTS_LOCK:
                COUNTS["max_actions"] += 1
            self.send_json(200, {"success": True})
            return

        if path == "/messages":
            with COUNTS_LOCK:
                COUNTS["max_messages"] += 1
            self.send_json(200, {"success": True})
            return

        self.send_json(404, {"error": "not_found"})


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), StubHandler)
    print(f"staging stubs listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
