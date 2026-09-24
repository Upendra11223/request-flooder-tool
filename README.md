# 🛡️ DDoS Lab — a contained lab for *learning* DoS/DDoS and its defenses

A hands-on, self-contained lab for understanding how Layer 4 and Layer 7
denial-of-service attacks overwhelm a service — and, just as importantly, how
defenses absorb them. You run a flood against a tiny **victim service that lives
only inside the lab**, watch it degrade on a live dashboard, then run the same
flood through a **defense layer** and watch it stay healthy.

> **This lab cannot attack anyone.** The traffic generator runs on an internal
> Docker network with no route to the internet, and it *refuses to run against
> any public IP address* (see [Safety by design](#-safety-by-design)). It is a
> teaching instrument, not an attack tool.

---

## 🎯 What you'll actually learn

Running a flooder at a live website teaches you nothing except "packets go out"
— and it's a crime. Real understanding comes from watching **why** a service
falls over and **how** it's protected. This lab shows you:

- The difference between **Layer 7** (application, e.g. HTTP) and **Layer 4**
  (transport, e.g. TCP/UDP) resource exhaustion.
- **Worker-pool exhaustion**, **connection-table exhaustion**, and **packet
  processing budgets** — the three ways the victim runs out of resources.
- How a **reverse-proxy rate limiter** (nginx) sheds a single-source flood, and
  why a *distributed* attack is harder to stop.
- How to read the signals defenders actually watch: request rate, rejection
  rate, in-flight concurrency, connection counts, drop rate.

Deep-dive theory lives in **[`docs/concepts.md`](docs/concepts.md)**.

---

## 🧱 Architecture

```
                 mgmtnet (bridge, to your browser)
                        │  :9090 dashboard + /metrics
                        ▼
   ┌───────────┐   ┌─────────────────────────────┐
   │ generator │──▶│           victim            │
   │  (L4/L7)  │   │  :8080 HTTP  (worker pool)  │
   └───────────┘   │  :8082 TCP   (conn table)   │
        │          │  :8081 UDP   (proc budget)  │
        │ or       │  :9090 admin (always up)    │
        ▼          └─────────────────────────────┘
   ┌───────────┐            ▲
   │  defense  │────────────┘  proxy_pass (rate + conn limits)
   │  (nginx)  │
   └───────────┘
        └──────── attacknet (internal: true — NO internet) ────────┘
```

- **victim** — a small instrumented target. Limits are intentionally tiny so it
  saturates under safe, modest load. Serves a live dashboard on `:9090`.
- **defense** — nginx reverse proxy with `limit_req` / `limit_conn`.
- **generator** — on-demand load generator, internal network only, public-IP
  refusal built in.

---

## 🚀 Quick start

Requires **Docker** and **Docker Compose v2**.

```bash
make up            # build + start victim and defense
# open the dashboard:
make dashboard     # -> http://localhost:9090
```

Then, in another terminal, run a scenario and watch the dashboard react:

```bash
make flood-http            # L7 flood, hits the victim DIRECTLY  -> goes RED
make reset                 # zero the counters between runs
make flood-http-defended   # same flood THROUGH nginx           -> stays GREEN
```

More scenarios:

```bash
make flood-tcp     # L4 TCP connection-table exhaustion
make flood-udp     # L4 UDP packet flood (watch the drop rate climb)
make logs          # tail victim + defense logs
make down          # stop everything   (make clean = also remove images/volumes)
```

### The key experiment

1. `make up`, open the dashboard.
2. `make flood-http` → the HTTP card fills up, latency and **503 rejections**
   climb, status goes **OVERWHELMED**.
3. `make reset`, then `make flood-http-defended` → nginx sheds the excess at the
   edge, the victim's worker pool barely moves, status stays **HEALTHY**.
4. Read `docs/concepts.md` to understand *why*, and why a distributed attack
   would defeat the simple per-IP limit.

---

## 🔒 Safety by design

This lab is built so it can only ever hit itself:

1. **No internet route.** The `attacknet` Docker network is declared
   `internal: true`. Containers on it (generator, victim, defense) have no
   gateway to the outside world. Packets cannot leave the host.
2. **Public-IP refusal.** `generator.py` resolves its target and **exits** if
   any resolved address is public. It only accepts private (RFC1918), loopback,
   or link-local targets. Lifting the script out of the lab to point it at a
   real site fails by design.
3. **No amplification payloads.** The generator sends generic filler bytes. It
   deliberately does *not* craft DNS/NTP/SNMP/SSDP reflection payloads — those
   have no learning value and exist only to harm third parties.
4. **On-demand generator.** The generator never auto-starts; you invoke each run
   explicitly.

### Legal note

Running real DoS/DDoS traffic against systems you don't own is a crime in
essentially every jurisdiction (e.g. US CFAA, UK Computer Misuse Act, Nepal's
Electronic Transactions Act). Practice offense only in environments built for it
— this lab, your own isolated VMs, or platforms like HackTheBox / TryHackMe.

---

## 📁 Layout

```
docker-compose.yml     # orchestration + the internal/no-egress network
Makefile               # make up / flood-* / reset / down
victim/                # instrumented target + live dashboard (stdlib Python)
generator/             # load generator with public-IP refusal (stdlib Python)
defense/               # nginx reverse proxy with rate + connection limits
docs/concepts.md       # the theory: L4 vs L7, exhaustion modes, mitigations
```

## 🧩 Extend it

Good next exercises (see `docs/concepts.md` for pointers): add a Slowloris-style
slow-header scenario; add `limit_conn` visualisation from nginx `stub_status`;
simulate a *distributed* source with multiple generator replicas to show why
per-IP limits alone aren't enough; add a SYN-flood discussion with `tc`/`iptables`.
