FROM python:3.12-slim
WORKDIR /app
COPY generator.py ./
# Stdlib only — no dependencies to install.
ENTRYPOINT ["python", "-u", "generator.py"]
