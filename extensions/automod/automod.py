from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timedelta
from functools import partial
from typing import TYPE_CHECKING

import discord
from discord.ext import commands
from discord.utils import MISSING

from core.utils import PaginationView

from .builder import RuleBuilderView
from .condition import first_failed
from .effect.runner import EffectContext, EffectOutcome, EffectStore, Status, run_effects
from .guide import automod_embeds
from .management import ConfirmDeleteView, RuleListView, name_error, notice
from .rule import Rule
from .trigger.checks import TriggerEvent
from .trigger.environment import Environment as TriggerEnv

if TYPE_CHECKING:
    from core import Bot

_log = logging.getLogger(__name__)


class _ViolationManager:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def add_violation(self, guild_id: int, user_id: int, name: str, *, rule_name: str, at: datetime) -> None:
        await self.bot.database.add_violation(
            guild_id=guild_id,
            user_id=user_id,
            violation_name=name,
            issued_at=at,
            issued_by=None,
            expired_at=None,
            metadata={"rule_name": rule_name},
        )

    async def reset_violations(self, guild_id: int, user_id: int, name: str | None) -> int:
        return await self.bot.database.reset_violations(guild_id=guild_id, user_id=user_id, violation_name=name or "default")

    async def mute_member(self, member: discord.Member, *, duration: timedelta | None, reason: str) -> None: ...


class Automod(commands.Cog, name="Auto Moderation"):
    """Automod rule management."""

    help_emoji = "\N{ROBOT FACE}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.rules: dict[int, list[Rule]] = {}

        self.__trigger_environment: TriggerEnv = TriggerEnv(bot=self.bot)

    @commands.group(name="automod", invoke_without_command=True)
    async def automod(self, ctx: commands.Context[Bot]) -> None:
        """Shows the help message for the automod feature."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @automod.command(name="guide", aliases=["help"])
    async def automod_help(self, ctx: commands.Context[Bot]) -> None:
        """Shows the help message for the automod feature."""
        embeds = automod_embeds()
        view = PaginationView(author=ctx.author, items=embeds)
        await view.start(ctx)

    @automod.command(name="add", aliases=["make", "create", "new", "build"])
    @commands.has_permissions(administrator=True)
    async def automod_add(
        self,
        ctx: commands.Context[Bot],
        *,
        name: str = commands.parameter(description="The new rule's name"),
    ) -> None:
        """Build a new automod rule with the interactive rule builder.

        Pick a trigger, optional conditions and the effects to apply, then save. Rule names must be unique in the server.
        """
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        name = name.strip()

        error = await name_error(self, ctx.guild.id, None, name)
        if error is not None:
            raise commands.BadArgument(error)

        view = RuleBuilderView(
            ctx.author,
            name,
            on_save=partial(self.finish_add, ctx.guild.id),
            on_cancel=self.cancel_flow,
            check_name=partial(name_error, self, ctx.guild.id, None),
        )

        view.message = await ctx.reply(view=view)

    @automod.command(name="edit", aliases=["modify", "change", "update"])
    @commands.has_permissions(administrator=True)
    async def automod_edit(self, ctx: commands.Context[Bot], *, name: str = commands.parameter(description="The rule to edit")) -> None:
        """Open an existing rule in the rule builder to change its trigger, conditions, effects, priority or name."""
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        guild_id = ctx.guild.id

        rule = await self._get_rule(guild_id, name)
        if rule is None:
            msg = f"No rule named {discord.utils.escape_markdown(name)!r} exists."
            raise commands.BadArgument(msg)

        view = RuleBuilderView(
            ctx.author,
            rule.name,
            rule=rule,
            on_save=partial(self.finish_edit, guild_id, rule.name),
            on_cancel=self.cancel_flow,
            check_name=partial(name_error, self, guild_id, rule.name),
        )
        view.message = await ctx.reply(view=view)

    @automod.command(name="delete", aliases=["remove", "del", "rm"])
    @commands.has_permissions(administrator=True)
    async def automod_delete(self, ctx: commands.Context[Bot], *, name: str = commands.parameter(description="The rule to delete")) -> None:
        """Delete a rule after a confirmation prompt."""
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        guild_id = ctx.guild.id

        rule = await self._get_rule(guild_id, name)
        if rule is None:
            msg = f"No rule named {discord.utils.escape_markdown(name)!r} exists."
            raise commands.BadArgument(msg)

        view = ConfirmDeleteView(
            ctx.author,
            rule,
            on_confirm=partial(self.finish_delete, guild_id, rule.name),
            on_cancel=self.cancel_flow,
        )

        view.message = await ctx.reply(view=view)

    @automod.command(name="list", aliases=["show", "view", "display", "ls"])
    @commands.has_permissions(administrator=True)
    async def automod_list(self, ctx: commands.Context[Bot]) -> None:
        """Browse the server's automod rules with their status, trigger, conditions and effects."""
        if TYPE_CHECKING:
            assert ctx.guild is not None
            assert isinstance(ctx.author, discord.Member)

        view = await RuleListView.create(ctx.author, self, ctx.guild.id)
        view.message = await ctx.reply(view=view)

    async def finish_add(
        self,
        guild_id: int,
        interaction: discord.Interaction[discord.Client],
        rule: Rule,
    ) -> None:
        await self._add_rule(guild_id, rule)
        await interaction.response.edit_message(view=notice(f"## Saved Rule: {rule.name}", discord.Colour.green()))

    async def finish_edit(
        self,
        guild_id: int,
        original: str,
        interaction: discord.Interaction[discord.Client],
        rule: Rule,
    ) -> None:
        await self._edit_rule(guild_id, original, rule)
        await interaction.response.edit_message(view=notice(f"## Updated Rule: {rule.name}", discord.Colour.green()))

    async def finish_delete(
        self,
        guild_id: int,
        name: str,
        interaction: discord.Interaction[discord.Client],
    ) -> None:
        await self._delete_rule(guild_id, name)
        await interaction.response.edit_message(view=notice(f"## Deleted Rule: {name}", discord.Colour.green()))

    async def cancel_flow(self, interaction: discord.Interaction[discord.Client]) -> None:
        await interaction.response.edit_message(view=notice("## Cancelled.", discord.Colour.red()))

    # Rule

    async def _get_rule(self, guild_id: int, name: str) -> Rule | None:
        rule = await self.bot.database.get_automod_rule(guild_id=guild_id, name=name)
        if rule is None:
            return None
        return Rule.parse(rule)

    async def _add_rule(self, guild_id: int, rule: Rule) -> None:
        await self.bot.database.create_automod_rule(guild_id=guild_id, rule=asdict(rule))  # pyright: ignore[reportArgumentType]

        # internal caching of rules
        if guild_id not in self.rules:
            self.rules[guild_id] = []
        self.rules[guild_id].append(rule)

    async def _edit_rule(self, guild_id: int, original: str, rule: Rule) -> None:
        await self.bot.database.edit_automod_rule(guild_id=guild_id, name=original, **asdict(rule))

        if guild_id in self.rules:
            self.rules[guild_id] = [r for r in self.rules[guild_id] if r.name != original]
        self.rules[guild_id].append(rule)

    async def _delete_rule(self, guild_id: int, name: str) -> None:
        await self.bot.database.delete_automod_rule(guild_id=guild_id, name=name)

        if guild_id in self.rules:
            self.rules[guild_id] = [r for r in self.rules[guild_id] if r.name != name]

    async def _list_rules(self, guild_id: int) -> list[Rule]:
        data = await self.bot.database.get_automod_rules(guild_id)
        rules = [Rule.parse(rule) for rule in data]
        self.rules[guild_id] = rules
        return rules

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None or message.author.id == self.bot.user.id:
            return

        guild_id = message.guild.id
        if guild_id not in self.rules:
            await self._list_rules(guild_id)

        await self.process_automod(guild=message.guild, message=message)

    async def process_automod(self, *, guild: discord.Guild, message: discord.Message = MISSING, member: discord.Member = MISSING) -> None:
        if TYPE_CHECKING:
            assert isinstance(message.author, discord.Member)

        for rule in self.rules[guild.id]:
            if not rule.enabled:
                continue

            if not await rule.trigger.check(message=message, member=member, key=rule.name, env=self.__trigger_environment):
                continue

            _log.info("Rule %r triggered by %r in guild %r", rule.name, message.author.id, guild.id)

            if (
                await first_failed(
                    rule.conditions,
                    message=message,
                    member=message.author,
                )
                is not None
            ):
                continue

            automation_context = EffectContext(
                bot=self.bot,
                store=self.create_effect_store(),
                guild=guild,
                member=message.author,
                rule_name=rule.name,
                trigger_type=rule.trigger.type,
                message=message,
            )

            outcomes = await run_effects(rule.effects, automation_context)
            for outcome in outcomes:
                self._log_effect_outcome(outcome, rule, message, guild.id)

    def _log_effect_outcome(
        self,
        outcome: EffectOutcome,
        rule: Rule,
        message: discord.Message,
        guild_id: int,
    ) -> None:
        log = _log.warning if outcome.status is Status.FAILED else _log.info
        action = {
            Status.FAILED: "failed",
            Status.DONE: "executed",
            Status.SKIPPED: "skipped",
        }[outcome.status]

        detail = f": {outcome.detail}" if outcome.status is not Status.DONE else ""

        log("Effect %r %s for rule %r triggered by %r in guild %r%s", outcome.type.value, action, rule.name, message.author.id, guild_id, detail)

    def create_effect_store(self) -> EffectStore:
        return _ViolationManager(self.bot)

    @commands.Cog.listener()
    async def on_automod_violation(self, member: discord.Member, name: str) -> None:
        for rule in await self.rules_for(member.guild.id, TriggerEvent.VIOLATION):
            if (
                await rule.trigger.check(member=member, env=self.__trigger_environment, key=rule.name)
                and await first_failed(rule.conditions, member=member) is None
            ):
                ctx = EffectContext(
                    bot=self.bot,
                    store=self.create_effect_store(),
                    guild=member.guild,
                    member=member,
                    rule_name=rule.name,
                    trigger_type=rule.trigger.type,
                )
                await run_effects(rule.effects, ctx)

    async def rules_for(self, guild_id: int, event: TriggerEvent) -> list[Rule]:
        if guild_id not in self.rules:
            await self._list_rules(guild_id)

        return [rule for rule in self.rules[guild_id] if rule.trigger.event == event]
