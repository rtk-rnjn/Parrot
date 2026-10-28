from __future__ import annotations

import os
import secrets

from dotenv import load_dotenv

load_dotenv()


DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/auth/callback")
REDIS_URI = os.getenv("REDIS_URI", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

IPC_REQUEST_CHANNEL = "bot:ipc:request"
TELEMETRY_KEY = "bot:telemetry:status"

MANAGE_GUILD, ADMINISTRATOR = 0x20, 0x8
ALLOWED_OPS = {"PING", "GET_MUTUAL_GUILDS", "GET_GUILD_DETAIL"}
