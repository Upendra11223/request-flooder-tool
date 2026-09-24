# DDoS Lab - convenience targets. Requires Docker + Docker Compose v2.
COMPOSE ?= docker compose
GEN := $(COMPOSE) run --rm generator

.PHONY: help up down restart logs dashboard reset build \
        flood-http flood-http-defended flood-tcp flood-udp clean

help:
	@echo "DDoS Lab"
	@echo "  make up                    Build + start victim and defense"
	@echo "  make dashboard             Print the dashboard URL"
	@echo "  make flood-http            L7 flood -> victim directly (undefended)"
	@echo "  make flood-http-defended   L7 flood -> defense (nginx rate limiting)"
	@echo "  make flood-tcp             L4 TCP connection flood -> victim"
	@echo "  make flood-udp             L4 UDP flood -> victim"
	@echo "  make reset                 Zero the victim's counters"
	@echo "  make logs                  Tail victim + defense logs"
	@echo "  make down / make clean     Stop / stop+remove images+volumes"

up build:
	$(COMPOSE) up -d --build victim defense
	@echo ""
	@echo ">> Dashboard: http://localhost:9090"

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f victim defense

dashboard:
	@echo "Open http://localhost:9090 in your browser."

reset:
	@curl -s http://localhost:9090/reset >/dev/null && echo "counters reset" || echo "victim not reachable"

# --- Scenarios -------------------------------------------------------------
flood-http:
	$(GEN) http-flood --target victim  --port 8080 --duration 25 --concurrency 150

flood-http-defended:
	$(GEN) http-flood --target defense --port 80   --duration 25 --concurrency 150

flood-tcp:
	$(GEN) tcp-flood  --target victim  --port 8082 --duration 25 --concurrency 250 --hold 4

flood-udp:
	$(GEN) udp-flood  --target victim  --port 8081 --duration 25 --concurrency 60  --packet-size 512

clean:
	$(COMPOSE) down -v --rmi local
