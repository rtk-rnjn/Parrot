from .afk import _GuildAfkMixin  # noqa
from .automod import _GuildAutomodMixin  # noqa
from .custom_commands import _GuildCustomCommandsMixin  # noqa
from .giveaway import _GuildGiveawayMixin  # noqa
from .leveling import _GuildLevelingMixin  # noqa
from .mute import _GuildMuteRoleMixin  # noqa
from .prefix import _GuildPrefixMixin  # noqa
from .starboard import _GuildStarboardMixin  # noqa
from .tags import _GuildTagsMixin  # noqa
from .voilation import _GuildVoilationMixin  # noqa
from .welcomer import _GuildWelcomerMixin  # noqa

__all__ = ("_GuildMixin",)


class _GuildMixin(
    _GuildPrefixMixin,
    _GuildCustomCommandsMixin,
    _GuildMuteRoleMixin,
    _GuildVoilationMixin,
    _GuildTagsMixin,
    _GuildAutomodMixin,
    _GuildAfkMixin,
    _GuildGiveawayMixin,
    _GuildLevelingMixin,
    _GuildWelcomerMixin,
    _GuildStarboardMixin,
): ...
