from __future__ import annotations

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
