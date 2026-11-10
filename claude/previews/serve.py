"""Serves /tmp/previews at localhost:8765 and saves POST /choice/<topic>.

Each preview has its own window, so previews written by different sessions do not replace each
other. A written preview opens a window on the secondary monitor when none shows it, the page
reloads when its own file changes, and a saved choice closes only the windows of that preview.
`/` redirects to the latest preview.

Every written version of a preview is kept, and previews that mark variants with `data-variant`
get a choice bar (bar.html) that switches variants, lists versions and confirms the choice.
"""

import json
import os
import re
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlsplit

import store

ROOT = store.ROOT
URL = "http://localhost:8765/"
BAR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bar.html")
OLD_VERSION = re.compile(r"\.history/([A-Za-z0-9_-]+)/(\d+)\.html")
FOLLOW = ("<script>new EventSource('/events?page={page}&mtime={mtime}')"
          ".onmessage=e=>e.data==='close'?window.close():location.reload()</script>")
WAITING = b"<title>Previews</title><p style='font:16px sans-serif'>No preview yet.</p>"
MONITOR = re.compile(r"(\d+)/\d+x(\d+)/\d+\+(\d+)\+(\d+)")
CONNECT_GRACE = 15  # Seconds a new window has to connect before its preview may open another.
SETTLE = 1.0  # Seconds a preview must stay unchanged before it is saved as a version.

lock = threading.Lock()
viewers = {}  # Preview name -> number of open pages showing it.
opened = {}  # Preview name -> time its window was last opened.
closes = {}  # Preview name -> number of choices saved from it; its pages close when it changes.
claimed = set()  # Windows already moved to the secondary monitor by a place() thread.


def mtimes():
    """Returns {name: mtime} of every preview in ROOT."""
    pages = {}
    for name in os.listdir(ROOT):
        if name.endswith(".html"):
            try:
                pages[name] = os.stat(os.path.join(ROOT, name)).st_mtime
            except FileNotFoundError:
                pass
    return pages


def mtime(name):
    """Returns the mtime of preview `name`, or None when it does not exist."""
    try:
        return os.stat(os.path.join(ROOT, name)).st_mtime
    except (FileNotFoundError, NotADirectoryError):
        return None


def latest():
    """Returns the name of the most recently written preview, or None."""
    pages = mtimes()
    return max(pages, key=pages.get, default=None)


def windows():
    found = subprocess.run(["xdotool", "search", "--classname", "^localhost"],
                           capture_output=True, text=True)
    return set(found.stdout.split())


def place(before, x, y, w, h):
    """Moves the first window that was not in `before` and that no other place() claimed onto
    the monitor at x,y of size w,h once the window manager has placed it, retrying until it
    lands there."""
    win = None
    for _ in range(20):
        time.sleep(0.5)
        if win is None:
            with lock:
                new = sorted(windows() - before - claimed)
                if not new:
                    continue
                win = new[0]
                claimed.add(win)
        subprocess.run(["xdotool", "windowmove", win, str(x), str(y),
                        "windowsize", win, str(w), str(h)])
        time.sleep(0.3)
        geometry = subprocess.run(["xdotool", "getwindowgeometry", win],
                                  capture_output=True, text=True).stdout
        m = re.search(r"Position: (-?\d+),", geometry)
        if m and x <= int(m.group(1)) < x + w:
            return


def open_window(name):
    """Opens a window for preview `name` on the first non-primary monitor, or wherever Chrome
    likes."""
    monitors = subprocess.run(["xrandr", "--listmonitors"], capture_output=True, text=True)
    secondary = [line.split()[2] for line in monitors.stdout.splitlines()[1:]
                 if "*" not in line.split()[1]]
    m = MONITOR.fullmatch(secondary[0]) if secondary else None
    before = windows()
    subprocess.Popen(["google-chrome", f"--app={URL}{quote(name)}"], stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
    if m:
        w, h, x, y = map(int, m.groups())
        # Chrome ignores --window-position when it is already running, so move the window.
        threading.Thread(target=place, args=(before, x, y, w, h), daemon=True).start()


def watch():
    """Saves every written preview as a version once it settles and opens a window for every
    written preview that no open page shows, ignoring deletions."""
    seen = mtimes()
    saved = {}  # Preview name -> mtime last saved as a version.
    while True:
        time.sleep(0.5)
        now = mtimes()
        written = [name for name, mtime in now.items() if mtime > seen.get(name, 0)]
        seen = now
        for name, mtime in now.items():
            topic = name.removesuffix(".html")
            if saved.get(name) != mtime and store.TOPIC.fullmatch(topic):
                with lock:
                    if store.snapshot(topic, SETTLE) is not None:
                        saved[name] = mtime
        if not os.environ.get("DISPLAY"):
            continue
        for name in written:
            with lock:
                # A page that is open reloads by itself; a window just opened is still loading.
                if viewers.get(name) or time.time() - opened.get(name, 0) < CONNECT_GRACE:
                    continue
                opened[name] = time.time()
            try:
                open_window(name)
            except OSError:
                # A missing tool must not stop the watcher; the next write retries.
                with lock:
                    opened.pop(name, None)


def with_bar(body, name):
    """Returns page `body` with the choice bar when `name` is a preview or one of its saved
    versions; the bar shows itself only on pages that need it."""
    topic = name.removesuffix(".html")
    if name.endswith(".html") and store.TOPIC.fullmatch(topic):
        # A file still being written has no version yet; the choice gets one when posted.
        with lock:
            version = store.snapshot(topic, SETTLE)
        current = True
    elif m := OLD_VERSION.fullmatch(name):
        topic, version = m.group(1), int(m.group(2))
        current = False
    else:
        return body
    saved = store.versions(topic)
    config = {"topic": topic, "version": version, "versions": saved,
              "current": current or bool(saved) and version == saved[-1]}
    with open(BAR, "rb") as f:
        bar = (f"<script>window.__preview={json.dumps(config)}</script>").encode() + f.read()
    end = body.lower().rfind(b"</body>")
    return body[:end] + bar + body[end:] if end >= 0 else body + bar


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def log_message(self, *args):
        pass

    def send_page(self, body, name="", served=None):
        body = with_bar(body, name) + FOLLOW.format(page=quote(name, safe=""),
                                                    mtime=served).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def events(self, name, served):
        """Streams `reload` when preview `name` differs from the version served at mtime
        `served` and `close` when a choice is saved from it. The page with no preview closes
        once one is written, since the watcher opens a window for it."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with lock:
            viewers[name] = viewers.get(name, 0) + 1
            opened.pop(name, None)
            seen_closes = closes.get(name, 0)
        try:
            while True:
                time.sleep(0.5)
                if closes.get(name, 0) != seen_closes or (not name and latest()):
                    self.wfile.write(b"data: close\n\n")
                    self.wfile.flush()
                    return
                now = mtime(name) if name else None
                if now and str(now) != served:
                    self.wfile.write(b"data: reload\n\n")
                    self.wfile.flush()
                    with lock:
                        # The page reconnects after reloading; until then it still shows.
                        opened[name] = time.time()
                    return
                self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return
        finally:
            with lock:
                viewers[name] -= 1

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/events":
            query = parse_qs(url.query)
            self.events(query.get("page", [""])[0], query.get("mtime", [""])[0])
            return
        if url.path == "/":
            name = latest()
            if not name:
                self.send_page(WAITING)
                return
            self.send_response(302)
            self.send_header("Location", f"/{quote(name)}")
            self.end_headers()
            return
        path = self.translate_path(url.path)
        if path.endswith(".html") and os.path.isfile(path):
            with open(path, "rb") as f:
                self.send_page(f.read(), os.path.relpath(path, ROOT), os.fstat(f.fileno()).st_mtime)
            return
        super().do_GET()

    def do_POST(self):
        m = re.fullmatch(r"/choice/([A-Za-z0-9_-]+)", self.path)
        if not m:
            self.send_error(404)
            return
        topic = m.group(1)
        if not os.path.isfile(os.path.join(ROOT, f"{topic}.html")):
            self.send_error(404, f"No preview {topic}.html")
            return
        data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if not isinstance(data, dict):
            data = {"data": data}
        if store.valid_version(topic, data.get("version")) is None:
            with lock:
                data["version"] = store.snapshot(topic)
        with open(os.path.join(ROOT, f"{topic}.choice.json"), "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        self.send_response(200)
        self.end_headers()
        # Close the page that posted, even when its file name differs from the topic.
        referer = unquote(urlsplit(self.headers.get("Referer", "")).path)
        pages = {f"{topic}.html", os.path.basename(referer)}
        with lock:
            for name in pages - {""}:
                closes[name] = closes.get(name, 0) + 1


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    threading.Thread(target=watch, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
