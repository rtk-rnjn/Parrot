from __future__ import annotations

from core import Cog, Parrot

from utilities.database import parrot_db

import discord

afk = parrot_db["afk"]


class EventCustom(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    async def on_timer_complete(self, **kw):
        if kw.get("mod_action"):
            return await self.mod_action_parser(**kw.get("mod_action"))
        if kw.get("extra"):
            data = kw.get("extra")
            await self.extra_action_parser(data["name"], **data["main"])
        embed = discord.Embed.from_dict(kw.get("embed") or {})
        if (kw.get("dm_notify") or kw.get("is_todo")) and kw.get("content"):
            user = self.bot.get_user(kw["messageAuthor"])
            if user:
                try:
                    await user.send(
                        content=f"{user.mention} this is reminder for: **{kw['content']}**\n>>> {kw['messageURL']}",
                        embed=embed,
                    )
                except discord.Forbidden:
                    pass  # I don't know whytf user blocks the DM
        elif kw.get("content"):
            channel = self.bot.get_channel(kw["messageChannel"])
            if channel:
                try:
                    await channel.send(
                        content=f"<@{kw['messageAuthor']}> this is reminder for: **{kw['content']}**\n>>> {kw['messageURL']}",
                        embed=embed,
                    )
                except discord.Forbidden:
                    pass

    async def mod_action_parser(self, **kw):
        action: str = kw.get("action")
        guild = self.bot.get_guild(kw.get("guild"))
        if guild is None:
            return
        target: int = kw.get("member") or kw.get("target")

        if action.upper() == "UNBAN":
            try:
                await guild.unban(discord.Object(target), reason=kw.get("reason"))
            except (discord.NotFound, discord.HTTPError, discord.Forbidden):
                pass

    async def extra_action_parser(self, name, **kw):
        if name.upper() == "REMOVE_AFK":
            await afk.delete_one({"_id": kw.get("_id")})


def setup(bot: Parrot):
    bot.add_cog(EventCustom(bot))
