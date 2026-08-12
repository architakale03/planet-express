FROM python:3.12-slim

# UV_PROJECT_ENVIRONMENT=/usr/local is load-bearing: Compose bind-mounts ./api
# over /app for live reload, which would shadow a virtualenv at /app/.venv and
# leave the container with no dependencies. Installing into the system prefix
# puts them outside the mount, and puts uvicorn/alembic straight on PATH.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

COPY --from=ghcr.io/astral-sh/uv:0.12.3 /uv /bin/uv

WORKDIR /app

# Copied first so the dependency layer caches across source edits. --frozen
# fails the build if uv.lock is stale rather than silently resolving something
# different from what runs locally.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --all-groups

COPY . .

# Run as non-root. The bind mount in compose is owned by the host user, so keep
# the container user's writes confined to /app rather than system paths.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
