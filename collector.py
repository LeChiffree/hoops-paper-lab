"""Tiny local collector: the browser POSTs raw API bytes here, we save them."""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(OUT, exist_ok=True)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class H(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/file/"):
            name = self.path[len("/file/"):].split("?")[0].strip("/")
            path = os.path.join(BASE_DIR, name)
            if os.path.exists(path) and os.path.isfile(path):
                data = open(path, "rb").read()
                self.send_response(200)
                self._cors()
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(data)
                return
            self.send_response(404); self._cors(); self.end_headers(); return
        if self.path.startswith("/have/"):
            name = self.path[len("/have/"):].strip("/")
            name = "".join(c for c in name if c.isalnum() or c in "-_.")[:80]
            exists = os.path.exists(os.path.join(OUT, name + ".bin"))
            self.send_response(200 if exists else 404)
            self._cors()
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"1" if exists else b"0")
            return
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"collector ok")

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(n)
        name = self.path.strip("/").replace("/", "_") or "dump"
        name = "".join(c for c in name if c.isalnum() or c in "-_.")[:80]
        path = os.path.join(OUT, name + ".bin")
        with open(path, "wb") as f:
            f.write(data)
        print(f"saved {path} {len(data)} bytes", flush=True)
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    print("collector on http://127.0.0.1:8899", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8899), H).serve_forever()
