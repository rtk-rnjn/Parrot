from __future__ import annotations

import discord

from .base import NOT_SET, Interaction, NoticeLevel, Page, PageModal, channel_text, role_text, role_warning, status_text

__all__ = ("LevelingPage",)

MIN_LEVEL = 1
MAX_LEVEL = 1000
MAX_LISTED_REWARDS = 15
MAX_SELECT_OPTIONS = 25


class AddRewardModal(PageModal):
    def __init__(self, page: LevelingPage) -> None:
        super().__init__(page, title="Add a level reward")
        self.level_input = discord.ui.TextInput(placeholder="5", min_length=1, max_length=len(str(MAX_LEVEL)))
        self.role_select = discord.ui.RoleSelect(placeholder="Pick the role to give\N{HORIZONTAL ELLIPSIS}", min_values=1, max_values=1)
        self.add_item(discord.ui.Label(text="Level", description=f"Between {MIN_LEVEL} and {MAX_LEVEL}.", component=self.level_input))
        self.add_item(discord.ui.Label(text="Role", description="Given when a member reaches that level.", component=self.role_select))

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            level = int(self.level_input.value.strip())
        except ValueError:
            level = 0
        if not MIN_LEVEL <= level <= MAX_LEVEL:
            await self.page.commit(interaction, f"The level must be a whole number between {MIN_LEVEL} and {MAX_LEVEL}.", level=NoticeLevel.ERROR)
            return

        role = self.role_select.values[0]
        await self.page.db.set_level_role(guild_id=self.page.guild.id, level=level, role_id=role.id)

        warning = role_warning(self.page.guild, role)
        if warning:
            await self.page.commit(interaction, f"Reward saved, but {warning}", level=NoticeLevel.WARNING)
        else:
            await self.page.commit(interaction, f"Members reaching level {level} will receive {role.mention}.")


class RemoveRewardsModal(PageModal):
    def __init__(self, page: LevelingPage) -> None:
        super().__init__(page, title="Remove level rewards")
        rewards = list(page.level_roles.items())[:MAX_SELECT_OPTIONS]
        options = [
            discord.SelectOption(
                label=f"Level {level}",
                value=str(level),
                description=_role_name(page.guild, role_id),
            )
            for level, role_id in rewards
        ]
        self.levels_select = discord.ui.Select(
            placeholder="Choose the rewards to remove\N{HORIZONTAL ELLIPSIS}", options=options, min_values=1, max_values=len(options)
        )
        self.add_item(
            discord.ui.Label(
                text="Rewards",
                description="Removing a reward does not take the role away from members who already have it.",
                component=self.levels_select,
            )
        )

    async def on_submit(self, interaction: Interaction) -> None:
        levels = sorted(int(value) for value in self.levels_select.values)
        for level in levels:
            await self.page.db.remove_level_role(guild_id=self.page.guild.id, level=level)
        listed = ", ".join(str(level) for level in levels)
        await self.page.commit(interaction, f"Removed the reward{'' if len(levels) == 1 else 's'} for level {listed}.")


def _role_name(guild: discord.Guild, role_id: int) -> str:
    role = guild.get_role(role_id)
    return f"@{role.name}" if role is not None else "deleted role"


class LevelingPage(Page):
    key = "leveling"
    label = "Leveling"
    emoji = "\N{CHART WITH UPWARDS TREND}"
    description = "Members earn XP by chatting. Announce level-ups and hand out roles at milestones."
    section = "leveling_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["leveling_config"].get("enabled"))

    @property
    def channel_id(self) -> int | None:
        return self.config["leveling_config"].get("channel_id")

    @property
    def level_roles(self) -> dict[int, int]:
        raw = self.config["leveling_config"].get("level_roles") or {}
        return dict(sorted((int(level), int(role_id)) for level, role_id in raw.items() if role_id))

    def summary(self) -> str:
        count = len(self.level_roles)
        return f"{status_text(self.enabled)} \N{MIDDLE DOT} {count} reward role{'' if count == 1 else 's'}"

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def reset_summary(self) -> str:
        return "the leveling toggle, announcement channel and every reward role (member XP is kept)"

    def _rewards_text(self) -> str:
        rewards = self.level_roles
        if not rewards:
            return NOT_SET
        lines = [
            f"Level {level} \N{RIGHTWARDS ARROW} {role_text(self.guild, role_id)}" for level, role_id in list(rewards.items())[:MAX_LISTED_REWARDS]
        ]
        hidden = len(rewards) - MAX_LISTED_REWARDS
        if hidden > 0:
            lines.append(f"-# and {hidden} more")
        return "\n".join(lines)

    def build(self) -> list[discord.ui.Item]:
        return [
            self.status(
                [
                    ("Status", status_text(self.enabled)),
                    ("Level-up announcements", channel_text(self.guild, self.channel_id) if self.channel_id else "*Off (no channel set)*"),
                ]
            ),
            self.text(f"### Reward roles\n{self._rewards_text()}"),
            self.row(
                self.toggle(self.enabled, self.set_enabled),
                self.button("Add reward\N{HORIZONTAL ELLIPSIS}", self.open_add_modal, style=discord.ButtonStyle.primary, emoji="\N{HEAVY PLUS SIGN}"),
                self.button(
                    "Remove rewards\N{HORIZONTAL ELLIPSIS}", self.open_remove_modal, emoji="\N{HEAVY MINUS SIGN}", disabled=not self.level_roles
                ),
                self.reset_button(),
            ),
            self.row(self.channel_select("Level-up announcement channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
        ]

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        await self.db.edit_leveling_config(guild_id=self.guild.id, enabled=enabled)
        await self.commit(
            interaction, "Leveling enabled. Members now earn XP for chatting." if enabled else "Leveling disabled. XP earned so far is kept."
        )

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        await self.db.edit_leveling_config(guild_id=self.guild.id, channel_id=channel_id)
        if channel_id is None:
            await self.commit(interaction, "Level-up announcements turned off. Reward roles are still given.")
        else:
            await self.commit(interaction, f"Level-ups will be announced in {channel_text(self.guild, channel_id)}.")

    async def open_add_modal(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(AddRewardModal(self))

    async def open_remove_modal(self, interaction: Interaction) -> None:
        if not self.level_roles:
            await self.commit(interaction, "There are no reward roles to remove.", level=NoticeLevel.INFO)
            return
        await interaction.response.send_modal(RemoveRewardsModal(self))
