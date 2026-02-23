# app-2.0 (Docker)

This repository runs a Telegram AI agent backed by Qdrant (vector DB).
The Docker setup below starts two services with `docker-compose`:

- `qdrant` — Qdrant vector database (persistent volume mounted)
- `app` — Python application (the Telegram bot & agents)

Requirements
- Docker & Docker Compose installed
- Create a `.env` file in the project root with your credentials (see sample below)

Important: do NOT hard-code API keys in code. Put them in `.env` (kept out of the image by `.dockerignore`).

Example `.env` (create in project root):

TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TAVILY_API_KEY=your_tavily_api_key_here
QDRANT_API_KEY=
QDRANT_URL=http://qdrant:6333

Note: `QDRANT_URL` must point to the Qdrant service by name when running with docker-compose: `http://qdrant:6333`.

How to run

1. Build and start services:

```bash
docker-compose up --build -d
```

2. Check logs:

```bash
docker-compose logs -f app
```

3. Stop services:

```bash
docker-compose down
```

Data persistence

The Qdrant data is stored in the Docker volume `qdrant_storage` and is persisted across container restarts.

Notes & recommendations

- The `app` service reads configuration from `.env` via `env_file` and an explicit `QDRANT_URL` override.
- For production, run the app behind a process manager or container orchestrator. You may also build a smaller runtime image and apply best-practice hardening.
- If Qdrant is hosted remotely, set `QDRANT_URL` in `.env` to the reachable URL and set `QDRANT_API_KEY` if required.

If you want, I can also:
- Add a small `Makefile` with common commands
- Add a `docker-compose.override.yml` for local development with code bind-mounts
- Pin dependency versions in `requirements.txt`
