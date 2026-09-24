FROM python:3.12-slim
WORKDIR /app
COPY victim.py dashboard.html ./
# Stdlib only — no dependencies to install.
EXPOSE 8080 8081/udp 8082 9090
CMD ["python", "-u", "victim.py"]
