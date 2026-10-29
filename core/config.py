import os

from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")

RESTRICTED_MODE = os.environ.get("RESTRICTED_MODE", "False").lower() in (
    "true",
    "1",
    "yes",
)
LAVALINK_PASSWORD = os.environ.get("LAVALINK_PASSWORD", "youshallnotpass")
OWNER_ID = os.getenv("OWNER_ID")

os.environ["JISHAKU_HIDE"] = "True"
os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
os.environ["JISHAKU_FORCE_PAGINATOR"] = "True"

LOADABLE_COGS = [
    "extensions.automod",
    "extensions.cc",
    "extensions.chess",
    "extensions.config",
    "extensions.events",
    "extensions.fun.easter",
    "extensions.fun.fun",
    "extensions.fun.hanukkah",
    "extensions.fun.love",
    "extensions.fun.meme",
    "extensions.fun.minecraft",
    "extensions.fun.pride",
    "extensions.fun.snakes",
    "extensions.games",
    "extensions.giveaway",
    "extensions.global_chat",
    "extensions.highlight",
    "extensions.hub",
    "extensions.image",
    "extensions.ipc",
    "extensions.leveling",
    "extensions.meta",
    "extensions.misc",
    "extensions.misc.math",
    "extensions.misc.wiki",
    "extensions.mod",
    "extensions.music",
    "extensions.nasa",
    "extensions.nsfw",
    "extensions.owner",
    "extensions.reminder",
    "extensions.rtfm",
    "extensions.rtfm.linter",
    "extensions.rtfm.w3schools",
    "extensions.starboard",
    "extensions.stats",
    "extensions.suggestion",
    "extensions.supercell",
    "extensions.tags",
    "extensions.telephone",
    "extensions.ticket",
    "extensions.todo",
    "extensions.welcomer",
]
