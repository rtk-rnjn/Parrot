from __future__ import annotations

import re
from typing import Annotated, Any, Optional, Union

from jinja2.sandbox import SandboxedEnvironment

import discord
from core import Cog, Context, Parrot
from discord.ext import commands, tasks

from .variables import Variables


class Environment(SandboxedEnvironment):
    intercepted_binops = frozenset(["//", "%", "**", "<<", ">>", "&", "^", "|"])

    def make_globals(self, *args, **kwargs):
        super().make_globals(*args, **kwargs)
        return {
            **self.globals,
        }

    def call_binop(self, context, operator: str, left, right):
        disabled_operators = ["//", "%", "**", "<<", ">>", "&", "^", "|"]
        if operator in disabled_operators:
            return self.undefined(f"Undefined binary operator: {operator}", name=operator)

        return super().call_binop(context, operator, left, right)


class AutoResponders(Cog):
    def __init__(self, bot: Parrot):
        self.bot = bot
        self.cache = {}
        self.cooldown = commands.CooldownMapping.from_cooldown(5, 5, commands.BucketType.channel)
        self.exceeded_cooldown = commands.CooldownMapping.from_cooldown(5, 10, commands.BucketType.channel)

    @tasks.loop(seconds=300)
    async def check_autoresponders(self) -> None:
        for guild_id, data in self.cache.items():
            await self.update_to_db(guild_id, data)

    async def update_to_db(self, guild_id: int, data: dict) -> None:
        await self.bot.guild_configurations.update_one(
            {"_id": guild_id},
            {"$set": {"autoresponder": data}},
        )

    async def cog_load(self):
        self.check_autoresponders.start()
        async for guild_data in self.bot.guild_configurations.find({"autoresponder": {"$exists": True}}):
            self.cache[guild_data["_id"]] = guild_data["autoresponder"]

    async def cog_unload(self):
        self.check_autoresponders.cancel()

    @commands.group(name="autoresponder", aliases=["ar"], invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def autoresponder(self, ctx: Context) -> None:
        """Autoresponder commands. See `$ar tutorial` for more info.

        You must have Manage Server permission to use this command.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @autoresponder.command(name="tutorial")
    async def autoresponder_tutorial(self, ctx: Context) -> None:
        """Tutorial for autoresponder commands."""
        embed = (
            discord.Embed(
                title="Autoresponder Tutorial",
                description=(
                    "Autoresponders are messages that are sent when a user sends a message that matches a certain pattern. "
                    "For example, you can set up an autoresponder that sends a message when a user says `hello`. "
                    "Autoresponders can be used to create commands, or to send a message when a user says a certain word. "
                ),
            )
            .add_field(
                name="Creating an autoresponder",
                value=(
                    "To create an autoresponder, use the command `$ar add <name> <response>`. "
                    "The name of the autoresponder must be unique. "
                ),
            )
            .add_field(
                name="For make the response more dynamic",
                value=(
                    "You can use Jinja2 template to make the response more dynamic. "
                    "For example, you can use `<@{{ message_author_id }}>` to mention the user who sent the message. "
                    "You can also use `{{ message_author_name }}` to get the name of the user who sent the message. "
                ),
            )
        )
        await ctx.reply(embed=embed)

    @autoresponder.command(name="variables")
    async def autoresponder_variables(self, ctx: Context) -> None:
        """Show variables that can be used in autoresponder response."""
        var = Variables(message=ctx.message, bot=self.bot)
        variables = var.build_base()

        def format_var(v: str) -> str:
            return "{{ " + v + " }}"

        des = ""
        for v, f in variables.items():
            des += f"`{format_var(v):<17}`\n"
        embed = discord.Embed(
            title="Autoresponder Variables",
            description=des,
        )
        await ctx.reply(embed=embed)

    @autoresponder.command(name="ignore")
    async def autoresponder_ignore(self, ctx: Context, name: str, entity: Union[discord.Role, discord.TextChannel]) -> None:
        """Ignore a role or member from an autoresponder."""
        if name not in self.cache[ctx.guild.id]:
            await ctx.reply("An autoresponder with that name does not exist.")
            return

        if isinstance(entity, discord.Role):
            if "ignore_role" not in self.cache[ctx.guild.id][name]:
                self.cache[ctx.guild.id][name]["ignore_role"] = []

            if entity.id in self.cache[ctx.guild.id][name]["ignore_role"]:
                await ctx.reply("That role is already ignored.")
                return

            self.cache[ctx.guild.id][name]["ignore_role"].append(entity.id)
            await ctx.reply(f"Ignored role `{entity.name}` from autoresponder `{name}`.")
        elif isinstance(entity, discord.TextChannel):
            if "ignore_channel" not in self.cache[ctx.guild.id][name]:
                self.cache[ctx.guild.id][name]["ignore_channel"] = []

            if entity.id in self.cache[ctx.guild.id][name]["ignore_channel"]:
                await ctx.reply("That channel is already ignored.")
                return

            self.cache[ctx.guild.id][name]["ignore_channel"].append(entity.id)
            await ctx.reply(f"Ignored channel `{entity.name}` from autoresponder `{name}`.")

    @autoresponder.command(name="add", aliases=["create", "set"])
    async def autoresponder_add(
        self, ctx: Context, name: str, *, res: Annotated[str, Optional[commands.clean_content]] = None
    ) -> None:
        """Add a new autoresponder.

        The name of the autoresponder must be unique.
        """
        if name in self.cache[ctx.guild.id]:
            await ctx.reply("An autoresponder with that name already exists.")
            return

        if not res:
            await ctx.reply("You must provide a response.")
            return

        self.cache[ctx.guild.id][name] = {
            "enabled": True,
            "response": res,
            "ignore_role": [],
            "ignore_channel": [],
        }
        await ctx.reply(f"Added autoresponder `{name}`.")

    @autoresponder.command(
        name="remove",
        aliases=[
            "delete",
            "del",
            "rm",
        ],
    )
    async def autoresponder_remove(self, ctx: Context, name: str) -> None:
        """Remove an autoresponder."""
        if name not in self.cache[ctx.guild.id]:
            await ctx.reply("An autoresponder with that name does not exist.")
            return

        del self.cache[ctx.guild.id][name]
        await ctx.reply(f"Removed autoresponder `{name}`.")

    @autoresponder.command(name="list", aliases=["ls"])
    async def autoresponder_list(self, ctx: Context) -> None:
        """List all autoresponders."""
        if not self.cache[ctx.guild.id]:
            await ctx.reply("There are no autoresponders.")
            return

        embed = discord.Embed(title="Autoresponders")
        embed.description = "".join(f"`{name}`\n" for name in self.cache[ctx.guild.id])
        await ctx.reply(embed=embed)

    @autoresponder.command(name="edit", aliases=["change", "modify"])
    async def autoresponder_edit(
        self, ctx: Context, name: str, *, res: Annotated[str, Optional[commands.clean_content]] = None
    ) -> None:
        """Edit an autoresponder."""
        if name not in self.cache[ctx.guild.id]:
            await ctx.reply("An autoresponder with that name does not exist.")
            return

        if not res:
            await ctx.reply("You must provide a response.")
            return

        self.cache[ctx.guild.id][name] = {
            "enabled": self.cache[ctx.guild.id][name].get("enabled", True),
            "response": res,
            "ignore_role": self.cache[ctx.guild.id][name].get("ignore_role", []),
            "ignore_channel": self.cache[ctx.guild.id][name].get("ignore_channel", []),
        }
        await ctx.reply(f"Edited autoresponder `{name}`.")

    @autoresponder.command(name="info", aliases=["show"])
    async def autoresponder_info(self, ctx: Context, name: str) -> None:
        """Show info about an autoresponder."""
        if name not in self.cache[ctx.guild.id]:
            await ctx.reply("An autoresponder with that name does not exist.")
            return

        embed = discord.Embed(title=name)
        embed.description = self.cache[ctx.guild.id][name]["response"]

        await ctx.reply(embed=embed)

    @autoresponder.command(name="enable", aliases=["on"])
    async def autoresponder_enable(self, ctx: Context, name: str) -> None:
        """Enable an autoresponder."""
        if name not in self.cache[ctx.guild.id]:
            await ctx.reply("An autoresponder with that name does not exist.")
            return

        if self.cache[ctx.guild.id][name].get("enabled"):
            await ctx.reply("That autoresponder is already enabled.")
            return

        self.cache[ctx.guild.id][name]["enabled"] = True
        await ctx.reply(f"Enabled autoresponder `{name}`.")

    @autoresponder.command(name="disable", aliases=["off"])
    async def autoresponder_disable(self, ctx: Context, name: str) -> None:
        """Disable an autoresponder."""
        if name not in self.cache[ctx.guild.id]:
            await ctx.reply("An autoresponder with that name does not exist.")
            return

        if not self.cache[ctx.guild.id][name].get("enabled"):
            await ctx.reply("That autoresponder is already disabled.")
            return

        self.cache[ctx.guild.id][name]["enabled"] = False
        await ctx.reply(f"Disabled autoresponder `{name}`.")

    @autoresponder.before_invoke
    @autoresponder_add.before_invoke
    @autoresponder_remove.before_invoke
    @autoresponder_list.before_invoke
    @autoresponder_edit.before_invoke
    @autoresponder_info.before_invoke
    @autoresponder_enable.before_invoke
    @autoresponder_disable.before_invoke
    async def ensure_cache(self, ctx: Context) -> None:
        if ctx.guild.id not in self.cache:
            self.cache[ctx.guild.id] = self.bot.guild_configurations_cache[ctx.guild.id].get("autoresponder", {})

    @Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot or not self.cache.get(message.guild.id):
            return

        assert isinstance(message.author, discord.Member)

        var = Variables(message=message, bot=self.bot)
        variables = var.build_base()

        for name, data in self.cache[message.guild.id].items():
            if not data.get("enabled"):
                continue

            if message.channel.id in data.get("ignore_channel", []):
                continue

            if any(role.id in data.get("ignore_role", []) for role in message.author.roles):
                continue

            response = data["response"]

            bucket = self.cooldown.get_bucket(message)
            exceeded_bucket = self.exceeded_cooldown.get_bucket(message)
            if exceeded_bucket.update_rate_limit():  # type: ignore
                break

            if retry_after := bucket.update_rate_limit():  # type: ignore
                await message.channel.send(
                    f"Gave up executing autoresponder for `{message.author}` (ID: `{message.author.id}`)\n"
                    f"Reason: Ratelimited. Try again in `{retry_after:.2f}` seconds."
                )
                break

            try:
                name = re.escape(name.strip())

                if re.fullmatch(rf"{name}", message.content, re.IGNORECASE):
                    await message.channel.send(await self.execute_jinja(response, **variables))
                    break
            except re.error:
                if name == message.content:
                    await message.channel.send(await self.execute_jinja(response, **variables))
                    break

    async def execute_jinja(self, response: str, **variables) -> Any:
        if not hasattr(self, "jinja_env"):
            self.jinja_env = Environment(
                enable_async=True, trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=False, autoescape=True
            )

        template = self.jinja_env.from_string(response)
        try:
            return await template.render_async(**variables)
        except Exception as e:
            return f"Gave up executing autoresponder\n" f"Reason: `{e.__class__.__name__}: {e}`"


async def setup(bot: Parrot) -> None:
    await bot.add_cog(AutoResponders(bot))
