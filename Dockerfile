# =============================================================================
# Luz Informer Bot - Multi-stage build
# =============================================================================
# Targets:
#   default (runtime): imagen final para ejecutar el bot
#   test: imagen con deps de desarrollo + tests (para CI: pytest, ruff)
# =============================================================================

# -----------------------------------------------------------------------------
# Stage: builder - dependencias de producción
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /app
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage: test - para workflows de tests y linters (CI)
# -----------------------------------------------------------------------------
FROM builder AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY config/ ./config/
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY pytest.ini .

# Por defecto pytest; en CI se puede override para ruff, etc.
CMD ["python", "-m", "pytest", "tests/", "-v"]

# -----------------------------------------------------------------------------
# Stage: runtime - imagen mínima para ejecutar el bot
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY config/ ./config/
COPY src/ ./src/
COPY scripts/ ./scripts/

RUN mkdir -p /data

CMD ["python", "-m", "src.main"]
