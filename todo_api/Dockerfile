FROM python:3.14-slim

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Activate the project virtual environment by placing its binary directory at the front of the path.
# https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/.venv/bin:$PATH"

# Compile bytecode
# https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
ENV UV_COMPILE_BYTECODE=1

# uv Cache
# https://docs.astral.sh/uv/guides/integration/docker/#caching
ENV UV_LINK_MODE=copy

WORKDIR /app

# Install UV.
# https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
# https://hub.docker.com/r/astral/uv
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/

# Install dependencies.
# https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=todo_api/uv.lock,target=/app/uv.lock \
    --mount=type=bind,source=todo_api/pyproject.toml,target=/app/pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy the project into the image.
COPY shared ./shared
COPY todo_api ./todo_api

WORKDIR /app/todo_api

ENV PYTHONPATH="/app:${PYTHONPATH}"

# Sync the project
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
