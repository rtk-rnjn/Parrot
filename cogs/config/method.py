from __future__ import annotations

from typing import Any, Dict, Optional, Union


import discord
from core import Context, Parrot


async def _enable(
    bot: Parrot,
    ctx: Context,
    cmd_cog: str,
    target: Union[discord.abc.Messageable, discord.Object],
    force: Optional[bool] = None,
) -> None:
    if not target:
        if force:
            await ctx.bot.guild_configurations.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {
                    "$set": {
                        "cmd_config.$.cmd_enable": False,
                        "cmd_config.$.channel_out": [],
                    }
                },
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable **server** wide, forcely"
            )
        else:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {"$set": {"cmd_config.$.cmd_enable": False}},
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable **server** wide"
            )
    elif isinstance(target, discord.abc.Messageable):
        if force:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {
                    "$pull": {"cmd_config.$.channel_out": target.id},
                    "$addToSet": {"cmd_config.$.channel_in": target.id},
                },
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable in {target.mention}, forcely"
            )
        else:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {"$pull": {"cmd_config.$.channel_out": target.id}},
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable in {target.mention}"
            )
    elif isinstance(target, discord.Role):
        if force:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {
                    "$pull": {"cmd_config.$.role_out": target.id},
                    "$addToSet": {"cmd_config.$.role_in": target.id},
                },
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now enable for **{target.name} ({target.id})**, forcely"
            )
        else:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {"$pull": {"cmd_config.$.role_out": target.id}},
                upsert=True,
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
    if not target:
        if force:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {
                    "$set": {
                        "cmd_config.$.cmd_enable": True,
                        "cmd_config.$.channel_in": [],
                    }
                },
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled **server** wide, forcely"
            )
        else:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {"$set": {"cmd_config.$.cmd_enable": True}},
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled **server** wide"
            )
    elif isinstance(target, discord.abc.Messageable):
        if force:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {
                    "$pull": {"cmd_config.$.channel_in": target.id},
                    "$addToSet": {"cmd_config.$.channel_out": target.id},
                },
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled in {target.mention}, forcely"
            )
        else:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {"$addToSet": {"cmd_config.$.channel_out": target.id}},
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled in {target.mention}"
            )
    elif isinstance(target, discord.Role):
        if force:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {
                    "$pull": {"cmd_config.$.role_in": target.id},
                    "$addToSet": {"cmd_config.$.role_out": target.id},
                },
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled for **{target.name} ({target.id})**, forcely"
            )
        else:
            await ctx.guild_collection.update_one(
                {"_id": ctx.guild.id, "cmd_config.cmd_name": cmd_cog},
                {"$addToSet": {"cmd_config.$.role_out": target.id}},
                upsert=True,
            )
            await ctx.send(
                f"{ctx.author.mention} **{cmd_cog}** {'commands are' if cmd_cog == 'all' else 'is'} now disabled in **{target.name} ({target.id})**"
            )
