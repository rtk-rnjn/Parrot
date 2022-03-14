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
#   "created_at": FLOAT,
#   "attachment": STR
# }


async def _add_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    collection = bot.mongo.parrot_db.starboard
    await collection.update_one(
        {"message_id": payload.message_id},
        {
            "$addToSet": {"starrer": payload.user_id},
            "$inc": {"number_of_stars": 1}
        }
    )

async def _remove_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    collection = bot.mongo.parrot_db.starboard
    await collection.update_one(
        {"_id": payload.message_id},
        {
            "$pull": {"starrer": payload.user_id},
            "$inc": {"number_of_stars": -1}
        }
    )


def __make_giveaway_post(
    *,
    bot_message: discord.Message,
    message: discord.Message,
) -> Dict[str, Union[str, int, List[int], None]]:
    post = {
        "message_id": [bot_message.id, message.id],
        "channel_id": message.channel.id,
        "author_id": message.author.id,
        "guild_id": message.guild.id,
        "created_at": message.created_at.timestamp(),
        "content": message.content,
        "number_of_stars": get_star_count(message)
    }

    if message.attachments:
        if message.attachments[0].url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
            post["picture"] = message.attachments[0].url
        else:
            post["attachment"] = message.attachments[0].url

    return post


def get_star_count(message) -> Optional[int]:
    for reaction in message.reactions:
        if str(reaction.emoji) == "\N{WHITE MEDIUM STAR}":
            return reaction.count
    return 0


async def star_post(
    bot: Parrot, *, starboard_channel: discord.TextChannel, message: discord.Message
):
    embed = discord.Embed()

    embed.set_author(
        name=str(message.author),
        icon_url=message.author.display_avatar.url,
        url=message.jump_url
    )
    if message.content:
        embed.description = message.content
    if message.attachments:
        if message.attachments[0].url.lower().endswith(('png', 'jpeg', 'jpg', 'gif', 'webp')):
            embed.set_image(url=message.attachments[0].url)
        else:
            embed.add_field(
                name="Attachment",
                value=f"[{message.attachments[0].filename}]({message.attachments[0].url})"
            )
    msg = await starboard_channel.send(embed=embed)

    bot.message_cache[msg.id] = msg
    bot.message_cache[message.id] = message

    post = __make_giveaway_post(bot_message=msg, message=message)
    await bot.mongo.parrot_db.starboard.insert_one(post)
