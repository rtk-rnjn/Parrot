import os

from limited_memory import is_limited_memory

from .environment import load_environment

load_environment()

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]

LIMITED_MEMORY = is_limited_memory()
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

LOADABLE_COGS = {
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
    "extensions.fun.pokemon",
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
}

if LIMITED_MEMORY:
    _cogs_to_remove = {
        "extensions.music",
    }

    LOADABLE_COGS = LOADABLE_COGS - _cogs_to_remove

EXTENSION_ENVIRONMENT = {
    "extensions.supercell": (),
}

EXTENSION_CAPABILITIES = {
    "extensions.fun.meme": ("Imgflip API service",),
    "extensions.music": ("Lavalink service",),
    "extensions.nasa": ("NASA API service",),
}

DATABASE_EXTENSIONS = {
    "extensions.automod",
    "extensions.config",
    "extensions.giveaway",
    "extensions.global_chat",
    "extensions.highlight",
    "extensions.hub",
    "extensions.ipc",
    "extensions.leveling",
    "extensions.owner",
    "extensions.reminder",
    "extensions.starboard",
    "extensions.stats",
    "extensions.suggestion",
    "extensions.supercell",
    "extensions.tags",
    "extensions.telephone",
    "extensions.ticket",
    "extensions.todo",
    "extensions.welcomer",
}
