import json
import os

with open("config.json") as f:
    data = json.load(f)

VERSION = "v4.1.0-stable"

OWNER_IDS = data["owner_ids"]
DEFAULT_PREFIX = data["prefix"]
CASE_INSENSITIVE = data["case_insensitive"]
STRIP_AFTER_PREFIX = data["strip_after_prefix"]

SUPER_USER = data["super_user"]
MASTER_OWNER = SUPER_USER

EXTENSIONS = data["extensions"]
DEV_LOGO = data["dev_logo"]

TOKEN = os.environ["TOKEN"]
DATABASE_KEY = os.environ["DATABASE_KEY"]
OPEN_ROBOT_API = os.environ["OPEN_ROBOT_API"]
my_secret = DATABASE_KEY

AUTHOR_NAME = data["author_name"]
AUTHOR_DISCRIMINATOR = data["discriminator"]

GITHUB = data["github"]
SUPPORT_SERVER = data["support_server"]
JOIN_LEAVE_CHANNEL_ID = data["join_leave_channel_id"]

MEME_PASS = "***qwerty123"
# this is not the real pass, just to tell the website from where the API call is comming from.
# yes you can use. but i suggest you to use your own.

PRIVACY_POLICY = data["privacy_policy"]
