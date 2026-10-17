# Amader Home Assistant Server

FastAPI backend for the custom doorbell platform.

## Local Python development

```sh
uv sync
uv run pytest
DATABASE_URL=postgresql://user:password@localhost/database uv run uvicorn amader_home_assistant.main:app --reload
```

## Docker deployment

Run from `amader-home-assistant/`:

```sh
cp .env.example .env
# Replace POSTGRES_PASSWORD before starting.
docker compose up --build -d
```

Endpoints currently available:

- `GET /health/live` — confirms the API process is running.
- `GET /health/ready` — confirms the configured PostgreSQL database is reachable.

The API intentionally binds to `127.0.0.1:8787` by default. Publish it through the server's HTTPS reverse proxy rather than exposing the container directly.
