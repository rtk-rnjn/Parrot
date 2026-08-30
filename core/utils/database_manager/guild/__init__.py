from .mute import _GuildMuteRoleMixin  # noqa
from .prefix import _GuildPrefixMixin  # noqa
from .voilation import _GuildVoilationMixin  # noqa

__all__ = ("_GuildMixin",)


class _GuildMixin(
    _GuildPrefixMixin,
    _GuildMuteRoleMixin,
    _GuildVoilationMixin,
): ...
