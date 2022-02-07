from __future__ import annotations

from core import Cog, Parrot

# from utilities.database import parrot_db

import discord


class EventCustom(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot

    async def on_timer_complete(self, **kw):
        embed = discord.Embed.from_dict(kw.get("embed", {}))
        if kw.get("dm_notify") or kw.get("is_todo"):
            user = self.bot.get_user(kw["messageAuthor"])
            if user:
                try:
                    await user.send(
                        content=f"{user.mention} this is reminder for: **{kw['content']}**\n\n>>> {kw['messageURL']}",
                        embed=embed,
                    )
                except discord.Forbidden:
                    pass  # I don't know whytf user blocks the DM
        else:
            channel = self.bot.get_channel(kw["messageChannel"])
            if channel:
                try:
                    await channel.send(
                        content=f"<@{kw['messageAuthor']}> this is reminder for: **{kw['content']}**\n\n>>> {kw['messageURL']}",
                        embed=embed,
                    )
                except discord.Forbidden:
                    pass

        if kw.get("mod_action"):
            pass


def setup(bot: Parrot):
    bot.add_cog(EventCustom(bot))
