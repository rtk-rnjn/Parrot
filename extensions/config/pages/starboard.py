from __future__ import annotations

import discord

from .base import Interaction, NoticeLevel, Page, PageModal, channel_text, status_text

__all__ = ("StarboardPage",)

MIN_THRESHOLD = 1
MAX_THRESHOLD = 1000
MAX_EMOJI_CODEPOINTS = 8


def parse_emoji(raw: str) -> str | None:
    """Return the stored form of a reaction emoji (what ``str(payload.emoji)`` yields), or ``None`` if invalid."""
    raw = raw.strip()
    if not raw:
        return None

    partial = discord.PartialEmoji.from_str(raw)
    if partial.is_custom_emoji():
        return str(partial)

    if len(raw) <= MAX_EMOJI_CODEPOINTS and not any(character.isalnum() or character.isspace() for character in raw):
        return raw
    return None


class StarboardModal(PageModal):
    def __init__(self, page: StarboardPage) -> None:
        super().__init__(page, title="Starboard rules")
        starboard = page.config["starboard_config"]
        self.threshold_input = discord.ui.TextInput(
            placeholder="3",
            default=str(starboard.get("threshold") or ""),
            min_length=1,
            max_length=len(str(MAX_THRESHOLD)),
        )
        self.emoji_input = discord.ui.TextInput(
            placeholder="\N{WHITE MEDIUM STAR}",
            default=starboard.get("emoji") or None,
            min_length=1,
            max_length=64,
        )
        self.self_star_input = discord.ui.Checkbox(default=bool(starboard.get("self_star")))
        self.allow_nsfw_input = discord.ui.Checkbox(default=bool(starboard.get("allow_nsfw")))
        self.max_days_age_input = discord.ui.TextInput(
            placeholder="30",
            default=str(starboard.get("max_age_days") or ""),
            min_length=1,
            max_length=len(str(MAX_THRESHOLD)),
        )

        self.add_item(
            discord.ui.Label(text="Reactions needed", description=f"Between {MIN_THRESHOLD} and {MAX_THRESHOLD}.", component=self.threshold_input)
        )
        self.add_item(
            discord.ui.Label(
                text="Reaction emoji",
                description="A standard emoji, or a custom emoji from this server such as <:name:id>.",
                component=self.emoji_input,
            )
        )
        self.add_item(
            discord.ui.Label(
                text="Allow self-star",
                description="Whether the author of a message can star their own message.",
                component=self.self_star_input,
            )
        )
        self.add_item(
            discord.ui.Label(
                text="Allow NSFW",
                description="Whether messages in NSFW channels can be starred.",
                component=self.allow_nsfw_input,
            )
        )
        self.add_item(
            discord.ui.Label(
                text="Max age (days)",
                description="Messages older than this many days will not be starred. Leave blank for no limit.",
                component=self.max_days_age_input,
            )
        )

    async def on_submit(self, interaction: Interaction) -> None:
        try:
            threshold = int(self.threshold_input.value.strip())
        except ValueError:
            threshold = 0
        if not MIN_THRESHOLD <= threshold <= MAX_THRESHOLD:
            await self.page.commit(
                interaction, f"Reactions needed must be a whole number between {MIN_THRESHOLD} and {MAX_THRESHOLD}.", level=NoticeLevel.ERROR
            )
            return

        emoji = parse_emoji(self.emoji_input.value)
        if emoji is None:
            await self.page.commit(interaction, "That does not look like a single emoji.", level=NoticeLevel.ERROR)
            return

        try:
            max_days_age = int(self.max_days_age_input.value.strip()) if self.max_days_age_input.value.strip() else None
        except ValueError:
            max_days_age = None

        await self.page.db.edit_starboard_config(
            guild_id=self.page.guild.id,
            threshold=threshold,
            emoji=emoji,
            self_star=self.self_star_input.value,
            allow_nsfw=self.allow_nsfw_input.value,
            max_age_days=max_days_age,
        )
        await self.page.commit(interaction, f"Messages now need {threshold} {emoji} reaction{'' if threshold == 1 else 's'} to reach the starboard.")


class StarboardPage(Page):
    key = "starboard"
    label = "Starboard"
    emoji = "\N{WHITE MEDIUM STAR}"
    description = "Repost messages that collect enough reactions into a hall-of-fame channel."
    section = "starboard_config"

    @property
    def enabled(self) -> bool:
        return bool(self.config["starboard_config"].get("enabled"))

    @property
    def channel_id(self) -> int | None:
        return self.config["starboard_config"].get("channel_id")

    def summary(self) -> str:
        starboard = self.config["starboard_config"]
        text = status_text(self.enabled)
        if self.channel_id:
            text += (
                f" \N{MIDDLE DOT} {starboard.get('threshold') or '?'} {starboard.get('emoji') or ''} in {channel_text(self.guild, self.channel_id)}"
            )
        return text

    def accent(self) -> discord.Colour | None:
        return discord.Colour.green() if self.enabled else discord.Colour.dark_grey()

    def reset_summary(self) -> str:
        return "the starboard toggle, channel, threshold and emoji (existing starboard posts are kept)"

    def build(self) -> list[discord.ui.Item]:
        starboard = self.config["starboard_config"]
        threshold = starboard.get("threshold")
        return [
            self.status(
                [
                    ("Status", status_text(self.enabled)),
                    ("Starboard channel", channel_text(self.guild, self.channel_id)),
                    ("Reactions needed", f"{threshold}" if threshold else "*Not set*"),
                    ("Reaction emoji", starboard.get("emoji") or "*Not set*"),
                    ("Allow self-star", "Yes" if starboard.get("self_star") else "No"),
                    ("Allow NSFW", "Yes" if starboard.get("allow_nsfw") else "No"),
                    ("Max age (days)", str(starboard.get("max_age_days")) if starboard.get("max_age_days") is not None else "*Not set*"),
                ]
            ),
            self.row(
                self.toggle(self.enabled, self.set_enabled),
                self.button(
                    "Edit threshold & emoji\N{HORIZONTAL ELLIPSIS}", self.open_rules_modal, style=discord.ButtonStyle.primary, emoji="\N{PENCIL}"
                ),
                self.reset_button(),
            ),
            self.row(self.channel_select("Starboard channel\N{HORIZONTAL ELLIPSIS}", self.set_channel, current=self.channel_id)),
            self.row(
                self.channels_select(
                    "Ignored channels\N{HORIZONTAL ELLIPSIS}", self.set_ignored_channels, current=starboard.get("ignored_channels") or []
                )
            ),
            self.row(self.roles_select("Ignored roles\N{HORIZONTAL ELLIPSIS}", self.set_ignored_roles, current=starboard.get("ignored_roles") or [])),
            self.row(
                self.mentionables_select("Ignored users\N{HORIZONTAL ELLIPSIS}", self.set_ignored_users, current=starboard.get("ignored_users") or [])
            ),
        ]

    async def set_enabled(self, interaction: Interaction, enabled: bool) -> None:
        if enabled and self.channel_id is None:
            await self.commit(interaction, "Pick a starboard channel first, then enable it.", level=NoticeLevel.ERROR)
            return
        await self.db.edit_starboard_config(guild_id=self.guild.id, enabled=enabled)
        await self.commit(interaction, "Starboard enabled." if enabled else "Starboard disabled.")

    async def set_channel(self, interaction: Interaction, channel_ids: list[int]) -> None:
        channel_id = channel_ids[0] if channel_ids else None
        if channel_id is None:
            await self.db.edit_starboard_config(guild_id=self.guild.id, enabled=False, channel_id=None)
            await self.commit(interaction, "Starboard channel cleared and the starboard disabled.")
            return

        await self.db.edit_starboard_config(guild_id=self.guild.id, channel_id=channel_id)
        hint = "" if self.enabled else " Press Enable to start collecting."
        await self.commit(interaction, f"Starboard posts will go to {channel_text(self.guild, channel_id)}.{hint}")

    async def open_rules_modal(self, interaction: Interaction) -> None:
        await interaction.response.send_modal(StarboardModal(self))

    async def set_ignored_channels(self, interaction: Interaction, channel_ids: list[int]) -> None:
        await self.db.edit_starboard_config(guild_id=self.guild.id, ignored_channels=channel_ids)
        await self.commit(interaction, f"Starboard will ignore {len(channel_ids)} channel{'' if len(channel_ids) == 1 else 's'}.")

    async def set_ignored_roles(self, interaction: Interaction, roles: list[discord.Role]) -> None:
        role_ids = [role.id for role in roles]
        await self.db.edit_starboard_config(guild_id=self.guild.id, ignored_roles=role_ids)
        await self.commit(interaction, f"Starboard will ignore {len(role_ids)} role{'' if len(role_ids) == 1 else 's'}.")

    async def set_ignored_users(self, interaction: Interaction, mentionables: list[discord.abc.Snowflake]) -> None:
        user_ids = [mentionable.id for mentionable in mentionables]
        await self.db.edit_starboard_config(guild_id=self.guild.id, ignored_users=user_ids)
        await self.commit(interaction, f"Starboard will ignore {len(user_ids)} user{'' if len(user_ids) == 1 else 's'}.")
