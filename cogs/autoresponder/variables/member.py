import discord


class JinjaMember:
    def __init__(self, *, member: discord.Member | discord.User) -> None:
        assert isinstance(member, discord.Member)
        self.__member = member

    @property
    def id(self):
        """Get member id."""
        return self.__member.id

    @property
    def name(self):
        """Get member name."""
        return self.__member.name

    @property
    def mention(self):
        """Get member mention."""
        return self.__member.mention

    @property
    def nick(self):
        """Get member nickname."""
        return self.__member.nick

    @property
    def display_name(self):
        """Get member display name."""
        return self.__member.display_name

    @property
    def avatar_url(self):
        """Get member avatar url."""
        return self.__member.display_avatar.url

    async def _check_perms(self, **perms: bool) -> bool:
        """Check if bot has permissions to do actions on member."""
        permissions = discord.Permissions(**perms)
        return (
            self.__member.guild.me.guild_permissions >= permissions
            and self.__member.guild.me.top_role > self.__member.top_role
        )

    async def kick(self, *, reason: str = None):
        """Kick member from guild."""
        if not await self._check_perms(kick_members=True):
            return

        await self.__member.kick(reason=reason)

    async def ban(self, *, reason: str = None, delete_message_days: int = discord.utils.MISSING):
        """Ban member from guild."""
        if not await self._check_perms(ban_members=True):
            return

        await self.__member.ban(reason=reason, delete_message_days=delete_message_days)

    async def unban(self, *, reason: str = None):
        """Unban member from guild."""
        if not await self._check_perms(ban_members=True):
            return

        await self.__member.unban(reason=reason)

    async def add_role(self, *, role: discord.Object, reason: str = None):
        """Add role to member."""
        if not await self._check_perms(manage_roles=True):
            return

        await self.__member.add_roles(role, reason=reason)
