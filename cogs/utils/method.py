from __future__ import annotations

import discord

from datetime import datetime
from time import time

from utilities.database import tags, todo, parrot_db, cluster
from utilities.buttons import Confirm, Prompt
from utilities.paginator import ParrotPaginator

from core import Parrot, Context

giveaway = parrot_db["giveaway"]
reacter = cluster["reacter"]

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
    collection = tags[f"{ctx.guild.id}"]
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
    collection = tags[f"{ctx.guild.id}"]
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
    collection = tags[f"{ctx.guild.id}"]
    if tag in IGNORE:
        return await ctx.reply(
            f"{ctx.author.mention} the name `{tag}` is reserved word."
        )
    if _ := await collection.find_one({"id": tag}):
        return await ctx.reply(f"{ctx.author.mention} the name `{tag}` already exists")
    view = Prompt(ctx.author.id)
    msg = await ctx.send(
        f"{ctx.author.mention} do you want to make the tag as NSFW marked channels",
        view=view,
    )
    await view.wait()
    if view.value is None:
        return await msg.reply(
            f"{ctx.author.mention} you did not responds on time. Considering as non NSFW"
        )
    nsfw = bool(view.value)
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
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.delete_one({"id": tag})
            await ctx.reply(f"{ctx.author.mention} tag deleted successfully")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _name_edit(bot: Parrot, ctx: Context, tag, name):
    collection = tags[f"{ctx.guild.id}"]
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
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"id": tag}, {"$set": {"text": text}})
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _claim_owner(bot: Parrot, ctx: Context, tag):
    collection = tags[f"{ctx.guild.id}"]
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
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        view = Confirm(ctx.author.id)
        msg = await ctx.reply(
            f"{ctx.author.mention} are you sure to transfer the tag ownership to **{member}**? This process is irreversible!",
            view=view,
        )
        await view.wait()
        if view.value is None:
            await msg.reply(f"{ctx.author.mention} you did not responds on time")
        elif view.value:
            await collection.update_one({"id": tag}, {"$set": {"owner": member.id}})
            await msg.reply(
                f"{ctx.author.mention} tag ownership successfully transfered to **{member}**"
            )
        else:
            await msg.reply(f"{ctx.author.mention} ok! reverting the process!")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _toggle_nsfw(bot: Parrot, ctx: Context, tag):
    collection = tags[f"{ctx.guild.id}"]
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
    collection = tags[f"{ctx.guild.id}"]
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
    collection = tags[f"{ctx.guild.id}"]
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
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        em = discord.Embed(
            title=f"Tag: {tag}", timestamp=datetime.utcnow(), color=ctx.author.color
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
    collection = todo[f"{ctx.author.id}"]
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
    collection = todo[f"{ctx.author.id}"]
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
    collection = todo[f"{ctx.author.id}"]
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
    collection = todo[f"{ctx.author.id}"]
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
    collection = todo[f"{ctx.author.id}"]
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
    collection = todo[f"{ctx.author.id}"]
    if data := await collection.find_one({"id": name}):
        await ctx.reply(
            f"> **{data['id']}**\n\nDescription: {data['text']}\n\nCreated At: <t:{data['time']}>"
        )
    else:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any TODO list with name `{name}`"
        )


async def _delete_todo(bot: Parrot, ctx: Context, name):
    collection = todo[f"{ctx.author.id}"]
    if _ := await collection.find_one({"id": name}):
        await collection.delete_one({"id": name})
        await ctx.reply(f"{ctx.author.mention} delete `{name}` task")
    else:
        await ctx.reply(
            f"{ctx.author.mention} you don't have any TODO list with name `{name}`"
        )
