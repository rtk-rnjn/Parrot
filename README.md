# Parrot

Parrot is a modular Discord bot written for Python 3.14 and `discord.py`. Features are organized as independent cogs, with shared bot, database, and utility code under `core/`.

## Requirements

- Python 3.14+
- A configured Discord bot application and token
- MongoDB and Redis configuration for persistence and caching
- Optional Lavalink configuration for music features

Install the pinned dependencies in a virtual environment:

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Configure environment variables in `.env` as required by the bot and database modules. Do not commit secrets.

## Running locally

```bash
.venv/bin/python main.py
```

Supporting services can be started with:

```bash
docker compose up -d
```

## Contributing

Keep feature-specific behavior inside its cog, use shared abstractions from `core/` where appropriate, and run Ruff, Pyright, and Flake8 before opening a pull request.

