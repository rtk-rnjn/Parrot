from __future__ import annotations

import discord
from core import Parrot, Context
from typing import Union, Optional


async def _enable(
    bot: Parrot,
    ctx: Context,
    cmd_cog: str,
    target: Union[discord.abc.Messageable, discord.Object],
    force: Optional[bool] = None,
) -> None:
    collection = bot.mongo.enable_disable[f"{ctx.guild.id}"]
    data = await collection.find_one({"_id": cmd_cog})
    if not data:
        await collection.insert_one(
            {
                "_id": cmd_cog,
                "channel_in": [],
                "channel_out": [],
                "role_in": [],
                "role_out": [],
                "server": False,
            }
        )
    if not target:
        if force:
            await collection.update_one(
                {"_id": cmd_cog}, {"$set": {"server": False, "channel_out": []}}
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable **server** wide, forcely"
            )
        else:
            await collection.update_one({"_id": cmd_cog}, {"$set": {"server": False}})
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable **server** wide"
            )
    elif isinstance(target, discord.abc.Messageable):
        if force:
            await collection.update_one(
                {"_id": cmd_cog},
                {
                    "$pull": {"channel_out": target.id},
                    "$addToSet": {"channel_in": target.id},
                },
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable in {target.mention}, forcely"
            )
        else:
            await collection.update_one(
                {"_id": cmd_cog}, {"$pull": {"channel_out": target.id}}
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable in {target.mention}"
            )
    elif isinstance(target, discord.Role):
        if force:
            await collection.update_one(
                {"_id": cmd_cog},
                {"$pull": {"role_out": target.id}, "$addToSet": {"role_in": target.id}},
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable for **{target.name} ({target.id})**, forcely"
            )
        else:
            await collection.update_one(
                {"_id": cmd_cog}, {"$pull": {"role_out": target.id}}
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable in **{target.name} ({target.id})**"
            )


async def _disable(
    bot: Parrot,
    ctx: Context,
    cmd_cog: str,
    target: Union[discord.abc.Messageable, discord.Object],
    force: Optional[bool] = None,
) -> None:
    collection = bot.mongo.enable_disable[f"{ctx.guild.id}"]
    data = await collection.find_one({"_id": cmd_cog})
    if not data:
        await collection.insert_one(
            {
                "_id": cmd_cog,
                "channel_in": [],
                "channel_out": [],
                "role_in": [],
                "role_out": [],
                "server": False,
            }
        )
    if not target:
        if force:
            await collection.update_one(
                {"_id": cmd_cog}, {"$set": {"server": True, "channel_in": []}}
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled **server** wide, forcely"
            )
        else:
            await collection.update_one({"_id": cmd_cog}, {"$set": {"server": True}})
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled **server** wide"
            )
    elif isinstance(target, discord.abc.Messageable):
        if force:
            await collection.update_one(
                {"_id": cmd_cog},
                {
                    "$pull": {"channel_in": target.id},
                    "$addToSet": {"channel_out": target.id},
                },
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled in {target.mention}, forcely"
            )
        else:
            await collection.update_one(
                {"_id": cmd_cog}, {"$addToSet": {"channel_out": target.id}}
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled in {target.mention}"
            )
    elif isinstance(target, discord.Role):
        if force:
            await collection.update_one(
                {"_id": cmd_cog},
                {"$pull": {"role_in": target.id}, "$addToSet": {"role_out": target.id}},
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled for **{target.name} ({target.id})**, forcely"
            )
        else:
            await collection.update_one(
                {"_id": cmd_cog}, {"$addToSet": {"role_out": target.id}}
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled in **{target.name} ({target.id})**"
            )
