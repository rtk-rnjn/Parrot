from __future__ import annotations

import asyncio
import contextlib
import enum
import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.utils import NoticeLayout

if TYPE_CHECKING:
    from discord.ext.commands import Context

    from core import Bot

_log = logging.getLogger(__name__)

PANEL_TIMEOUT = 300  # seconds of inactivity before the panel switches itself off
MAX_PICK = 10  # users per permit/block selection
USER_LIMITS = (0, 2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 50, 99)  # 0 means unlimited
BITRATES = (32, 64, 96, 128, 256, 384)  # kbps, trimmed to what the server's boost level allows

type Handler = Callable[[discord.Member], Awaitable["NoticeLayout | None"]]

MISSING_PERMS = "Bot is missing a permission for that. Need Manage Channels, Manage Permissions and Move Members."


def owner_overwrite() -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(
        connect=True,
        speak=True,
        view_channel=True,
        manage_channels=True,
        manage_permissions=True,
        move_members=True,
        mute_members=True,
        deafen_members=True,
    )


def guest_overwrite() -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(connect=True, speak=True, view_channel=True)


class Tab(enum.Enum):
    overview = ("Overview", "\N{HOUSE BUILDING}")
    access = ("Access", "\N{KEY}")
    members = ("Members", "\N{BUSTS IN SILHOUETTE}")
    settings = ("Settings", "\N{GEAR}\N{VARIATION SELECTOR-16}")

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def emoji(self) -> str:
        return self.value[1]


class RenameModal(discord.ui.Modal, title="Rename your channel"):
    name = discord.ui.TextInput(label="Channel name", min_length=1, max_length=100)

    def __init__(self, panel: HubPanel) -> None:
        super().__init__(timeout=180)
        self.panel = panel
        self.name.default = panel.channel.name

    async def on_submit(self, interaction: discord.Interaction) -> None:
        value = self.name.value.strip()
        await self.panel.run(interaction, lambda member: self.panel.rename(member, value))


class HubPanel(discord.ui.LayoutView):
    """The owner's control panel for one temporary channel.

    There is one panel per channel (opening it again replaces the old one). Every click re-checks the database,
    so a panel left over from before an ownership transfer stops working for the previous owner on its own.
    """

    def __init__(self, cog: Hub, owner: discord.Member, channel: discord.VoiceChannel) -> None:
        super().__init__(timeout=PANEL_TIMEOUT)
        self.cog = cog
        self.owner = owner
        self.channel = channel
        self.tab = Tab.overview
        self.message: discord.Message | None = None
        self.closed = False
        self.confirm_delete = False
        self._lock = asyncio.Lock()
        self._build()

    @property
    def is_public(self) -> bool:
        return self.channel.overwrites_for(self.channel.guild.default_role).connect is True

    @property
    def is_hidden(self) -> bool:
        return self.channel.overwrites_for(self.channel.guild.default_role).view_channel is False

    async def _reload(self) -> None:
        """Overwrites arrive through the gateway a moment late, so re-read the channel after changing them."""
        try:
            fresh = await self.channel.guild.fetch_channel(self.channel.id)
        except discord.NotFound:
            await self.close("This channel no longer exists.")
            return
        if isinstance(fresh, discord.VoiceChannel):
            self.channel = fresh

    async def refresh(self) -> None:
        if self.closed:
            return
        self._build()
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)

    async def close(self, reason: str) -> None:
        if self.closed:
            return
        self.closed = True
        if self.cog.panels.get(self.channel.id) is self:
            del self.cog.panels[self.channel.id]

        self.clear_items()
        self.add_item(discord.ui.Container(discord.ui.TextDisplay(f"## \N{SPEAKER WITH THREE SOUND WAVES} Channel panel closed\n{reason}"), accent_colour=discord.Colour.dark_grey()))
        if self.message is not None:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=self)
        self.stop()

    async def on_timeout(self) -> None:
        await self.close("The panel timed out. Run the `hub` command again to reopen it.")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        owner_id = await self.cog.db.get_hub_channel_owner_id(guild_id=self.channel.guild.id, channel_id=self.channel.id)
        if owner_id is None:
            await interaction.response.send_message(view=NoticeLayout.warning("This channel no longer exists."), ephemeral=True)
            await self.close("This channel no longer exists.")
            return False
        if interaction.user.id != owner_id:
            await interaction.response.send_message(
                view=NoticeLayout.error(f"Only the channel owner (<@{owner_id}>) can use this panel."), ephemeral=True
            )
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item) -> None:
        _log.exception("Hub panel error on %r", item, exc_info=error)

    async def run(self, interaction: discord.Interaction, handler: Handler) -> None:
        """Run one action at a time; a click that arrives while another is in flight is turned away."""
        if self.closed:
            await interaction.response.send_message(view=NoticeLayout.info("This panel is closed."), ephemeral=True)
            return
        if self._lock.locked():
            await interaction.response.send_message(view=NoticeLayout.info("Still busy with your last change. Give it a second."), ephemeral=True)
            return

        note: NoticeLayout | None = None
        async with self._lock:
            await interaction.response.defer()
            try:
                note = await handler(interaction.user)  # type: ignore[arg-type]
                await self._reload()
            except discord.Forbidden:
                note = NoticeLayout.error(MISSING_PERMS)
            except discord.HTTPException as exc:
                _log.warning("Hub action failed in channel %s: %s", self.channel.id, exc)
                note = NoticeLayout.error("Discord rejected that change.", footer=str(exc)[:200])

        if not self.closed:
            self._build()
            with contextlib.suppress(discord.HTTPException):
                await interaction.edit_original_response(view=self)
        if note is not None:
            await interaction.followup.send(view=note, ephemeral=True)

    def _button(
        self,
        custom_id: str,
        handler: Handler,
        *,
        label: str | None = None,
        emoji: str | None = None,
        style: discord.ButtonStyle = discord.ButtonStyle.secondary,
    ) -> discord.ui.Button:
        button: discord.ui.Button = discord.ui.Button(custom_id=custom_id, label=label, emoji=emoji, style=style)

        async def callback(interaction: discord.Interaction) -> None:
            await self.run(interaction, handler)

        button.callback = callback
        return button

    def _user_select(
        self,
        custom_id: str,
        placeholder: str,
        handler: Callable[[discord.Member, list[discord.Member]], Awaitable[NoticeLayout | None]],
    ) -> discord.ui.ActionRow:
        select: discord.ui.UserSelect = discord.ui.UserSelect(custom_id=custom_id, placeholder=placeholder, min_values=1, max_values=MAX_PICK)

        async def callback(interaction: discord.Interaction) -> None:
            users = [user for user in select.values if isinstance(user, discord.Member)]
            await self.run(interaction, lambda member: handler(member, users))

        select.callback = callback
        return discord.ui.ActionRow(select)

    def _text_select(
        self,
        custom_id: str,
        placeholder: str,
        options: list[discord.SelectOption],
        handler: Callable[[discord.Member, str], Awaitable[NoticeLayout | None]],
    ) -> discord.ui.ActionRow:
        select: discord.ui.Select = discord.ui.Select(custom_id=custom_id, placeholder=placeholder, options=options)

        async def callback(interaction: discord.Interaction) -> None:
            value = select.values[0]
            await self.run(interaction, lambda member: handler(member, value))

        select.callback = callback
        return discord.ui.ActionRow(select)

    def _build(self) -> None:
        self.clear_items()
        builders = {
            Tab.overview: self._overview_tab,
            Tab.access: self._access_tab,
            Tab.members: self._members_tab,
            Tab.settings: self._settings_tab,
        }
        children = [*builders[self.tab](), discord.ui.Separator(), self._tab_row()]
        self.add_item(discord.ui.Container(*children, accent_colour=discord.Colour.blurple()))

    def _tab_row(self) -> discord.ui.ActionRow:
        buttons: list[discord.ui.Button] = []
        for tab in Tab:
            current = tab is self.tab
            button: discord.ui.Button = discord.ui.Button(
                custom_id=f"hub:tab:{tab.name}",
                label=tab.label,
                emoji=tab.emoji,
                style=discord.ButtonStyle.primary if current else discord.ButtonStyle.secondary,
                disabled=current,
            )

            async def callback(interaction: discord.Interaction, tab: Tab = tab) -> None:
                self.tab, self.confirm_delete = tab, False
                self._build()
                await interaction.response.edit_message(view=self)

            button.callback = callback
            buttons.append(button)
        return discord.ui.ActionRow(*buttons)

    def _overview_tab(self) -> list[discord.ui.Item]:
        channel = self.channel
        limit = f"{len(channel.members)}/{channel.user_limit}" if channel.user_limit else f"{len(channel.members)} (no limit)"
        text = "\n".join(
            [
                f"## \N{SPEAKER WITH THREE SOUND WAVES} {discord.utils.escape_markdown(channel.name)}",
                f"Owner: {self.owner.mention}",
                f"Access: {'\N{GLOBE WITH MERIDIANS} Public, anyone can join' if self.is_public else '\N{LOCK} Private, only permitted people can join'}",
                f"Visibility: {'\N{SEE-NO-EVIL MONKEY} Hidden from the channel list' if self.is_hidden else '\N{EYE}\N{VARIATION SELECTOR-16} Visible to everyone'}",
                f"In channel: {limit} \N{MIDDLE DOT} Bitrate: {channel.bitrate // 1000} kbps",
            ]
        )

        async def open_rename(interaction: discord.Interaction) -> None:
            await interaction.response.send_modal(RenameModal(self))

        rename: discord.ui.Button = discord.ui.Button(custom_id="hub:rename", label="Rename", emoji="\N{PENCIL}\N{VARIATION SELECTOR-16}")
        rename.callback = open_rename

        return [
            discord.ui.TextDisplay(text),
            discord.ui.Separator(),
            discord.ui.ActionRow(
                rename,
                self._button(
                    "hub:privacy",
                    self.toggle_public,
                    label="Make private" if self.is_public else "Make public",
                    emoji="\N{LOCK}" if self.is_public else "\N{GLOBE WITH MERIDIANS}",
                ),
                self._button("hub:visibility", self.toggle_hidden, label="Show" if self.is_hidden else "Hide", emoji="\N{EYE}\N{VARIATION SELECTOR-16}" if self.is_hidden else "\N{SEE-NO-EVIL MONKEY}"),
            ),
        ]

    def _access_tab(self) -> list[discord.ui.Item]:
        guests = [t for t in self.channel.overwrites if isinstance(t, discord.Member) and t.id not in (self.owner.id, self.channel.guild.me.id)]
        allowed = [m.display_name for m in guests if self.channel.overwrites_for(m).connect is True]
        blocked = [m.display_name for m in guests if self.channel.overwrites_for(m).connect is False]
        text = "\n".join(
            [
                "## Access",
                f"Permitted: {', '.join(allowed) or 'nobody'}",
                f"Blocked: {', '.join(blocked) or 'nobody'}",
            ]
        )
        return [
            discord.ui.TextDisplay(text),
            discord.ui.TextDisplay("-# Permitted people can join even when the channel is private. Blocking also removes them if they are inside."),
            self._user_select("hub:permit", "Permit people\N{HORIZONTAL ELLIPSIS}", self.permit),
            self._user_select("hub:block", "Block people\N{HORIZONTAL ELLIPSIS}", self.block),
            discord.ui.ActionRow(self._button("hub:reset", self.reset_guests, label="Clear permit and block lists", emoji="\N{BROOM}")),
        ]

    def _members_tab(self) -> list[discord.ui.Item]:
        others = [m for m in self.channel.members if m.id != self.owner.id]
        text = (
            f"## Members\n{self.owner.mention} (owner)" + "".join(f"\n{m.mention}" for m in others)
            if self.channel.members
            else "## Members\nNobody is in the channel."
        )
        children: list[discord.ui.Item] = [discord.ui.TextDisplay(text)]
        if not others:
            return children

        options = [discord.SelectOption(label=m.display_name[:100], value=str(m.id)) for m in others[:25]]
        children.append(self._text_select("hub:kick", "Remove someone from the channel\N{HORIZONTAL ELLIPSIS}", options, self.kick))

        humans = [option for option, member in zip(options, others[:25], strict=True) if not member.bot]
        if humans:
            children.append(self._text_select("hub:transfer", "Give ownership to\N{HORIZONTAL ELLIPSIS}", humans, self.transfer))
        return children

    def _settings_tab(self) -> list[discord.ui.Item]:
        channel = self.channel
        limit_options = [
            discord.SelectOption(label="Unlimited" if value == 0 else f"{value} people", value=str(value), default=value == channel.user_limit)
            for value in USER_LIMITS
        ]
        ceiling = channel.guild.bitrate_limit // 1000
        bitrate_options = [
            discord.SelectOption(label=f"{value} kbps", value=str(value), default=value == channel.bitrate // 1000)
            for value in BITRATES
            if value <= ceiling
        ]

        children: list[discord.ui.Item] = [
            discord.ui.TextDisplay("## Settings"),
            self._text_select("hub:limit", "User limit", limit_options, self.set_limit),
            self._text_select("hub:bitrate", "Audio quality", bitrate_options, self.set_bitrate),
        ]

        if self.confirm_delete:
            children.append(discord.ui.TextDisplay("**Delete this channel for good?**"))
            children.append(
                discord.ui.ActionRow(
                    self._button("hub:delete-yes", self.delete_channel, label="Yes, delete it", emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.danger),
                    self._button("hub:delete-no", self.cancel_delete, label="Cancel"),
                )
            )
        else:
            children.append(
                discord.ui.ActionRow(self._button("hub:delete", self.ask_delete, label="Delete channel", emoji="\N{WASTEBASKET}\N{VARIATION SELECTOR-16}", style=discord.ButtonStyle.danger))
            )
        return children

    async def rename(self, member: discord.Member, name: str) -> NoticeLayout | None:
        self.channel = await self.channel.edit(name=name, reason=f"Renamed by owner {member} ({member.id})") or self.channel
        return NoticeLayout.info("Renamed.", footer="Discord only allows two renames every ten minutes.")

    async def toggle_public(self, member: discord.Member) -> NoticeLayout | None:
        overwrite = self.channel.overwrites_for(self.channel.guild.default_role)
        overwrite.connect = not self.is_public
        await self.channel.set_permissions(self.channel.guild.default_role, overwrite=overwrite, reason=f"Access changed by {member}")
        return None

    async def toggle_hidden(self, member: discord.Member) -> NoticeLayout | None:
        overwrite = self.channel.overwrites_for(self.channel.guild.default_role)
        overwrite.view_channel = bool(self.is_hidden)
        await self.channel.set_permissions(self.channel.guild.default_role, overwrite=overwrite, reason=f"Visibility changed by {member}")
        return None

    async def permit(self, member: discord.Member, users: list[discord.Member]) -> NoticeLayout | None:
        targets = [user for user in users if not user.bot and user.id != self.owner.id]
        for user in targets:
            await self.channel.set_permissions(user, overwrite=guest_overwrite(), reason=f"Permitted by {member}")
        return (
            NoticeLayout.info(f"Permitted {', '.join(u.display_name for u in targets)}.", footer="They can now join the channel.")
            if targets
            else NoticeLayout.warning("Pick people other than yourself and bots.", footer="You cannot permit yourself or bots.")
        )

    async def block(self, member: discord.Member, users: list[discord.Member]) -> NoticeLayout | None:
        targets = [user for user in users if not user.bot and user.id != self.owner.id]
        for user in targets:
            await self.channel.set_permissions(
                user, overwrite=discord.PermissionOverwrite(connect=False, view_channel=False), reason=f"Blocked by {member}"
            )
            if user.voice is not None and user.voice.channel == self.channel:
                await user.move_to(None, reason=f"Blocked by channel owner {member}")
        return (
            NoticeLayout.info(f"Blocked {', '.join(u.display_name for u in targets)}.", footer="They can no longer join the channel.")
            if targets
            else NoticeLayout.warning("Pick people other than yourself and bots.", footer="You cannot block yourself or bots.")
        )

    async def reset_guests(self, member: discord.Member) -> NoticeLayout | None:
        keep = {self.owner.id, self.channel.guild.me.id}
        for target in list(self.channel.overwrites):
            if isinstance(target, discord.Role) or target.id in keep:
                continue
            try:
                await self.channel.set_permissions(target, overwrite=None, reason=f"Lists cleared by {member}")  # type: ignore[arg-type]
            except TypeError:  # an overwrite for someone who left the server cannot be addressed as a member
                _log.debug("Skipping unresolvable overwrite target %s", target.id)
        return None

    async def kick(self, member: discord.Member, value: str) -> NoticeLayout | None:
        target = discord.utils.get(self.channel.members, id=int(value))
        if target is None or target.id == self.owner.id:
            return NoticeLayout.info("They already left.")
        await target.move_to(None, reason=f"Removed by channel owner {member}")
        return None

    async def transfer(self, member: discord.Member, value: str) -> NoticeLayout | None:
        target = discord.utils.get(self.channel.members, id=int(value))
        if target is None or target.bot:
            return NoticeLayout.warning("They need to be in the channel to receive ownership.", footer="You cannot transfer ownership to a bot.")
        await self.cog.transfer_ownership(self.channel, member, target)
        return NoticeLayout.info(
            f"{target.mention} now owns this channel. This panel is theirs now.", footer="The previous owner no longer has control."
        )

    async def set_limit(self, member: discord.Member, value: str) -> NoticeLayout | None:
        self.channel = await self.channel.edit(user_limit=int(value), reason=f"Limit changed by {member}") or self.channel
        return NoticeLayout.info(f"Channel limit set to {value}.")

    async def set_bitrate(self, member: discord.Member, value: str) -> NoticeLayout | None:
        self.channel = await self.channel.edit(bitrate=int(value) * 1000, reason=f"Bitrate changed by {member}") or self.channel
        return None

    async def ask_delete(self, member: discord.Member) -> NoticeLayout | None:
        self.confirm_delete = True
        return NoticeLayout.info("Are you sure you want to delete this channel?")

    async def cancel_delete(self, member: discord.Member) -> NoticeLayout | None:
        self.confirm_delete = False
        return NoticeLayout.info("Deletion cancelled.")

    async def delete_channel(self, member: discord.Member) -> NoticeLayout | None:
        await self.cog.delete_channel(self.channel, reason=f"Deleted by owner {member} ({member.id})")
        await self.close("The channel was deleted.")
        return None


class Hub(commands.Cog):
    """Join-to-create voice channels with an owner control panel."""

    help_emoji = "\N{SPEAKER WITH THREE SOUND WAVES}"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.panels: dict[int, HubPanel] = {}  # channel id -> its open panel
        self._creating: set[int] = set()  # member ids with a channel being created, against duplicate events
        _log.debug("Cog loaded: %s", self.__class__.__name__)

    @property
    def db(self):
        return self.bot.database

    async def cog_unload(self) -> None:
        for panel in list(self.panels.values()):
            await panel.close("The hub system is restarting.")

    @commands.group(name="hub", invoke_without_command=True)
    @commands.guild_only()
    async def hub(self, ctx: Context[Bot]) -> None:
        """Opens the control panel for your temporary voice channel."""
        assert isinstance(ctx.author, discord.Member)  # guild_only

        channel = await self._owned_channel(ctx.author)
        if channel is None:
            await ctx.reply(
                view=NoticeLayout.warning(
                    "You do not own a temporary channel right now.",
                    footer="Join the hub channel to get one. If the owner left yours, use the `claim` subcommand.",
                )
            )
            return

        old = self.panels.get(channel.id)
        if old is not None:
            await old.close("Replaced by a newer panel.")

        panel = HubPanel(self, ctx.author, channel)
        self.panels[channel.id] = panel
        panel.message = await ctx.reply(view=panel, allowed_mentions=discord.AllowedMentions.none())

    @hub.command(name="claim")
    async def claim(self, ctx: Context[Bot]) -> None:
        """Takes ownership of the temporary channel you are in, if its owner is no longer there."""
        if TYPE_CHECKING:
            assert isinstance(ctx.author, discord.Member)
            assert ctx.guild is not None

        channel = ctx.author.voice.channel if ctx.author.voice is not None else None
        if not isinstance(channel, discord.VoiceChannel):
            await ctx.reply(view=NoticeLayout.warning("Join the temporary channel you want to claim first."))
            return

        owner_id = await self.db.get_hub_channel_owner_id(guild_id=ctx.guild.id, channel_id=channel.id)
        if owner_id is None:
            await ctx.reply(view=NoticeLayout.warning("That is not a temporary channel."))
            return
        if owner_id == ctx.author.id:
            await ctx.reply(view=NoticeLayout.info("You already own this channel."))
            return

        owner = ctx.guild.get_member(owner_id)
        if owner is not None and owner in channel.members:
            await ctx.reply(view=NoticeLayout.error(f"{owner.display_name} is still in the channel, so it cannot be claimed."))
            return

        try:
            await self.transfer_ownership(channel, owner, ctx.author)
        except discord.HTTPException:
            _log.exception("Could not transfer channel %s to %s", channel.id, ctx.author.id)
            await ctx.reply(view=NoticeLayout.error(MISSING_PERMS))
            return

        panel = self.panels.get(channel.id)
        if panel is not None:
            await panel.refresh()
        await ctx.reply(view=NoticeLayout.info(f"You now own {channel.mention}. Run the `hub` command to open its panel."))

    async def transfer_ownership(self, channel: discord.VoiceChannel, old_owner: discord.Member | None, new_owner: discord.Member) -> None:
        """Move ownership in the database first (the source of truth), then the permissions to match."""
        await self.db.set_hub_channel_owner_id(guild_id=channel.guild.id, channel_id=channel.id, owner_id=new_owner.id)

        await channel.set_permissions(new_owner, overwrite=owner_overwrite(), reason=f"Ownership transferred to {new_owner}")
        if old_owner is not None:
            await channel.set_permissions(old_owner, overwrite=guest_overwrite(), reason="Ownership transferred away")

        panel = self.panels.get(channel.id)
        if panel is not None:
            panel.owner = new_owner

    async def _owned_channel(self, member: discord.Member) -> discord.VoiceChannel | None:
        """The temporary channel ``member`` owns: the one they are in, else any other. Does not move anyone."""
        guild = member.guild
        current = member.voice.channel if member.voice is not None else None
        if (
            isinstance(current, discord.VoiceChannel)
            and await self.db.get_hub_channel_owner_id(guild_id=guild.id, channel_id=current.id) == member.id
        ):
            return current

        for channel in guild.voice_channels:
            if await self.db.get_hub_channel_owner_id(guild_id=guild.id, channel_id=channel.id) == member.id:
                return channel
        return None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
        if before.channel == after.channel:
            return

        hub_id = await self.db.get_hub_channel_id(guild_id=member.guild.id)
        if hub_id is None:
            return

        if after.channel is not None and after.channel.id == hub_id:
            _log.debug("%s joined the hub in guild %s", member, member.guild.id)
            await self._create_personal_channel(member, after.channel)

        # The hub itself is never deleted. Anyone may join a temporary channel the owner permitted them into;
        # Discord's own permissions decide that, so no extra "keep out" rule is needed here.
        if before.channel is not None and before.channel.id != hub_id:
            await self._delete_if_empty(before.channel)

    async def _create_personal_channel(self, member: discord.Member, hub_channel: discord.VoiceChannel | discord.StageChannel) -> None:
        guild = member.guild
        if member.id in self._creating:
            return

        self._creating.add(member.id)
        try:
            # Returning owners go back to the channel they already have.
            existing = await self._owned_channel(member)
            if existing is not None:
                with contextlib.suppress(discord.HTTPException):
                    await member.move_to(existing, reason="Returning member to their existing temporary channel")
                return

            me = guild.me
            if me is None or not me.guild_permissions.manage_channels:
                _log.warning("Bot does not have Manage Channels in guild %s (%s)", guild.name, guild.id)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True),
                member: owner_overwrite(),
            }
            try:
                channel = await guild.create_voice_channel(
                    name=f"{member.display_name}'s Channel",
                    category=hub_channel.category,
                    overwrites=overwrites,
                    reason=f"Join-to-create channel for {member} ({member.id})",
                )
            except discord.Forbidden, discord.HTTPException:
                _log.exception("Failed to create personal channel for %s in guild %s", member, guild.id)
                return

            await self.db.set_hub_channel_owner_id(guild_id=guild.id, channel_id=channel.id, owner_id=member.id)

            try:
                await member.move_to(channel, reason=f"Moved {member} into their new join-to-create channel")
            except discord.HTTPException:
                _log.exception("Failed to move %s into channel %s", member, channel.id)
                await self._delete_if_empty(channel)  # do not leave an orphan behind
        finally:
            self._creating.discard(member.id)

    async def _delete_if_empty(self, channel: discord.VoiceChannel | discord.StageChannel) -> None:
        if channel.members:
            return

        guild = channel.guild
        if await self.db.get_hub_channel_id(guild_id=guild.id) == channel.id:
            return  # never delete the actual hub

        owner_id = await self.db.get_hub_channel_owner_id(guild_id=guild.id, channel_id=channel.id)
        if owner_id is None:
            return  # not one of ours

        await self.delete_channel(channel, reason=f"Join-to-create channel became empty (owner ID: {owner_id})")

    async def delete_channel(self, channel: discord.VoiceChannel | discord.StageChannel, *, reason: str) -> None:
        """Forget the channel and delete it. The database row goes first so a failed delete cannot leave a ghost."""
        guild = channel.guild
        await self.db.remove_hub_channel_owner_id(guild_id=guild.id, channel_id=channel.id)

        panel = self.panels.get(channel.id)
        if panel is not None:
            await panel.close("The channel was deleted.")

        try:
            await channel.delete(reason=reason)
        except discord.NotFound:
            pass  # already gone
        except discord.HTTPException:
            _log.exception("Failed to delete temporary channel %s in guild %s", channel.id, guild.id)


async def setup(bot: Bot) -> None:
    """Load the Hub cog."""
    await bot.add_cog(Hub(bot))
