from __future__ import annotations

import contextlib
import os
from typing import Any, Dict, List, Optional, Union

import yaml

with contextlib.suppress(ImportError):
    from dotenv import dotenv_values, load_dotenv

    load_dotenv()
    dotenv_values(".env")

with open("config.yml", encoding="utf-8", errors="ignore") as f:
    data: Dict[str, Any] = yaml.safe_load(f.read())

VERSION = "v5.0.0"

HEROKU: bool = True


def parse_env_var(key: Optional[str], default: Any = None) -> Union[str, int, float, bool, List[Any]]:
    """
    Parse an environment variable into a Python type.
    """
    value = os.environ.get(str(key), default)
    if value is None:
        raise ValueError(f"{key} is not set")
    if "|" in value:
        return [parse_env_var(None, key) for key in value.split("|")]
    if value.isdigit():
        return int(value)
    if value.replace(".", "", 1).isdigit():
        return float(value)
    return value.lower() == "true" if value.lower() in ("true", "false") else value


OWNER_IDS: List[int] = parse_env_var("OWNER_IDS")  # type: ignore
DEFAULT_PREFIX: str = parse_env_var("BOT_PREFIX", "$")  # type: ignore
CASE_INSENSITIVE: bool = parse_env_var("COMMAND_CASE_INSENSITIVE", True)  # type: ignore
STRIP_AFTER_PREFIX: bool = parse_env_var("STRIP_AFTER_PREFIX")  # type: ignore
SUPER_USER: str = parse_env_var("OWNER_ID")  # type: ignore
MASTER_OWNER: str = SUPER_USER
EXTENSIONS: List[str] = data["all_extensions"]
UNLOAD_EXTENSIONS: List[str] = data.get("unload_extensions", [])
DEV_LOGO: str = data["dev_logo"]
TOKEN: str = parse_env_var("TOKEN")  # type: ignore
DATABASE_KEY: str = parse_env_var("DATABASE_KEY")  # type: ignore
OPEN_ROBOT_API: str = parse_env_var("OPEN_ROBOT_API")  # type: ignore
AUTHOR_NAME: str = parse_env_var("OWNER_NAME")  # type: ignore
AUTHOR_DISCRIMINATOR: int = parse_env_var("OWNER_DISCRIMINATOR", 9230)  # type: ignore
GITHUB: str = f"https://github.com/{parse_env_var('GITHUB_ID')}/{parse_env_var('GITHUB_PROJECT_NAME')}"
SUPPORT_SERVER: str = f"https://discord.gg/{parse_env_var('SUPPORT_SERVER')}R"
WEBHOOK_JOIN_LEAVE_CHANNEL_ID: int = parse_env_var("WEBHOOK_JOIN_LEAVE_ID")  # type: ignore
SUPPORT_SERVER_ID = parse_env_var("SUPPORT_SERVER_ID", 741614680652644382)
MEME_PASS = parse_env_var("MEME_PASS")
PRIVACY_POLICY: str = parse_env_var("PRIVACY_POLICY")  # type: ignore

LRU_CACHE = 64 if HEROKU else 256
TO_LOAD_IPC: bool = "cogs.ipc" not in UNLOAD_EXTENSIONS
# TO_LOAD_IPC: bool = True

WEBHOOK_JOIN_LEAVE_LOGS: str = parse_env_var("WEBHOOK_JOIN_LEAVE_LOGS")  # type: ignore
WEBHOOK_ERROR_LOGS: str = parse_env_var("WEBHOOK_ERROR_LOGS")  # type: ignore
WEBHOOK_STARTUP_LOGS: str = parse_env_var("WEBHOOK_STARTUP_LOGS")  # type: ignore
WEBHOOK_VOTE_LOGS: str = parse_env_var("WEBHOOK_VOTE_LOGS")  # type: ignore
DATABASE_URI: str = parse_env_var("DATABASE_URI")  # type: ignore
CHANGE_LOG_CHANNEL_ID: int = parse_env_var("CHANGE_LOG_CHANNEL_ID")  # type: ignore
JEYY_API_TOKEN: str = parse_env_var("JEYY_API")  # type: ignore
