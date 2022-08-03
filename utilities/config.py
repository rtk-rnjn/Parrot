from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

import yaml

try:
    from dotenv import dotenv_values, load_dotenv  # type: ignore

    load_dotenv()
    dotenv_values(".env")
except ImportError:
    pass

with open("config.yml") as f:
    data: Dict[str, Any] = yaml.safe_load(f.read())

VERSION = "v4.9.5-beta"


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


OWNER_IDS: list = parse_env_var("OWNER_IDS")
DEFAULT_PREFIX: str = parse_env_var("BOT_PREFIX", "$")
CASE_INSENSITIVE: bool = parse_env_var("COMMAND_CASE_INSENSITIVE", True)
STRIP_AFTER_PREFIX: bool = parse_env_var("STRIP_AFTER_PREFIX")
SUPER_USER: str = parse_env_var("OWNER_ID")
MASTER_OWNER: str = SUPER_USER
EXTENSIONS: str = data["extensions"]
DEV_LOGO: str = data["dev_logo"]
TOKEN: str = parse_env_var("TOKEN")
DATABASE_KEY: str = parse_env_var("DATABASE_KEY")
OPEN_ROBOT_API: str = parse_env_var("OPEN_ROBOT_API")
my_secret = DATABASE_KEY
AUTHOR_NAME: str = parse_env_var("OWNER_NAME")
AUTHOR_DISCRIMINATOR: int = parse_env_var("OWNER_DISCRIMINATOR", 9230)
GITHUB: str = f"https://github.com/{parse_env_var('GITHUB_ID')}/{parse_env_var('GITHUB_PROJECT_NAME')}"
SUPPORT_SERVER: str = f"https://discord.gg/{parse_env_var('SUPPORT_SERVER')}"
WEBHOOK_JOIN_LEAVE_CHANNEL_ID: int = parse_env_var("WEBHOOK_JOIN_LEAVE_ID")
SUPPORT_SERVER_ID = parse_env_var("SUPPORT_SERVER_ID", 741614680652644382)
MEME_PASS = parse_env_var("MEME_PASS")
PRIVACY_POLICY: str = parse_env_var("PRIVACY_POLICY")
