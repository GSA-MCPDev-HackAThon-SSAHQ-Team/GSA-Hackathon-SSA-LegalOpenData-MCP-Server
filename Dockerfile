# syntax=docker/dockerfile:1
# Container image for remote (streamable-HTTP) deployment.
#
# Used by:
#   - IBM Code Engine (deploy/ibm/)
#   - cloud.gov (docker image path) and any other container host
#
# The server serves MCP over streamable-HTTP at :8080/mcp with a health check
# at :8080/health. app.py auto-selects HTTP because PORT is set below.

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV PORT=8080
ENV SSA_ALJ_DB_PATH=/app/data/ssa_alj.sqlite

WORKDIR /app

# Install uv (fast, reproducible installs).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
# The read-only SQLite database built by data/scripts/load_ssa_alj.py (see README).
COPY data/ssa_alj.sqlite ./data/ssa_alj.sqlite
RUN uv pip install --system --no-cache .

EXPOSE 8080

# PORT=8080 (set above) makes app.py run HTTP on that port automatically.
CMD ["python", "-m", "ssa_alj_mcp.app"]
