from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .channel import JinjaChannel
    from .member import JinjaMember
    from .role import JinjaRole

import discord


class JinjaGuild:
    def __init__(self, *, guild: discord.Guild) -> None:
        self.__guild = guild

    def __repr__(self) -> str:
        return f"<JinjaGuild id={self.id} name={self.name}>"

    def __str__(self) -> str:
        return self.name

    @property
    def id(self):
        """Get guild id."""
        return self.__guild.id

    @property
    def name(self):
        """Get guild name."""
        return self.__guild.name

    @property
    def icon_url(self):
        """Get guild icon url."""
        return getattr(self.__guild.icon, "url", None)

    @property
    def owner(self):
        """Get guild owner."""
        from .member import JinjaMember

        return JinjaMember(member=self.__guild.owner) if self.__guild.owner else None

    @property
    def member_count(self) -> int | None:
        """Get guild member count."""
        return self.__guild.member_count

    @property
    def description(self) -> str | None:
        """Get guild description."""
        return self.__guild.description

    @property
    def banner_url(self) -> str | None:
        """Get guild banner url."""
        return getattr(self.__guild.banner, "url", None)

    @property
    def vanity_url(self) -> str | None:
        """Get guild vanity url."""
        return self.__guild.vanity_url_code

    @property
    def region(self) -> str:
        """Get guild region."""
        return "deprecated"

    @property
    def premium_tier(self) -> int:
        """Get guild premium tier."""
        return self.__guild.premium_tier

    @property
    def premium_subscription_count(self) -> int | None:
        """Get guild premium subscription count."""
        return self.__guild.premium_subscription_count

    @property
    def preferred_locale(self) -> str | None:
        """Get guild preferred locale."""
        return self.__guild.preferred_locale.name

    @property
    def afk_timeout(self) -> int:
        """Get guild afk timeout."""
        return self.__guild.afk_timeout

    @property
    def members(self) -> list[JinjaMember]:
        """Get guild members."""
        from .member import JinjaMember

        return [JinjaMember(member=member) for member in self.__guild.members]

    @property
    def roles(self) -> list[JinjaRole]:
        """Get guild roles."""
        from .role import JinjaRole

        return [JinjaRole(role=role) for role in self.__guild.roles]

    @property
    def icon(self) -> str | None:
        """Get guild icon."""
        return getattr(self.__guild.icon, "url", None)

    @property
    def splash(self) -> str | None:
        """Get guild splash."""
        return getattr(self.__guild.splash, "url", None)

    @property
    def discovery_splash(self) -> str | None:
        """Get guild discovery splash."""
        return getattr(self.__guild.discovery_splash, "url", None)

    async def _check_perms(self, **perms: bool) -> bool:
        """Check if bot has permissions to do actions on guild."""
        permissions = discord.Permissions(**perms)
        return self.__guild.me.guild_permissions >= permissions

    async def ban(self, member: JinjaMember, *, reason: str = None, delete_message_days: int = discord.utils.MISSING):
        """Ban member from guild."""
        if not await self._check_perms(ban_members=True):
            return

        await self.__guild.ban(member.__member, reason=reason, delete_message_days=delete_message_days)

    async def unban(self, user: discord.Object, *, reason: str = None):
        """Unban user from guild."""
        if not await self._check_perms(ban_members=True):
            return

        await self.__guild.unban(user, reason=reason)

    def get_member(self, member_id: int) -> JinjaMember | None:
        """Get member from guild."""
        from .member import JinjaMember

        member = self.__guild.get_member(member_id)
        if member is None:
            return

        return JinjaMember(member=member)

    def get_role(self, role_id: int) -> JinjaRole | None:
        """Get role from guild."""
        from .role import JinjaRole

        role = self.__guild.get_role(role_id)
        if role is None:
            return

        return JinjaRole(role=role)

    async def create_role(
        self,
        name: str,
        *,
        permissions: discord.Permissions = discord.utils.MISSING,
        color: discord.Colour = discord.utils.MISSING,
        hoist: bool = discord.utils.MISSING,
        mentionable: bool = discord.utils.MISSING,
        reason: str = None,
    ) -> JinjaRole:
        """Create role in guild."""
        from .role import JinjaRole

        role = await self.__guild.create_role(
            name=name,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
            reason=reason,
        )

        return JinjaRole(role=role)

    async def _create_channel(
        self,
        _type: Literal["text", "voice"],
        name: str,
        *,
        overwrites: dict[JinjaMember | JinjaRole, discord.PermissionOverwrite] = discord.utils.MISSING,
        category: JinjaChannel = discord.utils.MISSING,
        reason: str = None,
    ) -> JinjaChannel:
        from .channel import JinjaChannel

        actual_overwrites = {}
        if overwrites:
            for key, value in overwrites.items():
                if isinstance(key, JinjaMember) and (member := self.get_member(key.id)):
                    actual_overwrites[member] = value
                elif isinstance(key, JinjaRole) and (role := self.get_role(key.id)):
                    actual_overwrites[role] = value

        if _type == "text":
            func = self.__guild.create_text_channel
        else:
            func = self.__guild.create_voice_channel

        if category:
            category: discord.CategoryChannel = self.__guild.get_channel(category.id) or discord.utils.MISSING
            if not isinstance(category, discord.CategoryChannel):
                category = discord.utils.MISSING

        channel = await func(
            name=name,
            overwrites=actual_overwrites,
            category=category,
            reason=reason,
        )

        return JinjaChannel(channel=channel)

    async def create_voice_channel(self, *args, **kwargs) -> JinjaChannel:
        return await self._create_channel("voice", *args, **kwargs)

    async def create_text_channel(self, *args, **kwargs) -> JinjaChannel:
        return await self._create_channel("text", *args, **kwargs)

    def get_channel(self, channel_id: int) -> JinjaChannel | None:
        """Get channel from guild."""
        from .channel import JinjaChannel

        channel = self.__guild.get_channel(channel_id)
        if channel is None:
            return

        return JinjaChannel(channel=channel)
