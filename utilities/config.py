from __future__ import annotations

from typing import Any, Dict
import yaml
import os
from dotenv import load_dotenv, dotenv_values

load_dotenv()
dotenv_values(".env")

with open("config.yml") as f:
    data: Dict[str, Any] = yaml.load(f.read())

VERSION = "v4.7.4-beta"

OWNER_IDS: list = data["owner_ids"]
DEFAULT_PREFIX: str = data["prefix"]
CASE_INSENSITIVE: bool = data["case_insensitive"]
STRIP_AFTER_PREFIX: bool = data["strip_after_prefix"]

SUPER_USER: str = data["super_user"]
MASTER_OWNER: str = SUPER_USER

EXTENSIONS: str = data["extensions"]
DEV_LOGO: str = data["dev_logo"]

TOKEN: str = os.environ["TOKEN"]
DATABASE_KEY: str = os.environ["DATABASE_KEY"]
OPEN_ROBOT_API: str = os.environ["OPEN_ROBOT_API"]
my_secret = DATABASE_KEY

AUTHOR_NAME: str = data["author_name"]
AUTHOR_DISCRIMINATOR: int = data["discriminator"]

GITHUB: str = data["github"]
SUPPORT_SERVER: str = data["support_server"]
JOIN_LEAVE_CHANNEL_ID: int = data["join_leave_channel_id"]
SUPPORT_SERVER_ID = 741614680652644382

MEME_PASS = "***qwerty123"
# this is not the real pass, just to tell the website from where the API call is comming from.
# yes you can use. but i suggest you to use your own.

PRIVACY_POLICY: str = data["privacy_policy"]
