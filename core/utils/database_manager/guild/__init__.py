from .automod import _GuildAutomodMixin  # noqa
from .custom_commands import _GuildCustomCommandsMixin  # noqa
from .mute import _GuildMuteRoleMixin  # noqa
from .prefix import _GuildPrefixMixin  # noqa
from .voilation import _GuildVoilationMixin  # noqa

__all__ = ("_GuildMixin",)


class _GuildMixin(
    _GuildPrefixMixin,
    _GuildCustomCommandsMixin,
    _GuildMuteRoleMixin,
    _GuildVoilationMixin,
    _GuildAutomodMixin,
): ...
