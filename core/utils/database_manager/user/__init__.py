from .timezone import _UserTimezoneMixin  # noqa

__all__ = ("_UserMixin",)


class _UserMixin(
    _UserTimezoneMixin,
): ...
