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
    data = await collection.find_one_and_update(
        {"message_id": payload.message_id},
        {"$addToSet": {"starrer": payload.user_id}, "$inc": {"number_of_stars": 1}},
        return_document=True
    )
    if data:
        await edit_starbord_post(bot, payload, **data)


async def _remove_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    collection = bot.mongo.parrot_db.starboard
    data = await collection.find_one_and_update(
        {"message_id": payload.message_id},
        {"$pull": {"starrer": payload.user_id}, "$inc": {"number_of_stars": -1}},
        return_document=True
    )
    if data:
        await edit_starbord_post(bot, payload, **data)


async def __make_starboard_post(
    bot: Parrot,
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
        "number_of_stars": await get_star_count(bot, message, from_db=False),
    }

    if message.attachments:
        if (
            message.attachments[0]
            .url.lower()
            .endswith(("png", "jpeg", "jpg", "gif", "webp"))
        ):
            post["picture"] = message.attachments[0].url
        else:
            post["attachment"] = message.attachments[0].url

    return post


async def get_star_count(bot: Parrot, message: discord.Message, *, from_db: bool=True) -> Optional[int]:
    if from_db:
        if data := await bot.mongo.parrot_db.starboard.find_one({"message_id": message.id}):
            return data["number_of_stars"]

    for reaction in message.reactions:
        if str(reaction.emoji) == "\N{WHITE MEDIUM STAR}":
            return reaction.count
    return 0

def star_gradient_colour(stars) -> int:
    p = stars / 13
    if p > 1.0:
        p = 1.0
    red = 255
    green = int((194 * p) + (253 * (1 - p)))
    blue = int((12 * p) + (247 * (1 - p)))
    return (red << 16) + (green << 8) + blue

def star_emoji(stars) -> str:
    if 5 > stars >= 0:
        return '\N{WHITE MEDIUM STAR}'
    elif 10 > stars >= 5:
        return '\N{GLOWING STAR}'
    elif 25 > stars >= 10:
        return '\N{DIZZY SYMBOL}'
    else:
        return '\N{SPARKLES}'

async def star_post(
    bot: Parrot, *, starboard_channel: discord.TextChannel, message: discord.Message
) -> None:
    embed = discord.Embed(timestamp=message.created_at)
    embed.set_footer(text=f"ID: {message.author.id}")
    
    count = await get_star_count(bot, message, from_db=True)
    embed.color = star_gradient_colour(count)

    embed.set_author(
        name=str(message.author),
        icon_url=message.author.display_avatar.url,
        url=message.jump_url,
    )
    if message.content:
        embed.description = message.content
    if message.attachments:
        if (
            message.attachments[0]
            .url.lower()
            .endswith(("png", "jpeg", "jpg", "gif", "webp"))
        ):
            embed.set_image(url=message.attachments[0].url)
        else:
            embed.add_field(
                name="Attachment",
                value=f"[{message.attachments[0].filename}]({message.attachments[0].url})",
            )
    msg = await starboard_channel.send(
        f"{star_emoji(count)} {count} | In: {message.channel.mention} | Message ID: {message.id}\n> {message.jump_url}",
        embed=embed
    )

    bot.message_cache[msg.id] = msg
    bot.message_cache[message.id] = message

    post = await __make_starboard_post(bot, bot_message=msg, message=message)
    await bot.mongo.parrot_db.starboard.insert_one(post)


async def edit_starbord_post(bot: Parrot, payload: discord.RawReactionActionEvent, **data) -> None:
    ch: discord.TextChannel = await bot.getch(bot.get_channel, bot.fetch_channel, data["channel_id"])
    if ch is None:
        return

    if payload.user_id == bot.user.id:
        # message was reacted on bot's message
        bot_message_id = payload.message_id
    else:
        data["message_id"].remove(payload.message_id)
        bot_message_id = data["message_id"][0]

    msg: discord.Message = await bot.get_or_fetch_message(ch, bot_message_id)
    
    if not msg.embeds:
        # moderators removed the embeds
        return

    embed: discord.Embed = msg.embeds[0]

    count = await get_star_count(bot, msg, from_db=True)
    embed.color = star_gradient_colour(count or 1)

    await msg.edit(embed=embed, content=msg.content)