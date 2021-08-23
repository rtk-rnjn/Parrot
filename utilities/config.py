import json, os
from main import VER

with open('config.json') as f:
    data = json.load(f)

OWNER_IDS = data['owner_ids']
DEFAULT_PREFIX = data['prefix']
CASE_INSENSITIVE = data['case_insensitive']
STRIP_AFTER_PREFIX = data['strip_after_prefix']
SUPER_USER = data['super_user']
EXTENSIONS = data['extensions']
VERSION = VER
TOKEN = os.environ['TOKEN']
SUPPORT_SERVER = data['support_server']
INVITE = data['invite']
DEV_LOGO = data['dev_logo']
DATABASE_KEY = os.environ['DATABASE_KEY']
my_secret = DATABASE_KEY
GIT = data['github']
MEME_PASS = "***qwerty123"
