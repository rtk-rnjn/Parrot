from __future__ import annotations

from typing import List, Optional

import discord
from core import Context, Parrot

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
    allowed_mentions = discord.AllowedMentions.none()
    if data := await collection.find_one({"tag_id": tag}):
        if not data["nsfw"] and msg_ref is not None or data["nsfw"] and ctx.channel.nsfw and msg_ref is not None:  # type: ignore
            await msg_ref.reply(data["text"], allowed_mentions=allowed_mentions)
        elif not data["nsfw"] or ctx.channel.nsfw:  # type: ignore
            await ctx.send(data["text"], allowed_mentions=allowed_mentions)
        else:
            await ctx.reply(f"{ctx.author.mention} this tag can only be called in NSFW marked channel")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")
    await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$inc": {"count": 1}})


async def _show_raw_tag(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
        first = discord.utils.escape_markdown(data["text"])
        main = discord.utils.escape_mentions(first)
        if data["nsfw"] and ctx.channel.nsfw or not data["nsfw"]:  # type: ignore
            await ctx.safe_send(main, allowed_mentions=discord.AllowedMentions.none())
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
    if _ := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
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
            "guild_id": ctx.guild.id,
            "nsfw": nsfw,
            "created_at": int(discord.utils.utcnow().timestamp()),
        }
    )
    await ctx.reply(f"{ctx.author.mention} tag created successfully")


async def _delete_tag(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
        if data["owner"] == ctx.author.id:
            await collection.delete_one({"tag_id": tag})
            await ctx.reply(f"{ctx.author.mention} tag deleted successfully")
        else:
            await ctx.error(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _name_edit(bot: Parrot, ctx: Context, tag: str, name: str):
    collection = ctx.bot.tags_collection
    if _ := await collection.find_one({"tag_id": name, "guild_id": ctx.guild.id}):
        await ctx.error(f"{ctx.author.mention} that name already exists in the database")
    elif data := await collection.find_one({"tag_id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"tag_id": name}})
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.error(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _text_edit(bot: Parrot, ctx: Context, tag: str, text: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"text": text}})
            await ctx.reply(f"{ctx.author.mention} tag content successfully changed")
        else:
            await ctx.error(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _claim_owner(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
        member = await bot.get_or_fetch_member(ctx.guild, data["owner"])
        if member:
            return await ctx.error(
                f"{ctx.author.mention} you can not claim the tag ownership as the member is still in the server"
            )
        await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"owner": ctx.author.id}})
        await ctx.reply(f"{ctx.author.mention} ownership of tag `{tag}` claimed!")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _transfer_owner(bot: Parrot, ctx: Context, tag: str, member: discord.Member):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
        if data["owner"] != ctx.author.id:
            return await ctx.error(f"{ctx.author.mention} you don't own this tag")
        val = await ctx.prompt(
            f"{ctx.author.mention} are you sure to transfer the tag ownership to **{member}**? This process is irreversible!"
        )
        if val is None:
            await ctx.error(f"{ctx.author.mention} you did not responds on time")
        elif val:
            await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"owner": member.id}})
            await ctx.reply(f"{ctx.author.mention} tag ownership successfully transfered to **{member}**")
        else:
            await ctx.error(f"{ctx.author.mention} ok! reverting the process!")
    else:
        await ctx.error(f"{ctx.author.mention} No tag with named `{tag}`")


async def _toggle_nsfw(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        nsfw = not data["nsfw"]
        await collection.update_one({"tag_id": tag, "guild_id": ctx.guild.id}, {"$set": {"nsfw": nsfw}})
        await ctx.reply(f"{ctx.author.mention} NSFW status of tag named `{tag}` is set to **{nsfw}**")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _show_tag_mine(bot: Parrot, ctx: Context):
    collection = ctx.bot.tags_collection
    entries: List[str] = []

    async for data in collection.find({"owner": ctx.author.id, "guild_id": ctx.guild.id, "tag_id": {"$exists": True}}):
        entries.append(f"{data['_id']}")
    try:
        return await ctx.paginate(entries, module="SimplePages")
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} you don't have any tags registered with your name")


async def _show_all_tags(bot: Parrot, ctx: Context):
    collection = ctx.bot.tags_collection
    entries: List[str] = []
    async for data in collection.find({"guild_id": ctx.guild.id, "tag_id": {"$exists": True}}):
        entries.append(f"{data['tag_id']}")
    try:
        return await ctx.paginate(entries, module="SimplePages")
    except IndexError:
        await ctx.reply(f"{ctx.author.mention} this server don't have any tags")


async def _view_tag(bot: Parrot, ctx: Context, tag: str):
    collection = ctx.bot.tags_collection
    if data := await collection.find_one({"tag_id": tag, "guild_id": ctx.guild.id}):
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
