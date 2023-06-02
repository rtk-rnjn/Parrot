from __future__ import annotations

import contextlib
import os
from typing import Any, Dict, List, Optional, Union

import yaml

with contextlib.suppress(ImportError):
    from dotenv import dotenv_values, load_dotenv  # type: ignore

    load_dotenv()
    dotenv_values(".env")

with open("config.yml", encoding="utf-8", errors="ignore") as f:
    data: Dict[str, Any] = yaml.safe_load(f.read())

VERSION = "v5.0-alpha.1"

HEROKU: bool = True


def parse_env_var(
    key: Optional[str], default: Any = None
) -> Union[str, int, float, bool, List[Any]]:
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


OWNER_IDS: List[int] = parse_env_var("OWNER_IDS")
DEFAULT_PREFIX: str = parse_env_var("BOT_PREFIX", "$")
CASE_INSENSITIVE: bool = parse_env_var("COMMAND_CASE_INSENSITIVE", True)
STRIP_AFTER_PREFIX: bool = parse_env_var("STRIP_AFTER_PREFIX")
SUPER_USER: str = parse_env_var("OWNER_ID")
MASTER_OWNER: str = SUPER_USER
EXTENSIONS: List[str] = data["all_extensions"]
UNLOAD_EXTENSIONS: List[str] = data.get("unload_extensions", [])
DEV_LOGO: str = data["dev_logo"]
TOKEN: str = parse_env_var("TOKEN")
DATABASE_KEY: str = parse_env_var("DATABASE_KEY")
OPEN_ROBOT_API: str = parse_env_var("OPEN_ROBOT_API")
AUTHOR_NAME: str = parse_env_var("OWNER_NAME")
AUTHOR_DISCRIMINATOR: int = parse_env_var("OWNER_DISCRIMINATOR", 9230)
GITHUB: str = f"https://github.com/{parse_env_var('GITHUB_ID')}/{parse_env_var('GITHUB_PROJECT_NAME')}"
SUPPORT_SERVER: str = f"https://discord.gg/{parse_env_var('SUPPORT_SERVER')}R"
WEBHOOK_JOIN_LEAVE_CHANNEL_ID: int = parse_env_var("WEBHOOK_JOIN_LEAVE_ID")
SUPPORT_SERVER_ID = parse_env_var("SUPPORT_SERVER_ID", 741614680652644382)
MEME_PASS = parse_env_var("MEME_PASS")
PRIVACY_POLICY: str = parse_env_var("PRIVACY_POLICY")

if HEROKU:
    UNLOAD_EXTENSIONS.append("cogs.ipc")
    LRU_CACHE = 128
else:
    LRU_CACHE = 256

TO_LOAD_IPC: bool = "cogs.ipc" not in UNLOAD_EXTENSIONS

WEBHOOK_JOIN_LEAVE_LOGS: str = parse_env_var("WEBHOOK_JOIN_LEAVE_LOGS")
WEBHOOK_ERROR_LOGS: str = parse_env_var("WEBHOOK_ERROR_LOGS")
WEBHOOK_STARTUP_LOGS: str = parse_env_var("WEBHOOK_STARTUP_LOGS")
WEBHOOK_VOTE_LOGS: str = parse_env_var("WEBHOOK_VOTE_LOGS")
DATABASE_URI: str = parse_env_var("DATABASE_URI")
CHANGE_LOG_CHANNEL_ID: int = parse_env_var("CHANGE_LOG_CHANNEL_ID")