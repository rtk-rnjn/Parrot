from __future__ import annotations

from core import Cog, Parrot

# from utilities.database import parrot_db

import discord


class EventCustom(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    async def on_timer_complete(self, **kw):
        if kw.get("mod_action"):
            return await self.mod_action_parser(**kw.get("mod_action"))
        embed = discord.Embed.from_dict(kw.get("embed") or {})
        if kw.get("dm_notify") or kw.get("is_todo"):
            user = self.bot.get_user(kw["messageAuthor"])
            if user:
                try:
                    await user.send(
                        content=f"{user.mention} this is reminder for: **{kw['content']}**\n>>> {kw['messageURL']}",
                        embed=embed,
                    )
                except discord.Forbidden:
                    pass  # I don't know whytf user blocks the DM
        else:
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


def setup(bot: Parrot):
    bot.add_cog(EventCustom(bot))
