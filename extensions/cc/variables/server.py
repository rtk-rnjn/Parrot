from __future__ import annotations

from dataclasses import dataclass, field

import discord


@dataclass(frozen=True, slots=True, repr=False)
class Server:
    _guild: discord.Guild = field(repr=False)

    def __str__(self) -> str:
        return self.name

    @property
    def id(self) -> int:
        """Get server id."""
        return self._guild.id

    @property
    def name(self) -> str:
        """Get server name."""
        return self._guild.name

    @property
    def icon_url(self) -> str | None:
        """Get server icon URL."""
        return getattr(self._guild.icon, "url", None)

    @property
    def member_count(self) -> int | None:
        """Get server member count."""
        return self._guild.member_count

    @property
    def description(self) -> str | None:
        """Get server description."""
        return self._guild.description

    @property
    def banner_url(self) -> str | None:
        """Get server banner URL."""
        return getattr(self._guild.banner, "url", None)

    @property
    def vanity_url(self) -> str | None:
        """Get server vanity URL."""
        return self._guild.vanity_url_code

    @property
    def region(self) -> str:
        """Get server region."""
        return "deprecated"

    @property
    def premium_tier(self) -> int:
        """Get server premium tier."""
        return self._guild.premium_tier

    @property
    def premium_subscription_count(self) -> int | None:
        """Get server premium subscription count."""
        return self._guild.premium_subscription_count

    @property
    def preferred_locale(self) -> str:
        """Get server preferred locale."""
        return self._guild.preferred_locale.name

    @property
    def afk_timeout(self) -> int:
        """Get server AFK timeout."""
        return self._guild.afk_timeout

    @property
    def icon(self) -> str | None:
        """Get server icon."""
        return getattr(self._guild.icon, "url", None)

    @property
    def splash(self) -> str | None:
        """Get server splash."""
        return getattr(self._guild.splash, "url", None)

    @property
    def discovery_splash(self) -> str | None:
        """Get server discovery splash."""
        return getattr(self._guild.discovery_splash, "url", None)

    async def _check_perms(self, **perms: bool) -> bool:
        """Check if the bot has the required permissions in the server."""
        permissions = discord.Permissions(**perms)
        return self._guild.me.guild_permissions >= permissions
