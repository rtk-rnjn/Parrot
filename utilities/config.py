from __future__ import annotations

import os
from typing import Any, Dict, Union

import yaml

try:
    from dotenv import dotenv_values, load_dotenv  # type: ignore

    load_dotenv()
    dotenv_values(".env")
except ImportError:
    pass

with open("config.yml") as f:
    data: Dict[str, Any] = yaml.safe_load(f.read())

VERSION = "v4.8.0-beta"


def parse_env_var(key: str, default: Any = None) -> Union[str, int, float, bool]:
    """
    Parse an environment variable into a Python type.
    """
    value = os.environ.get(key, default)
    if value is None:
        raise ValueError(f"{key} is not set")
    if value.isdigit():
        return int(value)
    if value.replace(".", "", 1).isdigit():
        return float(value)
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


OWNER_IDS: list = data["owner_ids"]
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

AUTHOR_NAME: str = data["author_name"]
AUTHOR_DISCRIMINATOR: int = parse_env_var("OWNER_DISCRIMINATOR", 9230)

GITHUB: str = f"https://github.com/{parse_env_var('GITHUB_ID', 'rtk-rnjn')}/{parse_env_var('GITHUB_REPO', 'Parrot')}"
SUPPORT_SERVER: str = f"https://discord.gg/{parse_env_var('SUPPORT_SERVER')}"
WEBHOOK_JOIN_LEAVE_CHANNEL_ID: int = parse_env_var("WEBHOOK_JOIN_LEAVE_ID")
SUPPORT_SERVER_ID = parse_env_var("SUPPORT_SERVER_ID")

MEME_PASS = parse_env_var("MEME_PASS")
# this is not the real pass, just to tell the website from where the API call is comming from.
# yes you can use. but i suggest you to use your own.

PRIVACY_POLICY: str = data["privacy_policy"]
