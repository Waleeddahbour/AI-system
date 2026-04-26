FROM python:3.12-alpine

# Install uv from the official image (no pip needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Optimise uv for container use
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies (cached layer — only re-runs when lock file changes)
COPY pyproject.toml uv.lock README.md ./
COPY app ./app
RUN uv sync --frozen --no-dev

# Copy source
COPY . .

# Make venv binaries available on PATH so uvicorn can be called directly
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
