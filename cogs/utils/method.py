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

IGNORE = {
    "all",
    "delete",
    "del",
    "create",
    "add",
    "editname",
    "edittext",
    "owner",
    "info",
    "snipe",
    "steal",
    "claim",
    "tnsfw",
    "nsfw",
    "tooglensfw",
    "give",
    "transfer",
    "raw",
}


async def _show_tag(bot: Parrot, ctx: Context, tag: str, msg_ref: Optional[discord.Message] = None):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag}):
        if not data["nsfw"] and msg_ref is not None or data["nsfw"] and ctx.channel.nsfw and msg_ref is not None:  # type: ignore
            await msg_ref.reply(data["text"])
        elif not data["nsfw"] or ctx.channel.nsfw:  # type: ignore
            await ctx.send(data["text"])
        else:
            await ctx.reply(f"{ctx.author.mention} this tag can only be called in NSFW marked channel")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")
    await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$inc": {"count": 1}})  # type: ignore


async def _show_raw_tag(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        first = discord.utils.escape_markdown(data["text"])
        main = discord.utils.escape_mentions(first)
        if data["nsfw"] and ctx.channel.nsfw or not data["nsfw"]:  # type: ignore
            await ctx.safe_send(main)
        else:
            await ctx.reply(f"{ctx.author.mention} this tag can only be called in NSFW marked channel")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _create_tag(bot: Parrot, ctx: Context, tag: str, text: str):
    tag = tag.strip()
    text = text.strip()

    if not tag:
        return await ctx.error(f"{ctx.author.mention} you did not provided any tag name")

    if not text:
        return await ctx.error(f"{ctx.author.mention} you did not provided any text to be saved")

    collection = ctx.bot.tags_collection
    if tag in IGNORE:
        return await ctx.error(f"{ctx.author.mention} the name `{tag}` is reserved word.")
    if _ := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        return await ctx.error(f"{ctx.author.mention} the name `{tag}` already exists")

    val = await ctx.prompt(f"{ctx.author.mention} do you want to make the tag as NSFW marked channels")
    if val is None:
        return await ctx.error(f"{ctx.author.mention} you did not responds on time. Considering as non NSFW")
    nsfw = bool(val)
    await collection.insert_one(
        {
            "tag_id": tag,
            "text": text,
            "count": 0,
            "owner": ctx.author.id,
            "guild_id": ctx.guild.id,  # type: ignore
            "nsfw": nsfw,
            "created_at": int(time()),
        }
    )
    await ctx.reply(f"{ctx.author.mention} tag created successfully")


async def _delete_tag(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        if data["owner"] == ctx.author.id:
            await collection.delete_one({"tag_id": tag})
            await ctx.reply(f"{ctx.author.mention} tag deleted successfully")
        else:
            await ctx.error(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _name_edit(bot: Parrot, ctx: Context, tag: str, name: str):
    collection = ctx.bot.tags_collection
    if _ := await collection.find_one({"tag_id": name, "guild_id": ctx.guild.id}):  # type: ignore
        await ctx.error(f"{ctx.author.mention} that name already exists in the database")
    elif data := await collection.find_one({"tag_id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"tag_id": name}})  # type: ignore
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.error(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _text_edit(bot: Parrot, ctx: Context, tag: str, text: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        if data["owner"] == ctx.author.id:
            await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"text": text}})  # type: ignore
            await ctx.reply(f"{ctx.author.mention} tag content successfully changed")
        else:
            await ctx.error(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _claim_owner(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        member = await bot.get_or_fetch_member(ctx.guild, data["owner"])  # type: ignore
        if member:
            return await ctx.error(
                f"{ctx.author.mention} you can not claim the tag ownership as the member is still in the server"
            )
        await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"owner": ctx.author.id}})  # type: ignore
        await ctx.reply(f"{ctx.author.mention} ownership of tag `{tag}` claimed!")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _transfer_owner(bot: Parrot, ctx: Context, tag: str, member: discord.Member):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        if data["owner"] != ctx.author.id:
            return await ctx.error(f"{ctx.author.mention} you don't own this tag")
        val = await ctx.prompt(
            f"{ctx.author.mention} are you sure to transfer the tag ownership to **{member}**? This process is irreversible!"
        )
        if val is None:
            await ctx.error(f"{ctx.author.mention} you did not responds on time")
        elif val:
            await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"owner": member.id}})  # type: ignore
            await ctx.reply(f"{ctx.author.mention} tag ownership successfully transfered to **{member}**")
        else:
            await ctx.error(f"{ctx.author.mention} ok! reverting the process!")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _toggle_nsfw(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        nsfw = not data["nsfw"]
        await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"nsfw": nsfw}})  # type: ignore
        await ctx.reply(f"{ctx.author.mention} NSFW status of tag named `{tag}` is set to **{nsfw}**")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _show_tag_mine(bot: Parrot, ctx: Context):
    collection = ctx.bot.tags_collection
    i = 1
    entries: List[str] = []

    async for data in collection.find({"owner": ctx.author.id, "guild_id": ctx.guild.id, "tag_id": {"$exists": True}}):  # type: ignore
        entries.append(f"`{i}` {data['_id']}")
        i += 1
    try:
        return await ctx.paginate(entries, module="SimplePages")
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} you don't have any tags registered with your name")


async def _show_all_tags(bot: Parrot, ctx: Context):
    collection = ctx.bot.tags_collection
    i = 1
    entries: List[str] = []
    async for data in collection.find({"guild_id": ctx.guild.id, "tag_id": {"$exists": True}}):  # type: ignore
        entries.append(f"`{i}` - {data['tag_id']}")
        i += 1
    try:
        return await ctx.paginate(entries, module="SimplePages")
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} this server don't have any tags")


async def _view_tag(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):  # type: ignore
        text_len = len(data["text"])
        assert ctx.guild
        owner = await bot.get_or_fetch_member(ctx.guild, data["owner"])
        nsfw = data["nsfw"]
        count = data["count"]
        created_at = f"<t:{data['created_at']}>"
        claimable = owner is None
        em = (
            discord.Embed(
                title=f"Tag: {tag}",
                timestamp=discord.utils.utcnow(),
                color=ctx.author.color,
            )
            .add_field(name="Owner", value=f"**{owner.mention if owner else None}**")
            .add_field(name="Created At?", value=created_at)
            .add_field(name="Text Length", value=str(text_len))
            .add_field(name="Is NSFW?", value=nsfw)
            .add_field(name="Tag Used", value=count)
            .add_field(name="Can Claim?", value=claimable)
        )
        await ctx.reply(embed=em)


async def _create_todo(bot: Parrot, ctx: Context, name: str, text: str):
    collection = ctx.user_collection
    if data := await collection.find_one({"id": name}):
        await ctx.reply(f"{ctx.author.mention} `{name}` already exists as your TODO list")
    else:
        await collection.insert_one(
            {
                "id": name,
                "text": text,
                "time": int(time()),
                "deadline": None,
                "msglink": ctx.message.jump_url,
            }
        )
        await ctx.reply(f"{ctx.author.mention} created as your TODO list")


async def _set_timer_todo(bot: Parrot, ctx: Context, name: str, timestamp: float):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        post = {"deadline": timestamp}
        try:
            await ctx.author.send(
                f"You will be reminded for your task named **{name}** here at <t:{int(timestamp)}>. "
                f"To delete your reminder consider typing.\n```\n{ctx.clean_prefix}remind delete {ctx.message.id}```",
                view=ctx.send_view(),
            )
        except Exception as e:
            return await ctx.error(f"{ctx.author.mention} seems that your DM are blocked for the bot. Error: {e}")
        finally:
            await collection.update_one({"_id": name}, {"$set": post})
            await bot.create_timer(
                _event_name="todo",
                expires_at=timestamp,
                created_at=ctx.message.created_at.timestamp(),
                message=ctx.message,
                content=f"you had set TODO reminder for your task named `{name}`",
                dm_notify=True,
                is_todo=True,
            )
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _update_todo_name(bot: Parrot, ctx: Context, name: str, new_name: str):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        if _ := await collection.find_one({"id": new_name}):
            await ctx.reply(f"{ctx.author.mention} `{new_name}` already exists as your TODO list")
        else:
            await collection.update_one({"id": name}, {"$set": {"id": new_name}})
            await ctx.reply(f"{ctx.author.mention} name changed from `{name}` to `{new_name}`")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _update_todo_text(bot: Parrot, ctx: Context, name: str, text: str):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        await collection.update_one({"id": name}, {"$set": {"text": text}})
        await ctx.reply(f"{ctx.author.mention} TODO list of name `{name}` has been updated")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _list_todo(bot: Parrot, ctx: Context):
    collection = ctx.user_collection
    i = 1
    entries: List[str] = []
    async for data in collection.find({}):
        entries.append(f"[`{i}`]({data['msglink']}) {data['id']}")
        i += 1
    try:
        return await ctx.paginate(entries, module="SimplePages")
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} you do not have task to do")


async def _show_todo(bot: Parrot, ctx: Context, name: str):
    collection = ctx.user_collection
    if data := await collection.find_one({"id": name}):
        await ctx.reply(f"> **{data['id']}**\n\nDescription: {data['text']}\n\nCreated At: <t:{data['time']}>")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


async def _delete_todo(bot: Parrot, ctx: Context, name: str):
    collection = ctx.user_collection
    if _ := await collection.find_one({"id": name}):
        await collection.delete_one({"id": name})
        await ctx.reply(f"{ctx.author.mention} delete `{name}` task")
    else:
        await ctx.reply(f"{ctx.author.mention} you don't have any TODO list with name `{name}`")


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
    msg: discord.Message = await ctx.send(embed=embed)  # type: ignore
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
