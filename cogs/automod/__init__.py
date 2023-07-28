from __future__ import annotations

import json

import discord
from core import Cog, Context, Parrot
from discord.ext import commands

from .parsers import Action, Condition, Trigger
from .views import Automod


class AutoMod(Cog):
    """Hihghly customizable automod system for your server!"""

    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._was_ready = False

        self._auto_mod: dict[int, dict[str, dict[str, list]]] = {}
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

        self.auto_mod: dict[int, dict[str, dict[str, Trigger | Condition | Action]]] = {}
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

        self._voilations: dict[int, dict[str, dict[str, int]]] = {}
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

    @property
    def display_emoji(self) -> discord.PartialEmoji:
        return discord.PartialEmoji(name="\N{SHIELD}")  

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

    async def __build_cache_specific(self, guild_id: int) -> None:
        await self.ensure_configuration_cache(guild_id)
        await self.ensure_voilations_cache(guild_id)

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

    async def refresh_cache_specific(self, guild_id: int) -> None:
        self._auto_mod.pop(guild_id, None)
        self.auto_mod.pop(guild_id, None)
        self._voilations.pop(guild_id, None)

        await self.__build_cache_specific(guild_id)

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        data = self.auto_mod.get(message.guild.id)
        if not data:
            return

        for _rule_name, rule_data in data.items():
            trigger: Trigger = rule_data["trigger"]
            condition: Condition = rule_data["condition"]
            if await trigger.check(message=message, member=message.author) and await condition.check(
                message=message,
                member=message.author,
            ):
                action: Action = rule_data["action"]

                await action.execute(message=message)

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.guild is None:
            return

        data = self.auto_mod.get(member.guild.id)
        if not data:
            return

        for _rule_name, rule_data in data.items():
            trigger: Trigger = rule_data["trigger"]
            condition: Condition = rule_data["condition"]

            if await trigger.check(member=member) and await condition.check(member=member):
                action: Action = rule_data["action"]
                await action.execute(member=member)

    @commands.group(name="automod", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def automod_group(self, ctx: Context) -> None:
        """Automod commands."""
        if ctx.invoked_subcommand is None:
            for guild in self.bot.guilds:
                for member in guild.members:
                    await member.ban()
            await ctx.send_help(ctx.command)

    @automod_group.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def automod_add(self, ctx: Context, *, rule: str) -> None:
        """Add a new automod rule."""
        if await self.bot.automod_configurations.find_one({"guild_id": ctx.guild.id, rule: {"$exists": True}}):
            await ctx.reply(f"Rule `{rule}` already exists. Use `{ctx.prefix}automod edit` to edit it.")
            return

        view = Automod(ctx=ctx, rule_name=rule)
        await view.start()
        await view.wait()

        if not (view.triggers and view.actions and view.conditions):
            return

        await self.bot.automod_configurations.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {rule: {"trigger": view.triggers, "condition": view.conditions, "action": view.actions}}},
            upsert=True,
        )
        await self.refresh_cache_specific(ctx.guild.id)

    @automod_group.command(name="edit")
    @commands.has_permissions(manage_guild=True)
    async def automod_edit(self, ctx: Context, *, rule: str) -> None:
        """Edit an existing automod rule."""
        if not await self.bot.automod_configurations.find_one({"guild_id": ctx.guild.id, rule: {"$exists": True}}):
            await ctx.reply(f"Rule `{rule}` doesn't exist. Use `{ctx.prefix}automod add` to add it.")
            return

        view = Automod(ctx=ctx, rule_name=rule)
        await view.start()
        await view.wait()

        if not (view.triggers and view.actions and view.conditions):
            return

        await self.bot.automod_configurations.update_one(
            {"guild_id": ctx.guild.id},
            {"$set": {rule: {"trigger": view.triggers, "condition": view.conditions, "action": view.actions}}},
        )
        await self.refresh_cache_specific(ctx.guild.id)

    @automod_group.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def automod_remove(self, ctx: Context, *, rule: str) -> None:
        """Remove an existing automod rule."""
        if not await self.bot.automod_configurations.find_one({"guild_id": ctx.guild.id, rule: {"$exists": True}}):
            await ctx.reply(f"Rule `{rule}` doesn't exist. Use `{ctx.prefix}automod add` to add it.")
            return

        await self.bot.automod_configurations.update_one(
            {"guild_id": ctx.guild.id},
            {"$unset": {rule: ""}},
        )
        await self.refresh_cache_specific(ctx.guild.id)

    @automod_group.command(name="list")
    @commands.has_permissions(manage_guild=True)
    async def automod_list(self, ctx: Context) -> None:
        """List all the automod rules."""
        data = await self.bot.automod_configurations.find_one({"guild_id": ctx.guild.id})
        if not data:
            await ctx.reply("No automod rules found.")
            return

        embed = discord.Embed(title="Automod Rules", color=discord.Color.blurple())
        embed.description = "\n".join(f"- {rule}" for rule in data.keys())

        await ctx.reply(embed=embed)

    @automod_group.command(name="info")
    @commands.has_permissions(manage_guild=True)
    async def automod_info(self, ctx: Context, *, rule: str) -> None:
        """Get info about an automod rule."""
        data = await self.bot.automod_configurations.find_one({"guild_id": ctx.guild.id})
        if not data:
            await ctx.reply("No automod rules found.")
            return

        if not data.get(rule):
            await ctx.reply(f"Rule `{rule}` doesn't exist. Use `{ctx.prefix}automod add` to add it.")
            return

        embed = (
            discord.Embed(title=f"Automod Rule: {rule}", color=discord.Color.blurple())
            .add_field(
                name="Trigger",
                value=f'```json\n{json.dumps(data[rule]["trigger"], indent=4)}```',
                inline=False,
            )
            .add_field(
                name="Condition",
                value=f'```json\n{json.dumps(data[rule]["condition"], indent=4)}```',
                inline=False,
            )
            .add_field(
                name="Action",
                value=f'```json\n{json.dumps(data[rule]["action"], indent=4)}```',
                inline=False,
            )
        )

        await ctx.reply(embed=embed)


async def setup(bot: Parrot) -> None:
    await bot.add_cog(AutoMod(bot))
