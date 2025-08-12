# Use official Python image as base
FROM python:3.12-slim

WORKDIR /app

# install system and Rust build dependencies
RUN apt-get update && apt-get install -y git curl build-essential pkg-config libssl-dev

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:/app/.venv/bin:${PATH}"

# dependency files first
COPY pyproject.toml uv.lock alembic.ini ./

# copy source packages
COPY pylon_common ./pylon_common
COPY pylon_service ./pylon_service

# install uv and dependencies
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/
RUN /bin/uv sync --no-install-project

# database mounting
VOLUME ["/app/db"]

EXPOSE 8000
CMD [".venv/bin/python", "-m", "uvicorn", "pylon_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

