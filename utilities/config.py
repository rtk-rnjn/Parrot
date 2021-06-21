import json, os

with open('config.json') as f:
	data = json.load(f)

OWNER_IDS = data['owner_ids']
PREFIX = data['prefix']
CASE_SENSITIVE = data['case_insensitive']
STRIP_AFTER_PREFIX = data['strip_after_prefix']
SUPER_USER = data['super_user']
EXTENSIONS = data['extensions']
TOKEN = os.environ['TOKEN']
VERSION = "v3.1"
SUPPORT_SERVER = data['support_server']
INVITE = data['invite']
DEV_LOGO = data['dev_logo']
