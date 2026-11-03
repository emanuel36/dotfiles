"""Serves /tmp/previews at localhost:8765 and saves POST /choice/<topic>.

Every served page follows the latest preview: it reloads when its own file changes and
navigates to another preview when that one is written. `/` redirects to the latest preview.
"""

import json
import os
import re
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = "/tmp/previews"
FOLLOW = (b"<script>new EventSource('/events').onmessage=e=>{const p='/'+e.data;"
          b"location.pathname===p?location.reload():location.assign(p)}</script>")
WAITING = b"<title>Previews</title><p style='font:16px sans-serif'>No preview yet.</p>"


def latest():
    """Returns the (mtime, name) of the most recently written preview, or (0, None)."""
    pages = []
    for name in os.listdir(ROOT):
        if name.endswith(".html"):
            try:
                pages.append((os.stat(os.path.join(ROOT, name)).st_mtime, name))
            except FileNotFoundError:
                pass
    return max(pages, default=(0, None))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, *args):
        pass

    def send_page(self, body):
        body += FOLLOW
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            seen = latest()
            try:
                while True:
                    time.sleep(0.5)
                    now = latest()
                    if now != seen and now[1]:
                        self.wfile.write(f"data: {now[1]}\n\n".encode())
                        self.wfile.flush()
                        return
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
        if self.path == "/":
            name = latest()[1]
            if not name:
                self.send_page(WAITING)
                return
            self.send_response(302)
            self.send_header("Location", f"/{name}")
            self.end_headers()
            return
        path = self.translate_path(self.path.split("?")[0])
        if path.endswith(".html") and os.path.isfile(path):
            with open(path, "rb") as f:
                self.send_page(f.read())
            return
        super().do_GET()

    def do_POST(self):
        m = re.fullmatch(r"/choice/([A-Za-z0-9_-]+)", self.path)
        if not m:
            self.send_error(404)
            return
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        with open(os.path.join(ROOT, f"{m.group(1)}.choice.json"), "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.send_response(200)
        self.end_headers()


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
