#!/usr/bin/env python3
"""
DDoS Lab - Victim Service
=========================

A deliberately small, instrumented target so learners can *watch* a service
degrade under load and recover behind a defense. It is NOT a production server;
its limits are intentionally tiny so saturation is visible on a laptop.

Three data-plane listeners model the layers an attacker hits, plus one
always-responsive admin plane so the dashboard keeps working even while the
service is being overwhelmed:

  :8080  HTTP service   (Layer 7)  - bounded worker pool; returns 503 when full
  :8082  raw TCP        (Layer 4)  - bounded connection table; refuses when full
  :8081  UDP            (Layer 4)  - token-bucket "processing budget"; drops excess
  :9090  admin/metrics/dashboard   - lightweight, not subject to the limits above

Everything is Python standard library only, so the container image builds with
no third-party dependencies.
"""

import json
import os
import socket
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Tunables (override via environment) ------------------------------------
# Kept small on purpose: a tiny victim saturates under modest, safe load.
HTTP_WORKERS = int(os.environ.get("HTTP_WORKERS", "50"))       # max concurrent HTTP requests
HTTP_WORK_MS = int(os.environ.get("HTTP_WORK_MS", "50"))       # simulated work per request
TCP_MAX_CONN = int(os.environ.get("TCP_MAX_CONN", "200"))      # max concurrent TCP connections
UDP_CAPACITY = int(os.environ.get("UDP_CAPACITY", "2000"))     # packets/sec the app can "process"
HISTORY_LEN = int(os.environ.get("HISTORY_LEN", "60"))         # seconds of history for sparklines

HTTP_PORT = int(os.environ.get("HTTP_PORT", "8080"))
UDP_PORT = int(os.environ.get("UDP_PORT", "8081"))
TCP_PORT = int(os.environ.get("TCP_PORT", "8082"))
ADMIN_PORT = int(os.environ.get("ADMIN_PORT", "9090"))

DASHBOARD_HTML = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")

# --- Shared state -----------------------------------------------------------
_lock = threading.Lock()
_worker_sem = threading.BoundedSemaphore(HTTP_WORKERS)
_tcp_sem = threading.BoundedSemaphore(TCP_MAX_CONN)

M = {
    "http": {"total": 0, "served": 0, "rejected": 0, "in_flight": 0,
             "rps": 0.0, "reject_rps": 0.0, "last_latency_ms": 0.0},
    "tcp": {"total": 0, "active": 0, "refused": 0, "cps": 0.0},
    "udp": {"packets": 0, "bytes": 0, "processed": 0, "dropped": 0, "pps": 0.0, "drop_rps": 0.0},
    "config": {"http_workers": HTTP_WORKERS, "http_work_ms": HTTP_WORK_MS,
               "tcp_max_conn": TCP_MAX_CONN, "udp_capacity": UDP_CAPACITY},
    "history": {"http_rps": [], "http_reject_rps": [], "udp_pps": [], "udp_drop_rps": []},
    "started_at": time.time(),
}

# UDP token bucket, refilled once per second by the sampler thread.
_udp_tokens = UDP_CAPACITY

# Baseline the sampler diffs against; reset alongside the counters so per-second
# rates never go negative right after /reset.
_prev = {"http_total": 0, "http_rejected": 0, "udp_packets": 0, "udp_dropped": 0, "tcp_total": 0}


def _health():
    """Derive a simple health label from current rejection pressure."""
    h = M["http"]
    total_rate = h["rps"] + h["reject_rps"]
    reject_ratio = (h["reject_rps"] / total_rate) if total_rate > 0 else 0.0
    if reject_ratio > 0.5 or M["tcp"]["active"] >= TCP_MAX_CONN:
        return "overwhelmed"
    if reject_ratio > 0.05 or M["udp"]["drop_rps"] > 0:
        return "degraded"
    return "healthy"


# --- HTTP service (Layer 7 target) ------------------------------------------
class ServiceHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _handle(self, write_body=True):
        with _lock:
            M["http"]["total"] += 1

        # Model a finite worker pool: if all workers are busy, shed load (503).
        if not _worker_sem.acquire(blocking=False):
            with _lock:
                M["http"]["rejected"] += 1
            self._respond(503, b"503 Service Unavailable: worker pool exhausted\n", write_body)
            return

        try:
            with _lock:
                M["http"]["in_flight"] += 1
            start = time.perf_counter()
            time.sleep(HTTP_WORK_MS / 1000.0)  # simulated request work
            latency_ms = (time.perf_counter() - start) * 1000.0
            with _lock:
                M["http"]["served"] += 1
                M["http"]["last_latency_ms"] = round(latency_ms, 2)
            self._respond(200, b"OK\n", write_body)
        finally:
            with _lock:
                M["http"]["in_flight"] -= 1
            _worker_sem.release()

    def _respond(self, code, body, write_body=True):
        try:
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if write_body:
                self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self._handle(write_body=True)

    def do_POST(self):
        self._handle(write_body=True)

    def do_HEAD(self):
        self._handle(write_body=False)

    def log_message(self, *args):
        pass  # keep stdout clean under load


# --- Raw TCP service (Layer 4 connection-flood target) ----------------------
class TCPConnHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # Model a finite connection table.
        if not _tcp_sem.acquire(blocking=False):
            with _lock:
                M["tcp"]["refused"] += 1
            try:
                self.request.close()
            except OSError:
                pass
            return
        try:
            with _lock:
                M["tcp"]["total"] += 1
                M["tcp"]["active"] += 1
            self.request.settimeout(10)
            # Hold the connection until the client leaves or times out. This is
            # what makes connection-exhaustion visible: attacker holds sockets.
            try:
                while True:
                    data = self.request.recv(1024)
                    if not data:
                        break
            except (socket.timeout, OSError):
                pass
        finally:
            with _lock:
                M["tcp"]["active"] -= 1
            _tcp_sem.release()


class ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


# --- UDP service (Layer 4 flood target) -------------------------------------
def udp_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", UDP_PORT))
    global _udp_tokens
    while True:
        try:
            data, _addr = sock.recvfrom(65535)
        except OSError:
            continue
        with _lock:
            M["udp"]["packets"] += 1
            M["udp"]["bytes"] += len(data)
            # Token bucket: only UDP_CAPACITY packets/sec can be "processed";
            # everything beyond that is dropped, as a real stack would drop.
            if _udp_tokens > 0:
                _udp_tokens -= 1
                M["udp"]["processed"] += 1
            else:
                M["udp"]["dropped"] += 1


# --- Admin / metrics / dashboard (always responsive) ------------------------
class AdminHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body, content_type):
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/metrics":
            with _lock:
                snapshot = json.loads(json.dumps(M))  # cheap deep copy under lock
            snapshot["health"] = _health()
            snapshot["uptime_s"] = round(time.time() - M["started_at"], 1)
            self._send(200, json.dumps(snapshot).encode(), "application/json")
        elif path == "/healthz":
            self._send(200, b'{"ok":true}', "application/json")
        elif path == "/reset":
            _reset_counters()
            self._send(200, b'{"reset":true}', "application/json")
        elif path in ("/", "/dashboard"):
            try:
                with open(DASHBOARD_HTML, "rb") as f:
                    body = f.read()
                self._send(200, body, "text/html; charset=utf-8")
            except OSError:
                self._send(500, b"dashboard.html missing", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *args):
        pass


def _reset_counters():
    global _udp_tokens
    with _lock:
        for grp in ("http", "tcp", "udp"):
            for k, v in M[grp].items():
                if isinstance(v, (int, float)):
                    M[grp][k] = type(v)(0)
        for k in M["history"]:
            M["history"][k] = []
        for k in _prev:
            _prev[k] = 0  # re-baseline so the next sample isn't a negative delta
        M["started_at"] = time.time()
        _udp_tokens = UDP_CAPACITY


# --- Background sampler: per-second rates, history, token refill ------------
def sampler():
    global _udp_tokens
    while True:
        time.sleep(1.0)
        with _lock:
            # max(0, …) guards the one interval spanning a /reset.
            http_rps = max(0, M["http"]["total"] - _prev["http_total"])
            reject_rps = max(0, M["http"]["rejected"] - _prev["http_rejected"])
            udp_pps = max(0, M["udp"]["packets"] - _prev["udp_packets"])
            udp_drop_rps = max(0, M["udp"]["dropped"] - _prev["udp_dropped"])
            cps = max(0, M["tcp"]["total"] - _prev["tcp_total"])

            M["http"]["rps"] = float(http_rps)
            M["http"]["reject_rps"] = float(reject_rps)
            M["udp"]["pps"] = float(udp_pps)
            M["udp"]["drop_rps"] = float(udp_drop_rps)
            M["tcp"]["cps"] = float(cps)

            for key, val in (("http_rps", http_rps), ("http_reject_rps", reject_rps),
                             ("udp_pps", udp_pps), ("udp_drop_rps", udp_drop_rps)):
                buf = M["history"][key]
                buf.append(val)
                if len(buf) > HISTORY_LEN:
                    del buf[0:len(buf) - HISTORY_LEN]

            _prev.update({"http_total": M["http"]["total"], "http_rejected": M["http"]["rejected"],
                          "udp_packets": M["udp"]["packets"], "udp_dropped": M["udp"]["dropped"],
                          "tcp_total": M["tcp"]["total"]})
            _udp_tokens = UDP_CAPACITY  # refill the per-second budget


def main():
    print("=" * 60)
    print(" DDoS Lab - Victim Service")
    print(f"  HTTP (L7) : :{HTTP_PORT}  workers={HTTP_WORKERS} work={HTTP_WORK_MS}ms")
    print(f"  TCP  (L4) : :{TCP_PORT}  max_conn={TCP_MAX_CONN}")
    print(f"  UDP  (L4) : :{UDP_PORT}  capacity={UDP_CAPACITY} pps")
    print(f"  Admin     : :{ADMIN_PORT}  (dashboard + /metrics)")
    print("=" * 60, flush=True)

    threading.Thread(target=sampler, daemon=True).start()
    threading.Thread(target=udp_server, daemon=True).start()

    tcp_srv = ThreadingTCPServer(("0.0.0.0", TCP_PORT), TCPConnHandler)
    threading.Thread(target=tcp_srv.serve_forever, daemon=True).start()

    svc = ThreadingHTTPServer(("0.0.0.0", HTTP_PORT), ServiceHandler)
    threading.Thread(target=svc.serve_forever, daemon=True).start()

    admin = ThreadingHTTPServer(("0.0.0.0", ADMIN_PORT), AdminHandler)
    try:
        admin.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")


if __name__ == "__main__":
    main()
