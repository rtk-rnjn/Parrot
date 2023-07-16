from __future__ import annotations

import asyncio
import random
from time import time
from typing import Any, Dict, List, Optional

import discord
from core import Context, Parrot
from discord.ext import commands
from utilities.exceptions import ParrotCheckFailure, ParrotTimeoutError
from utilities.time import ShortTime


async def _create_giveaway_post(
    *,
    message: discord.Message,
    giveaway_channel: int,
    prize: str,
    winners: int,
    endtime: float,
    required_role: int = None,
    required_guild: int = None,
    required_level: int = None,
) -> Dict[str, Any]:
    post_extra = {
        "message_id": message.id,
        "author_id": message.author.id,
        "channel_id": message.channel.id,
        "giveaway_channel": giveaway_channel,
        "guild_id": message.guild.id,  # type: ignore
        "created_at": message.created_at.timestamp(),
        "prize": prize,
        "winners": winners,
        "required_role": required_role,
        "required_guild": required_guild,
        "required_level": required_level,
    }
    return {
        "message": message,
        "created_at": message.created_at.timestamp(),
        "expires_at": endtime,
        "extra": {"name": "GIVEAWAY_END", "main": post_extra},
    }


async def end_giveaway(bot: Parrot, **kw: Any) -> List[int]:
    channel: discord.TextChannel = await bot.getch(bot.get_channel, bot.fetch_channel, kw.get("giveaway_channel"))

    msg: discord.Message = await bot.get_or_fetch_message(channel, kw["message_id"], fetch=True)  # type: ignore
    await bot.delete_timer(_id=kw["message_id"])

    embed = msg.embeds[0]
    embed.color = 0xFF000
    await msg.edit(embed=embed)

    reactors = kw["reactors"]
    if not reactors:
        for reaction in msg.reactions:
            if str(reaction.emoji) == "\N{PARTY POPPER}":
                reactors: List[int] = [user.id async for user in reaction.users()]
                break
            reactors = []

    __item__remove(reactors, bot.user.id)

    if not reactors:
        return []

    win_count = kw.get("winners", 1)

    real_winners: List[int] = []

    while True:
        if win_count > len(reactors):
            # more winner than the reactions
            return real_winners

        winners = random.choices(reactors, k=win_count)
        kw["winners"] = winners
        real_winners = await __check_requirements(bot, **kw)

        _ = [__item__remove(reactors, i) for i in real_winners]  # flake8: noqa

        await __update_giveaway_reactors(bot=bot, reactors=reactors, message_id=kw.get("message_id"))  # type: ignore

        if not real_winners and not reactors:
            # requirement do not statisfied and we are out of reactors
            return real_winners

        if real_winners:
            return real_winners
        win_count = win_count - len(real_winners)
        await asyncio.sleep(0)


async def __check_requirements(bot: Parrot, **kw: Any) -> List[int]:
    # vars
    real_winners: List[int] = kw.get("winners", [])

    current_guild: discord.Guild = bot.get_guild(kw.get("guild_id"))  # type: ignore
    required_guild: Optional[discord.Guild] = bot.get_guild(kw.get("required_guild", 0))
    required_role: int = kw.get("required_role", 0)
    required_level: int = kw.get("required_level", 0)

    for member in kw.get("winners", []):
        member = await bot.get_or_fetch_member(current_guild, member)
        assert isinstance(member, discord.Member)
        if required_guild:
            is_member_none = await bot.get_or_fetch_member(required_guild, member.id)
            if is_member_none is None:
                __item__remove(real_winners, member)

        if required_role and not member._roles.has(required_role):
            __item__remove(real_winners, member)

        if required_level:
            level = await bot.guild_level_db[f"{current_guild.id}"].find_one({"_id": member.id})
            if level < required_level:
                __item__remove(real_winners, member)

    return real_winners


async def __update_giveaway_reactors(*, bot: Parrot, reactors: List[int], message_id: int) -> None:
    collection = bot.giveaways
    await collection.update_one({"message_id": message_id}, {"$set": {"reactors": reactors}})


def __item__remove(ls: List[Any], item: Any) -> Optional[List[Any]]:
    try:
        ls.remove(item)
    except (ValueError, KeyError):
        return ls
    return ls


async def __wait_for__message(ctx: Context) -> str:
    def check(m: discord.Message) -> bool:
        return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

    try:
        msg: discord.Message = await ctx.wait_for("message", check=check, timeout=60)
    except asyncio.TimeoutError:
        raise ParrotTimeoutError()
    else:
        return msg.content


async def _make_giveaway(ctx: Context) -> Dict[str, Any]:
    bot: Parrot = ctx.bot
    quest = [
        "In what channel you want to host giveaway? (Channel ID, Channel Name, Channel Mention)",
        "Duration for the giveaway",
        "Prize for the giveaway",
        "Number of winners?",
        "Required Role? (Role ID, Role Name, Role Mention) | `skip`, `none`, `no` for no role requirement",
        "Requied Level? `skip`, `none`, `no` for no role requirement",
        "Required Server? (ID Only, bot must be in that server) `skip`, `none`, `no` for no role requirement",
    ]

    payload = {}
    CHANNEL = None

    for index, question in enumerate(quest, start=1):
        if index == 1:
            await ctx.reply(embed=discord.Embed(description=question))
            channel = await commands.TextChannelConverter().convert(ctx, argument=(await __wait_for__message(ctx)))
            CHANNEL = channel
            payload["giveaway_channel"] = channel.id

        elif index == 2:
            await ctx.reply(embed=discord.Embed(description=question))
            duration = ShortTime(await __wait_for__message(ctx))
            payload["endtime"] = duration.dt.timestamp()

        elif index == 3:
            await ctx.reply(embed=discord.Embed(description=question))
            prize = await __wait_for__message(ctx)
            payload["prize"] = prize

        elif index == 4:
            await ctx.reply(embed=discord.Embed(description=question))
            winners = __is_int(await __wait_for__message(ctx), "Winner must be a whole number")
            payload["winners"] = winners

        elif index == 5:
            await ctx.reply(embed=discord.Embed(description=question))
            arg = await __wait_for__message(ctx)
            if arg.lower() not in ("skip", "no", "none"):
                role = await commands.RoleConverter().convert(ctx, argument=arg)
                payload["required_role"] = role.id
            else:
                payload["required_role"] = None

        elif index == 6:
            await ctx.reply(embed=discord.Embed(description=question))
            level = __is_int(await __wait_for__message(ctx), "Level must be a whole number")
            payload["required_level"] = level

        elif index == 7:
            await ctx.reply(embed=discord.Embed(description=question))
            server = __is_int(await __wait_for__message(ctx), "Server ID must be a whole number")
            payload["required_guild"] = server

    embed = discord.Embed(
        title="\N{PARTY POPPER} Giveaway \N{PARTY POPPER}",
        color=ctx.bot.color,
        timestamp=ctx.message.created_at,
        url=ctx.message.jump_url,
    )
    embed.description = f"""**React \N{PARTY POPPER} to win**

> Prize: **{payload['prize']}**
> Hosted by: {ctx.author.mention} (`{ctx.author.id}`)
> Ends in: <t:{int(payload['endtime'])}:R>
"""
    embed.set_footer(text=f"ID: {ctx.message.id}", icon_url=ctx.author.display_avatar.url)
    CHANNEL = CHANNEL or ctx.channel
    msg = await CHANNEL.send(embed=embed)
    await msg.add_reaction("\N{PARTY POPPER}")
    bot.message_cache[msg.id] = msg
    main_post = await _create_giveaway_post(message=msg, **payload)  # flake8: noqa

    await bot.giveaways.insert_one({**main_post["extra"]["main"], "reactors": [], "status": "ONGOING"})
    await ctx.reply(embed=discord.Embed(description="Giveaway has been created!"))
    return main_post


async def _make_giveaway_drop(ctx: Context, *, duration: ShortTime, winners: int, prize: str):
    payload = {
        "giveaway_channel": ctx.channel.id,
        "endtime": duration.dt.timestamp(),
        "winners": winners,
        "prize": prize,
        "required_role": None,
        "required_level": None,
        "required_guild": None,
    }

    embed = discord.Embed(
        title="\N{PARTY POPPER} Giveaway \N{PARTY POPPER}",
        color=ctx.bot.color,
        timestamp=ctx.message.created_at,
        url=ctx.message.jump_url,
    )
    embed.description = f"""**React \N{PARTY POPPER} to win**

> Prize: **{payload['prize']}**
> Hosted by: {ctx.author.mention} (`{ctx.author.id}`)
> Ends: <t:{int(payload['endtime'])}:R>
"""
    embed.set_footer(text=f"ID: {ctx.message.id}", icon_url=ctx.author.display_avatar.url)
    msg: discord.Message = await ctx.send(embed=embed)
    await msg.add_reaction("\N{PARTY POPPER}")
    main_post = await _create_giveaway_post(message=msg, **payload)  # flake8: noqa

    await ctx.bot.giveaways.insert_one({**main_post["extra"]["main"], "reactors": [], "status": "ONGOING"})
    return main_post


def __is_int(st: str, error: str) -> Optional[int]:
    if st.lower() in {"skip", "none", "no"}:
        return None
    try:
        main = int(st)
    except ValueError as e:
        raise ParrotCheckFailure(error) from e
    else:
        return main


async def add_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    if str(payload.emoji) != "\N{PARTY POPPER}":
        return

    await bot.giveaways.update_one(
        {"message_id": payload.message_id, "status": "ONGOING"},
        {"$addToSet": {"reactors": payload.user_id}},
    )


async def remove_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    if str(payload.emoji) != "\N{PARTY POPPER}":
        return

    await bot.giveaways.update_one(
        {"message_id": payload.message_id, "status": "ONGOING"},
        {"$pull": {"reactors": payload.user_id}},
    )
