from __future__ import annotations

import discord, typing

from datetime import datetime
from time import time

from utilities.database import tags
from utilities.buttons import Confirm, Prompt


async def _show_tag(bot, ctx, tag, msg_ref=None):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if not data['nsfw']:
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
                await ctx.reply(f"{ctx.author.mention} this tag can only be called in NSFW marked channel")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")
    await collection.update_one({"id": tag}, {"$inc": {"count": 1}})


async def _create_tag(bot, ctx, tag, text):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        return await ctx.reply(f"{ctx.author.mention} the name `{tag}` already exists")
    else:
        view = Prompt(ctx.author.id)
        await ctx.send(f"{ctx.author.mention} do you want to make the tag as NSFW marked channels", view=view)
        await view.wait()
        if view.value is None:
            await msg.reply(f"{ctx.author.mention} you did not responds on time. Considering as non NSFW")
            nsfw = False
        elif view.value:
            nsfw = True
        else:
            nsfw = False
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


async def _delete_tag(bot, ctx, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.delete_one({"id": tags})
            await ctx.reply(f"{ctx.author.mention} tag deleted successfully")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _name_edit(bot, ctx, tag, name):
    collection = tags[f"{ctx.guild.id}"]
    if exists := await collection.find_one({"id": name}):
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


async def _text_edit(bot, ctx, tag, text):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        if data["owner"] == ctx.author.id:
            await collection.update_one({"id": tag}, {"$set": {"text": text}})
            await ctx.reply(f"{ctx.author.mention} tag name successfully changed")
        else:
            await ctx.reply(f"{ctx.author.mention} you don't own this tag")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _claim_owner(bot, ctx, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        member = ctx.guild.get_member(data["owner"])
        if member:
            return await ctx.reply(
                f"{ctx.author.mention} you can not claim the tag ownership as the member is still in the server"
            )
        await collection.update_one({"id": tag}, {"$set": {"owner": ctx.author.id}})
        await ctx.reply(f"{ctx.author.mention} ownership of tag `{tag}` claimed!")
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _transfer_owner(bot, ctx, tag, member):
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


async def _toggle_nsfw(bot, ctx, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({'id': tag}):
        if data["owner"] != ctx.author.id:
            return await ctx.reply(f"{ctx.author.mention} you don't own this tag")
        nsfw = not data['nsfw']
        await collection.update_one({'id': tag}, {'$set': {'nsfw': nsfw}})
        await ctx.reply(
            f"{ctx.author.mention} NSFW status of tag named `{tag}` is set to **{nsfw}**"
          )
    else:
        await ctx.reply(f"{ctx.author.mention} No tag with named `{tag}`")


async def _view_tag(bot, ctx, tag):
    collection = tags[f"{ctx.guild.id}"]
    if data := await collection.find_one({"id": tag}):
        em = discord.Embed(
            title=f"Tag: {tag}", timestamp=datetime.utcnow(), color=ctx.author.color
        )
        text_len = len(data["text"])
        owner = ctx.guild.get_member(data["owner"])
        nsfw = data["nsfw"]
        count = data["count"]
        created_at = f"<t:{data['created_at']}>"
        claimable = True if owner is None else False
        em.add_field(name="Owner", value=f"**{owner.mention if owner else None}** ")
        em.add_field(name="Created At?", value=created_at)
        em.add_field(name="Text Length", value=str(text_len))
        em.add_field(name="Is NSFW?", value=nsfw)
        em.add_field(name="Tag Used", value=count)
        em.add_field(name="Can Claim?", value=claimable)
        em.set_footer(text=f"{ctx.author}")
        await ctx.reply(embed=em)
