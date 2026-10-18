from __future__ import annotations

from typing import TYPE_CHECKING

from ..mixin import DatabaseMixin
from .afk import _GuildAfkMixin
from .automod import _GuildAutomodMixin
from .birthday import _GuildBirthdayMixin
from .commands import _GuildCommandConfigMixin
from .custom_commands import _GuildCustomCommandsMixin
from .defaults import DEFAULT_PREFIX, EVENT_NAMES, default_guild_configuration
from .events import _GuildEventsMixin
from .giveaway import _GuildGiveawayMixin
from .global_chat import _GuildGlobalChatMixin
from .hub import _GuildHubMixin
from .leveling import _GuildLevelingMixin
from .mod import _GuildModActionMixin, _GuildModeratorMixin
from .mute import _GuildMuteRoleMixin
from .prefix import _GuildPrefixMixin
from .settings import SETTING_SECTIONS, GuildSettingSection, _GuildSettingsMixin
from .starboard import _GuildStarboardMixin
from .suggestion import _GuildSuggestionMixin
from .tags import _GuildTagsMixin
from .telephone import _GuildTelephoneMixin
from .ticket import _GuildTicketMixin
from .violation import _GuildViolationMixin
from .welcomer import _GuildWelcomerMixin

if TYPE_CHECKING:
    from ..models import GuildConfiguration

__all__ = ("DEFAULT_PREFIX", "EVENT_NAMES", "SETTING_SECTIONS", "GuildSettingSection", "_GuildMixin")


class _GuildMixin(
    _GuildPrefixMixin,
    _GuildCustomCommandsMixin,
    _GuildMuteRoleMixin,
    _GuildViolationMixin,
    _GuildTagsMixin,
    _GuildAutomodMixin,
    _GuildAfkMixin,
    _GuildGiveawayMixin,
    _GuildHubMixin,
    _GuildLevelingMixin,
    _GuildWelcomerMixin,
    _GuildStarboardMixin,
    _GuildBirthdayMixin,
    _GuildGlobalChatMixin,
    _GuildSuggestionMixin,
    _GuildTelephoneMixin,
    _GuildEventsMixin,
    _GuildTicketMixin,
    _GuildModeratorMixin,
    _GuildModActionMixin,
    _GuildSettingsMixin,
    _GuildCommandConfigMixin,
    DatabaseMixin,
):
    def create_guild_configuration(self, guild_id: int) -> GuildConfiguration:
        return default_guild_configuration(guild_id)

    def empty_guild_config(self, guild_id: int) -> GuildConfiguration:
        """Compatibility alias for :meth:`create_guild_configuration`."""
        return self.create_guild_configuration(guild_id)
