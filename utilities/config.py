import json, os

with open('config.json') as f:
    data = json.load(f)

OWNER_IDS = data['owner_ids']
DEFAULT_PREFIX = data['prefix']
CASE_INSENSITIVE = data['case_insensitive']
STRIP_AFTER_PREFIX = data['strip_after_prefix']
SUPER_USER = data['super_user']
EXTENSIONS = data['extensions']
VERSION = "v3.8.0"
TOKEN = os.environ['TOKEN']
DEV_LOGO = data['dev_logo']
DATABASE_KEY = os.environ['DATABASE_KEY']
my_secret = DATABASE_KEY
MEME_PASS = "***qwerty123" # this is not the real pass, just to tell the website from where the API call is comming from.
