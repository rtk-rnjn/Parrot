from __future__ import annotations

import discord
from core import Cog, Parrot

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

        self.auto_mod = {}
        # {
        #     guild_id: {
        #         "rule_name": {
        #             "trigger": Trigger,
        #             "condition": Condition,
        #             "action": Action,
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

        self._was_ready = True
        await self.__cache_build()

    async def __cache_build(self):
        for guild in self.bot.guilds:
            await self.ensure_configuration_cache(guild.id)
            await self.ensure_voilations_cache(guild.id)

        for guild_id in self._auto_mod:
            self.auto_mod[guild_id] = {}
            for rule_name, rule_data in self._auto_mod[guild_id].items():
                trigger = Trigger(self.bot, rule_data["trigger"])
                condition = Condition(self.bot, rule_data["condition"])
                action = Action(self.bot, rule_data["action"])

                self.auto_mod[guild_id][rule_name] = {
                    "trigger": trigger,
                    "condition": condition,
                    "action": action,
                }

    async def refresh_cache(self) -> None:
        self._auto_mod = {}
        self.auto_mod = {}
        self._voilations = {}

        await self.__cache_build()

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        data = self.auto_mod.get(message.guild.id)
        if not data:
            return

        for _rule_name, rule_data in data.items():
            trigger = rule_data["trigger"]
            condition = rule_data["condition"]
            if await trigger.check(message=message, member=message.author) and await condition.check(
                message=message,
                member=message.author,
            ):
                action = rule_data["action"]

                await action.execute(message=message)

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild is None:
            return

        data = self.auto_mod.get(member.guild.id)
        if not data:
            return

        for _rule_name, rule_data in data.items():
            trigger = rule_data["trigger"]
            condition = rule_data["condition"]

            if await trigger.check(member=member) and await condition.check(member=member):
                action = rule_data["action"]
                await action.execute(member=member)
