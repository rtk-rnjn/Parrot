from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoConfig:
    pass


@dataclass(frozen=True, slots=True)
class RolesConfig:
    roles: tuple[int, ...]
    require_all: bool = False


@dataclass(frozen=True, slots=True)
class ChannelsConfig:
    channels: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class CategoriesConfig:
    categories: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class DurationConfig:
    minutes: int
