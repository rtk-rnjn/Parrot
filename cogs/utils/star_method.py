from __future__ import annotations
from typing import List, Dict, Optional, Union

from core import Parrot, Context
import discord

# Template:
# {
#   "_id": Object(...),
#   "channel_id": INTEGER,
#   "message_id": [INTEGER, ...]
#   "guild_id": INTEGER,
#   "author_id": INTEGER,
#   "number_of_stars": INTEGER,
#   "content": STRING,
#   "picture": STRING,
#   "starrer": [INTEGER, ...]
#   "created_at": FLOAT
# }


async def _add_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    collection = bot.mongo.parrot_db.starboard
    await collection.update_one(
        {"message_id": payload.message_id}, {"$addToSet": {"starrer": payload.user_id}}
    )

async def _remove_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    collection = bot.mongo.parrot_db.starboard
    await collection.update_one(
        {"_id": payload.message_id}, {"$addToSet": {"starrer": payload.user_id}}
    )
