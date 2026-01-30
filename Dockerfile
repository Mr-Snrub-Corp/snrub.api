# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev python3-dev && rm -rf /var/lib/apt/lists/*

WORKDIR /fastapi

FROM base AS dev-build
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=bind,source=uv.lock,target=uv.lock \
  --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
  uv sync --frozen --no-install-project

FROM dev-build AS dev
ADD . /fastapi
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen
# Install test dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
  uv add pytest 
ENV PATH="/fastapi/.venv/bin:$PATH"
EXPOSE 8000

# Make the startup script executable
RUN chmod +x /fastapi/scripts/start-dev.sh

# Development server with migrations and hot reload
ENTRYPOINT ["/fastapi/scripts/start-dev.sh"]
