from __future__ import annotations

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

from .parsers import Action, Condition, Trigger


class AutoMod(Cog):
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._was_ready = False

        self._auto_mod = {}
        # {
        #     guild_id: {
        #         "rule_name": {
        #             "trigger": [],
        #             "condition": [],
        #             "action": [],
        #        }
        #     },
        #     ...
        # }

        self._voilations = {}
        # {
        #     guild_id: {
        #         "u_{user_id}": {
        #             "global": 0,
        #             "{voilation_name}": 0,
        #         }
        #     },
        #     ...
        # }

        self._auto_mod_logs = {}

    async def ensure_configuration_cache(self, guild_id: int) -> None:
        data = await self.bot.automod_configurations.find_one({"guild_id": guild_id})
        if not data:
            return

        """
        # DB Structure
        {
            "_id": ObjectId(""),
            "guild_id": 1234567890,
            "{rule_name}": {
                "trigger": [],
                "condition": [],
                "action": [],
            },
            ...
        }
        """

        data.pop("_id")
        guild_id = data.pop("guild_id")

        self._auto_mod[guild_id] = data

    async def ensure_voilations_cache(self, guild_id: int) -> None:
        data = await self.bot.automod_voilations.find_one({"guild_id": guild_id})
        if not data:
            return

        """
        # DB Structure
        {
            "_id": ObjectId(""),
            "guild_id": 1234567890,
            "u_{user_id}": {
                "global": 0,
                "{voilation_name}": 0,
            },
            ...
        }
        """

        data.pop("_id")
        guild_id = data.pop("guild_id")

        self._voilations[guild_id] = data

    @Cog.listener()
    async def on_ready(self) -> None:
        if self._was_ready:
            return

        for guild in self.bot.guilds:
            await self.ensure_configuration_cache(guild.id)
            await self.ensure_voilations_cache(guild.id)

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        data = self._auto_mod.get(message.guild.id)
        if not data:
            return

        for rule_name, rule_data in data.items():
            trigger = Trigger(self.bot, rule_data["trigger"])
            condition = Condition(self.bot, rule_data["condition"])
            action = Action(self.bot, rule_data["action"])

            if await trigger.check(message=message, member=message.author) and await condition.check(
                message=message, member=message.author
            ):
                await action.execute(message=message)

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild is None:
            return

        data = self._auto_mod.get(member.guild.id)
        if not data:
            return

        for rule_name, rule_data in data.items():
            trigger = Trigger(self.bot, rule_data["trigger"])
            condition = Condition(self.bot, rule_data["condition"])
            action = Action(self.bot, rule_data["action"])

            if await trigger.check(member=member) and await condition.check(member=member):
                await action.execute(member=member)