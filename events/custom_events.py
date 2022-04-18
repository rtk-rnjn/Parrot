from __future__ import annotations
from cogs.cc.method import CustomCommandsExecutionOngTimer

from core import Cog, Parrot

from cogs.utils.method import end_giveaway

import discord


class EventCustom(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot

    async def on_timer_complete(self, **kw) -> None:
        await self.bot.wait_until_ready()
        if kw.get("mod_action"):
            await self.mod_action_parser(**kw.get("mod_action"))

        if kw.get("embed"):
            embed = discord.Embed.from_dict(kw.get("embed"))
        else:
            embed = None

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
                    # bot is not having permissions to send messages
                    pass

        if kw.get("extra"):
            data = kw.get("extra")
            await self.extra_action_parser(data.get("name"), **data.get("main"))

    async def mod_action_parser(self, **kw) -> None:
        action: str = kw.get("action")
        guild = self.bot.get_guild(kw.get("guild"))
        if guild is None:
            return
        target: int = kw.get("member") or kw.get("target")

        if action.upper() == "UNBAN":
            try:
                await guild.unban(discord.Object(target), reason=kw.get("reason"))
            except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                # User not found, Bot Not having permissions, Other HTTP Error
                pass

        if action.upper() == "BAN":
            try:
                await guild.ban(discord.Object(target), reason=kw.get("reason"))
            except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                # User not found, Bot Not having permissions, Other HTTP Error
                pass

    async def extra_action_parser(self, name, **kw) -> None:
        if name.upper() == "REMOVE_AFK":
            await self.bot.mongo.parrot_db.afk.delete_one(kw)
            self.bot.afk.remove(kw.get("messageAuthor"))

        if name.upper() == "SET_AFK":
            await self.bot.mongo.parrot_db.afk.insert_one(kw)
            self.bot.afk.add(kw.get("messageAuthor"))

        if name.upper() == "SET_TIMER":
            await self.bot.mongo.parrot_db.timers.insert_one(kw)

        if name.upper() == "GIVEAWAY_END":
            await self._parse_giveaway(**kw)

    async def _parse_command_execution(self, **kw):
        guild_id = kw['__guild_id__']
        if data := await self.bot.mongo.cc.commands.find_one(
            {
                "$or": [
                    {
                        "_id": guild_id,
                        "commands.trigger_type": "timer_complete",
                        "commands.review_needed": False,
                    },
                    {
                        "_id": guild_id,
                        "commands.trigger_type": "timer_complete",
                        "commands.review_needed": False,
                    },
                ]
            }
        ):
            commands = data.get("commands", [])
            for command in commands:
                if (
                    command["trigger_type"]
                    in {"timer_complete", "timer_complete"}
                    and not command["review_needed"]
                ):
                    cc = CustomCommandsExecutionOngTimer(self.bot, self.bot.get_guild(guild_id), **kw)
                    await cc.execute(command.get_code)

    async def _parse_giveaway(self, **kw) -> None:
        data = await self.bot.mongo.parrot_db.giveaway.find_one(
            {
                "message_id": kw.get("message_id"),
                "guild_id": kw.get("guild_id"),
                "status": "ONGOING",
            }
        )
        member_ids = await end_giveaway(self.bot, **data)
        channel = await self.bot.getch(
            self.bot.get_channel, self.bot.fetch_channel, kw.get("giveaway_channel")
        )
        await self.bot.mongo.parrot_db.giveaway.find_one_and_update(
            {"message_id": kw.get("message_id"), "status": "ONGOING"},
            {"$set": {"status": "END"}},
        )
        msg_link = f"https://discord.com/channels/{kw.get('guild_id')}/{kw.get('giveaway_channel')}/{kw.get('message_id')}"
        if not member_ids:
            return await channel.send(f"No winners!\n> {msg_link}")

        joiner = ">, <@".join([str(i) for i in member_ids])

        await channel.send(
            f"Congrats <@{joiner}> you won {kw.get('prize')}\n" f"> {msg_link}"
        )


async def setup(bot: Parrot) -> None:
    await bot.add_cog(EventCustom(bot))
