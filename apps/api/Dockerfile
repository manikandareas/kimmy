FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /usr/local/bin/uv
WORKDIR /app
COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev
RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "kimmy.main:app", "--host", "0.0.0.0", "--port", "8000"]
