# DoS / DDoS concepts — the theory behind the lab

This document explains what the lab demonstrates. Read it alongside the live
dashboard; the metrics map directly onto the ideas below.

---

## 1. DoS vs. DDoS

- **DoS** (Denial of Service): a *single* source exhausts a target's resources
  so legitimate users can't be served.
- **DDoS** (Distributed DoS): *many* sources (a botnet, or reflectors) do the
  same thing at once. Distribution is what makes it hard to stop — you can't
  just block one IP.

This lab is single-source (one generator). That's deliberate: it lets a simple
per-IP rate limit *win*, which then makes it obvious **why distribution is the
whole point** of real DDoS. See §6.

---

## 2. The OSI layers attackers target

| Layer | Name | Example attack | What runs out | Lab port |
|------:|------|----------------|---------------|----------|
| 7 | Application | HTTP request flood, Slowloris | worker/thread pool, CPU, DB connections | `victim:8080` |
| 4 | Transport | TCP SYN flood, connection flood | connection table, socket memory | `victim:8082` |
| 4/3 | Transport/Net | UDP flood, ICMP flood | packet processing budget, bandwidth | `victim:8081` |

**Layer 7** attacks are "expensive per request" — each request looks legitimate
but forces the server to do real work (render a page, hit a database). You need
comparatively few of them.

**Layer 4/3** attacks are "cheap per packet, huge in volume" — they don't care
about application logic; they drown the network stack or saturate the link.

---

## 3. The three exhaustion modes in the lab

### 3a. Worker-pool exhaustion (L7 / `:8080`)
The victim can serve only `HTTP_WORKERS` (default 50) requests at once, each
taking `HTTP_WORK_MS`. When all workers are busy, new requests are **rejected
with 503** rather than queued forever (this is "load shedding").

On the dashboard: the **worker pool bar** fills to 100%, **Rejected/sec** climbs,
status → OVERWHELMED. Real analogue: PHP-FPM/Gunicorn/Puma worker saturation,
or a thread-per-request server running out of threads.

### 3b. Connection-table exhaustion (L4 / `:8082`)
Every open TCP connection consumes a slot and kernel memory. The victim caps
concurrent connections at `TCP_MAX_CONN` (default 200) and **refuses** beyond
that. The generator's `tcp-flood` opens connections and *holds them* (`--hold`),
occupying slots — the same principle as a SYN flood (half-open connections) or
Slowloris (slow, long-lived requests).

On the dashboard: **Active** rises to the cap, **Refused** climbs.

### 3c. Packet processing budget (L4 / `:8081`)
UDP is connectionless — the victim receives every datagram, but can only
"process" `UDP_CAPACITY` packets/sec (a token bucket). Excess is **dropped**,
exactly as an overwhelmed stack or rate-limited NIC would drop.

On the dashboard: **Packets/sec** exceeds the dashed capacity line on the
sparkline and **Dropped/sec** becomes non-zero. Real UDP floods also aim to
saturate raw *bandwidth*, which no application can fix by itself.

---

## 4. Amplification / reflection (explained, deliberately NOT built)

The nastiest volumetric DDoS attacks are **reflection + amplification**:
1. The attacker sends a small request to a public server (DNS, NTP, SNMP, SSDP,
   memcached…) but **spoofs the source IP** to be the victim.
2. The server sends a much larger reply **to the victim**.
3. A tiny request becomes a huge response — amplification factors range from
   ~x50 (DNS) to x50,000+ (memcached).

**This lab intentionally contains no amplification payloads.** Crafting
DNS/NTP/SNMP/SSDP payloads has zero defensive learning value — you don't need to
forge them to understand the concept — and their only real-world use is
attacking third parties. What matters for *defense*:
- **Don't run open resolvers/reflectors.** Restrict who your UDP services answer.
- **BCP 38 / source-address validation** at the network edge stops spoofing,
  which is what makes reflection possible in the first place.
- **Upstream scrubbing / anycast** absorbs volume you can't handle yourself.

---

## 5. Defenses (and what the lab shows)

The `defense` service is nginx as a reverse proxy with two limits:

- `limit_req_zone … rate=10r/s` + `burst=20` — a **token-bucket rate limit** per
  client IP. Excess requests get 503 *at the edge*, before reaching the victim.
- `limit_conn 10` — caps **concurrent connections** per client IP.

Run `make flood-http-defended` and watch the victim's worker pool barely move:
nginx sheds the flood so the origin stays healthy. That's the core defensive
pattern — **push rejection to a cheap, scalable edge**.

Other real-world layers (discussed, not all built here):
- **CDN / WAF** in front of origin (Cloudflare, Akamai, AWS Shield).
- **SYN cookies** (`net.ipv4.tcp_syncookies`) for SYN floods — the kernel avoids
  allocating state for half-open connections.
- **Connection & request limits** at the load balancer.
- **Anycast + scrubbing centers** to spread and clean volumetric traffic.
- **Autoscaling** to add capacity (helps against small floods, loses the cost
  race against large ones).
- **Challenge/JS/CAPTCHA** to separate bots from humans at L7.

---

## 6. Why the lab's defense would lose against real DDoS

The per-IP `limit_req` works beautifully here because there is exactly **one**
source. A real DDoS spreads across thousands of IPs, each staying *under* the
per-IP threshold, so:
- Per-IP limits don't trigger — each source looks reasonable.
- The **aggregate** still buries the origin.

That's why production defense combines per-IP limits with **behavioral/anomaly
detection**, **reputation feeds**, **global rate limits**, and **upstream
scrubbing**. Try it yourself: run several generator replicas
(`docker compose run` in parallel, or scale the service) and watch a single
per-IP limit fail to hold.

---

## 7. Metrics glossary (what the dashboard fields mean)

| Field | Meaning | Defender's read |
|-------|---------|-----------------|
| Requests/sec | offered load reaching the service | baseline vs. spike |
| Rejected/sec (503) | load being shed | high = at capacity |
| Worker pool (in-flight / max) | concurrency saturation | 100% = exhausted |
| Last latency | time to serve one request | rising = pressure |
| TCP Active / max | connection-table usage | at cap = conn flood |
| TCP Refused | connections turned away | climbing = exhaustion |
| UDP pps vs capacity | offered vs. processable | over line = flood |
| UDP Dropped/sec | packets beyond budget | non-zero = saturation |

---

## 8. Further practice (legal)

- **HackTheBox / TryHackMe** — guided offensive labs in sanctioned environments.
- **Your own isolated VMs** — a home lab you fully control.
- **Load-testing tools for your own services** — `k6`, `Locust`, `wrk`, `hey`
  (capacity planning, not attacking).
- **Read the mitigations** — Cloudflare's DDoS learning center, RFC 4987 (TCP
  SYN flooding), BCP 38 (source address validation).

Never send DoS/DDoS traffic at systems you don't own or lack written
authorization to test.
