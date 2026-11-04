"""Serves /tmp/previews at localhost:8765 and saves POST /choice/<topic>.

Every served page follows the latest preview: it reloads when its own file changes and moves
to another preview when that one is written. A written preview opens a window on the secondary
monitor when none is open, and a saved choice closes it. `/` redirects to the latest preview.
"""

import json
import os
import re
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = "/tmp/previews"
URL = "http://localhost:8765/"
FOLLOW = (b"<script>new EventSource('/events').onmessage=e=>{if(e.data==='close')"
          b"return window.close();const p='/'+e.data;"
          b"location.pathname===p?location.reload():location.replace(p)}</script>")
WAITING = b"<title>Previews</title><p style='font:16px sans-serif'>No preview yet.</p>"
MONITOR = re.compile(r"(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)")

closes = 0  # Incremented on every saved choice; each open page closes when it changes.


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


def windows():
    found = subprocess.run(["xdotool", "search", "--classname", "^localhost"],
                           capture_output=True, text=True)
    return found.stdout.split()


def place(x, y, w, h):
    """Moves the new window onto the monitor at x,y of size w,h once the window manager has
    placed it, retrying until it lands there."""
    for _ in range(20):
        time.sleep(0.5)
        for win in windows():
            subprocess.run(["xdotool", "windowmove", win, str(x), str(y),
                            "windowsize", win, str(w), str(h)])
            time.sleep(0.3)
            geometry = subprocess.run(["xdotool", "getwindowgeometry", win],
                                      capture_output=True, text=True).stdout
            m = re.search(r"Position: (-?\d+),", geometry)
            if m and x <= int(m.group(1)) < x + w:
                return


def open_window():
    """Opens the preview window on the first non-primary monitor, or wherever Chrome likes."""
    monitors = subprocess.run(["xrandr", "--listmonitors"], capture_output=True, text=True)
    secondary = [line.split()[2] for line in monitors.stdout.splitlines()[1:]
                 if "*" not in line.split()[1]]
    m = MONITOR.fullmatch(secondary[0]) if secondary else None
    subprocess.Popen(["google-chrome", f"--app={URL}"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    if m:
        w, h, x, y = map(int, m.groups())
        # Chrome ignores --window-position when it is already running, so move the window.
        threading.Thread(target=place, args=(x, y, w, h), daemon=True).start()


def watch():
    """Opens a window whenever a preview is written and no window is open, ignoring deletions."""
    seen = latest()
    while True:
        time.sleep(0.5)
        now = latest()
        # Deleting a preview leaves an older one as the latest, which is not a new write.
        if now[0] <= seen[0]:
            continue
        seen = now
        if os.environ.get("DISPLAY"):
            try:
                if not windows():
                    open_window()
            except OSError:
                pass  # A missing tool must not stop the watcher; the next write retries.


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
            seen, seen_closes = latest(), closes
            try:
                while True:
                    time.sleep(0.5)
                    if closes != seen_closes:
                        self.wfile.write(b"data: close\n\n")
                        self.wfile.flush()
                        return
                    now = latest()
                    if now[0] > seen[0]:
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
        global closes
        m = re.fullmatch(r"/choice/([A-Za-z0-9_-]+)", self.path)
        if not m:
            self.send_error(404)
            return
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        with open(os.path.join(ROOT, f"{m.group(1)}.choice.json"), "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.send_response(200)
        self.end_headers()
        closes += 1


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    threading.Thread(target=watch, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
