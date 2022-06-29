from __future__ import annotations
import asyncio
import random
from typing import Any, Dict, List, Optional

import discord
from discord.ext import commands
from time import time

from utilities.exceptions import ParrotCheckFailure, ParrotTimeoutError
from utilities.paginator import ParrotPaginator
from utilities.time import ShortTime

from core import Parrot, Context

IGNORE = [
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
]


async def _show_tag(bot: Parrot, ctx: Context, tag, msg_ref=None):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if not data["nsfw"]:
            if msg_ref is not None:
                await msg_ref.reply(data["text"])
            else:
                await ctx.send(data["text"])
        else:
            if ctx.channel.nsfw:
                if msg_ref is not None:
                    await msg_ref.reply(data["text"])
                else:
                    await ctx.send(data["text"])
            else:
                await ctx.reply(
                    f"{ctx.author.mention} this tag can only be called in NSFW marked channel"
                )
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")
    await collection.update_one({"id": tag}, {"$inc": {"count": 1}})


async def _show_raw_tag(bot: Parrot, ctx: Context, tag: str):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"_id": tag}):
        first = discord.utils.escape_markdown(data["text"])
        main = discord.utils.escape_mention(first)
        if not data["nsfw"]:
            await ctx.safe_send(main)
        else:
            if ctx.channel.nsfw:
                await ctx.safe_send(main)
            else:
                await ctx.reply(
                    f"{ctx.author.mention} this tag can only be called in NSFW marked channel"
                )
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _create_tag(bot: Parrot, ctx: Context, tag, text):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if tag in IGNORE:
        return await ctx.reply(
            f"{ctx.author.mention} the name `{tag}` is reserved word."
        )
    if _ := await collection.find_one({"id": tag}):
        return await ctx.reply(f"{ctx.author.mention} the name `{tag}` already exists")

    val = await ctx.prompt(
        f"{ctx.author.mention} do you want to make the tag as NSFW marked channels"
    )
    if val is None:
        return await ctx.reply(
            f"{ctx.author.mention} you did not responds on time. Considering as non NSFW"
        )
    nsfw = bool(val)
    await collection.insert_one(
        {
            "id": tag,
            "text": text,
            "count": 0,
            "owner": ctx.author.id,
            "nsfw": nsfw,
            "created_at": int(time()),
        }
    )
    await ctx.reply(f"{ctx.author.mention} tag created successfully")


async def _delete_tag(bot: Parrot, ctx: Context, tag):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.delete_one({"id": tag})
            await ctx.reply(f"{ctx.author.mention} tag deleted successfully")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _name_edit(bot: Parrot, ctx: Context, tag, name):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if _ := await collection.find_one({"id": name}):
        await ctx.reply(
            f"{ctx.author.mention} that name already exists in the database"
        )
    elif data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"id": tag}, {"$set": {"id": name}})
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _text_edit(bot: Parrot, ctx: Context, tag, text):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"id": tag}, {"$set": {"text": text}})
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _claim_owner(bot: Parrot, ctx: Context, tag):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        member = await bot.get_or_fetch_member(ctx.guild, data["owner"])
        if member:
            return await ctx.reply(
                f"{ctx.author.mention} you can not claim the tag ownership as the member is still in the server"
            )
        await collection.update_one({"id": tag}, {"$set": {"owner": ctx.author.id}})
        await ctx.reply(f"{ctx.author.mention} ownership of tag `{tag}` claimed!")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _transfer_owner(bot: Parrot, ctx: Context, tag, member):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        val = await ctx.prompt(
            f"{ctx.author.mention} are you sure to transfer the tag ownership to **{member}**? This process is irreversible!"
        )
        if val is None:
            await ctx.reply(f"{ctx.author.mention} you did not responds on time")
        elif val:
            await collection.update_one({"id": tag}, {"$set": {"owner": member.id}})
            await ctx.reply(
                f"{ctx.author.mention} tag ownership successfully transfered to **{member}**"
            )
        else:
            await ctx.reply(f"{ctx.author.mention} ok! reverting the process!")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _toggle_nsfw(bot: Parrot, ctx: Context, tag):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        nsfw = not data["nsfw"]
        await collection.update_one({"id": tag}, {"$set": {"nsfw": nsfw}})
        await ctx.reply(
            f"{ctx.author.mention} NSFW status of tag named `{tag}` is set to **{nsfw}**"
        )
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _show_tag_mine(bot: Parrot, ctx: Context):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    i = 1
    paginator = ParrotPaginator(ctx, title="Tags")
    async for data in collection.find({"owner": ctx.author.id}):
        paginator.add_line(f"`{i}` {data['_id']}")
        i += 1
    try:
        await paginator.start()
    except IndexError:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any tags registered with your name"
        )


async def _show_all_tags(bot: Parrot, ctx: Context):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    i = 1
    paginator = ParrotPaginator(ctx, title="Tags", per_page=12)
    async for data in collection.find({}):
        paginator.add_line(f"`{i}` {data['id']}")
        i += 1
    try:
        await paginator.start()
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} this server don't have any tags")


async def _view_tag(bot: Parrot, ctx: Context, tag):
    collection = bot.mongo.tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        em = discord.Embed(
            title=f"Tag: {tag}",
            timestamp=discord.utils.utcnow(),
            color=ctx.author.color,
        )
        text_len = len(data["text"])
        owner = await bot.get_or_fetch_member(ctx.guild, data["owner"])
        nsfw = data["nsfw"]
        count = data["count"]
        created_at = f"<t:{data['created_at']}>"
        claimable = owner is None
        em.add_field(name="Owner", value=f"**{owner.mention if owner else None}** ")
        em.add_field(name="Created At?", value=created_at)
        em.add_field(name="Text Length", value=str(text_len))
        em.add_field(name="Is NSFW?", value=nsfw)
        em.add_field(name="Tag Used", value=count)
        em.add_field(name="Can Claim?", value=claimable)
        em.set_footer(text=f"{ctx.author}")
        await ctx.reply(embed=em)


async def _create_todo(bot: Parrot, ctx: Context, name, text):
    collection = bot.mongo.todo[f"{ctx.author.id}"]
    if data := await collection.find_one({"id": name}):
        await ctx.reply(
            f"{ctx.author.mention} `{name}` already exists as your TODO list"
        )
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
    collection = bot.mongo.todo[f"{ctx.author.id}"]
    if _ := await collection.find_one({"id": name}):
        post = {"deadline": timestamp}
        try:
            await ctx.author.send(
                f"You will be reminded for your task named **{name}** here at <t:{int(timestamp)}>. To delete your reminder consider typing.\n```\n$delremind {ctx.message.id}```"
            )
        except Exception as e:
            return await ctx.send(
                f"{ctx.author.mention} seems that your DM are blocked for the bot. Error: {e}"
            )
        finally:
            await collection.update_one({"_id": name}, {"$set": post})
            await bot.get_cog("Utils").create_timer(
                expires_at=timestamp,
                created_at=ctx.message.created_at.timestamp(),
                message=ctx.message,
                content=f"you had set TODO reminder for your task named **{name}**",
                dm_notify=True,
                is_todo=True,
            )
    else:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any TODO list with name `{name}`"
        )


async def _update_todo_name(bot: Parrot, ctx: Context, name, new_name):
    collection = bot.mongo.todo[f"{ctx.author.id}"]
    if _ := await collection.find_one({"id": name}):
        if _ := await collection.find_one({"id": new_name}):
            await ctx.reply(
                f"{ctx.author.mention} `{new_name}` already exists as your TODO list"
            )
        else:
            await collection.update_one({"id": name}, {"$set": {"id": new_name}})
            await ctx.reply(
                f"{ctx.author.mention} name changed from `{name}` to `{new_name}`"
            )
    else:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any TODO list with name `{name}`"
        )


async def _update_todo_text(bot: Parrot, ctx: Context, name, text):
    collection = bot.mongo.todo[f"{ctx.author.id}"]
    if _ := await collection.find_one({"id": name}):
        await collection.update_one({"id": name}, {"$set": {"text": text}})
        await ctx.reply(
            f"{ctx.author.mention} TODO list of name `{name}` has been updated"
        )
    else:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any TODO list with name `{name}`"
        )


async def _list_todo(bot: Parrot, ctx: Context):
    collection = bot.mongo.todo[f"{ctx.author.id}"]
    i = 1
    paginator = ParrotPaginator(ctx, title="Your Pending Tasks", per_page=12)
    async for data in collection.find({}):
        paginator.add_line(f"[`{i}`]({data['msglink']}) {data['id']}")
        i += 1
    try:
        await paginator.start()
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} you do not have task to do")


async def _show_todo(bot: Parrot, ctx: Context, name):
    collection = bot.mongo.todo[f"{ctx.author.id}"]
    if data := await collection.find_one({"id": name}):
        await ctx.reply(
            f"> **{data['id']}**\n\nDescription: {data['text']}\n\nCreated At: <t:{data['time']}>"
        )
    else:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any TODO list with name `{name}`"
        )


async def _delete_todo(bot: Parrot, ctx: Context, name):
    collection = bot.mongo.todo[f"{ctx.author.id}"]
    if _ := await collection.find_one({"id": name}):
        await collection.delete_one({"id": name})
        await ctx.reply(f"{ctx.author.mention} delete `{name}` task")
    else:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any TODO list with name `{name}`"
        )


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
        "guild_id": message.guild.id,
        "created_at": message.created_at.timestamp(),
        "prize": prize,
        "winners": winners,
        "required_role": required_role,
        "required_guild": required_guild,
        "required_level": required_level,
    }
    post = {
        "message": message,
        "created_at": message.created_at.timestamp(),
        "expires_at": endtime,
        "extra": {"name": "GIVEAWAY_END", "main": post_extra},
    }
    return post


async def end_giveaway(bot: Parrot, **kw) -> List[int]:
    channel = await bot.getch(
        bot.get_channel, bot.fetch_channel, kw.get("giveaway_channel")
    )

    msg = await bot.get_or_fetch_message(channel, kw.get("message_id"))

    embed = msg.embeds[0]
    embed.color = 0xFF000
    await msg.edit(embed=embed)

    # data = await bot.mongo.parrot_db.giveaway.find_one(
    #     {"message_id": kw.get("message_id"), "guild_id": kw.get("guild_id"), "status": "ONGOING"}
    # )

    reactors = kw["reactors"]
    if not reactors:
        for reaction in msg.reactions:
            if str(reaction.emoji) == "\N{PARTY POPPER}":
                reactors: List[int] = [user.id async for user in reaction.users()]
                break
            reactors = []

    __item__remove(reactors, bot.user.id)

    if not reactors:
        return

    win_count = kw.get("winners", 1)

    real_winners = []

    while True:
        if win_count > len(reactors):
            # more winner than the reactions
            return real_winners

        winners = random.choices(reactors, k=win_count)
        kw["winners"] = winners
        real_winners = await __check_requirements(bot, **kw)

        [__item__remove(reactors, i) for i in real_winners]  # flake8: noqa

        await __update_giveaway_reactors(
            bot=bot, reactors=reactors, message_id=kw.get("message_id")
        )

        if not real_winners and not reactors:
            # requirement do not statisfied and we are out of reactors
            return real_winners

        if real_winners:
            return real_winners
        win_count = win_count - len(real_winners)
        await asyncio.sleep(0)


async def __check_requirements(bot: Parrot, **kw: Dict[str, Any]) -> List[int]:
    # vars
    real_winners = kw.get("winners")

    current_guild = bot.get_guild(kw.get("guild_id"))
    required_guild = bot.get_guild(kw.get("required_guild"))
    required_role = kw.get(
        "required_role",
    )
    required_level = kw.get("required_level", 0)

    for member in kw.get("winners"):
        member = await bot.get_or_fetch_member(current_guild, member)
        if required_guild:
            is_member_none = await bot.get_or_fetch_member(required_guild, member.id)
            if is_member_none is None:
                __item__remove(real_winners, member)

        if required_role and not member._roles.has(required_role):
            __item__remove(real_winners, member)

        if required_level:
            level = await bot.mongo.leveling[f"{current_guild.id}"].find_one(
                {"_id": member.id}
            )
            if level < required_level:
                __item__remove(real_winners, member)

    return real_winners


async def __update_giveaway_reactors(
    *, bot: Parrot, reactors: List[int], message_id: int
) -> None:
    collection = bot.mongo.parrot_db.giveaway
    await collection.update_one(
        {"message_id": message_id}, {"$set": {"reactors": reactors}}
    )


def __item__remove(ls: List[Any], item: Any) -> Optional[List]:
    try:
        ls.remove(item)
    except (ValueError, KeyError):
        return ls


async def __wait_for__message(ctx: Context) -> Optional[str]:
    def check(m: discord.Message) -> bool:
        return m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

    try:
        msg = await ctx.bot.wait_for("message", check=check, timeout=60)
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
            channel = await commands.TextChannelConverter().convert(
                ctx, argument=(await __wait_for__message(ctx))
            )
            CHANNEL = channel
            payload["giveaway_channel"] = channel.id

        if index == 2:
            await ctx.reply(embed=discord.Embed(description=question))
            duration = ShortTime(await __wait_for__message(ctx))
            payload["endtime"] = duration.dt.timestamp()

        if index == 3:
            await ctx.reply(embed=discord.Embed(description=question))
            prize = await __wait_for__message(ctx)
            payload["prize"] = prize

        if index == 4:
            await ctx.reply(embed=discord.Embed(description=question))
            winners = __is_int(
                await __wait_for__message(ctx), "Winner must be a whole number"
            )
            payload["winners"] = winners

        if index == 5:
            await ctx.reply(embed=discord.Embed(description=question))
            arg = await __wait_for__message(ctx)
            if arg.lower() not in ("skip", "no", "none"):
                role = await commands.RoleConverter().convert(ctx, argument=arg)
                payload["required_role"] = role.id
            else:
                payload["required_role"] = None

        if index == 6:
            await ctx.reply(embed=discord.Embed(description=question))
            level = __is_int(
                await __wait_for__message(ctx), "Level must be a whole number"
            )
            payload["required_level"] = level

        if index == 7:
            await ctx.reply(embed=discord.Embed(description=question))
            server = __is_int(
                await __wait_for__message(ctx), "Server must be a whole number"
            )
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
    embed.set_footer(
        text=f"ID: {ctx.message.id}", icon_url=ctx.author.display_avatar.url
    )
    CHANNEL = CHANNEL or ctx.channel
    msg = await CHANNEL.send(embed=embed)
    await msg.add_reaction("\N{PARTY POPPER}")
    bot.message_cache[msg.id] = msg
    main_post = await _create_giveaway_post(message=msg, **payload)  # flake8: noqa

    await bot.mongo.parrot_db.giveaway.insert_one(
        {**main_post["extra"]["main"], "reactors": [], "status": "ONGOING"}
    )
    return main_post


async def _make_giveaway_drop(
    ctx: Context, *, duration: ShortTime, winners: int, prize: str
):
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
> Ends in: <t:{int(payload['endtime'])}:R>
"""
    embed.set_footer(
        text=f"ID: {ctx.message.id}", icon_url=ctx.author.display_avatar.url
    )
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("\N{PARTY POPPER}")
    main_post = await _create_giveaway_post(message=msg, **payload)  # flake8: noqa

    await ctx.bot.mongo.parrot_db.giveaway.insert_one(
        {**main_post["extra"]["main"], "reactors": [], "status": "ONGOING"}
    )
    return main_post


def __is_int(st: str, error: str) -> Optional[int]:
    if st.lower() in ("skip", "none", "no"):
        return None
    try:
        main = int(st)
    except ValueError:
        raise ParrotCheckFailure(error)
    else:
        return main


async def add_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    if str(payload.emoji) != "\N{PARTY POPPER}":
        return

    await bot.mongo.parrot_db.giveaway.update_one(
        {"message_id": payload.message_id, "status": "ONGOING"},
        {"$addToSet": {"reactors": payload.user_id}},
    )


async def remove_reactor(bot: Parrot, payload: discord.RawReactionActionEvent):
    if str(payload.emoji) != "\N{PARTY POPPER}":
        return

    await bot.mongo.parrot_db.giveaway.update_one(
        {"message_id": payload.message_id, "status": "ONGOING"},
        {"$pull": {"reactors": payload.user_id}},
    )
