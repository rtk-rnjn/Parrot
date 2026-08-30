from .configs import (
    CategoriesConfig,
    ChannelsConfig,
    DurationConfig,
    NoConfig,
    RolesConfig,
)
from .enum import ConditionType

type ConditionConfig = NoConfig | RolesConfig | ChannelsConfig | CategoriesConfig | DurationConfig

_CONFIG_TYPES: dict[ConditionType, type[ConditionConfig]] = {
    ConditionType.IGNORED_ROLES: RolesConfig,
    ConditionType.REQUIRED_ROLES: RolesConfig,
    ConditionType.IGNORED_CHANNELS: ChannelsConfig,
    ConditionType.ACTIVE_CHANNELS: ChannelsConfig,
    ConditionType.ACCOUNT_AGE_ABOVE: DurationConfig,
    ConditionType.ACCOUNT_AGE_BELOW: DurationConfig,
    ConditionType.MEMBER_DURATION_ABOVE: DurationConfig,
    ConditionType.MEMBER_DURATION_BELOW: DurationConfig,
    ConditionType.IGNORE_BOTS: NoConfig,
    ConditionType.ONLY_BOTS: NoConfig,
    ConditionType.IGNORED_CATEGORIES: CategoriesConfig,
    ConditionType.ACTIVE_CATEGORIES: CategoriesConfig,
    ConditionType.NEW_MESSAGE: NoConfig,
    ConditionType.EDITED_MESSAGE: NoConfig,
    ConditionType.ACTIVE_IN_THREADS: NoConfig,
    ConditionType.IGNORE_THREADS: NoConfig,
    ConditionType.IGNORE_FORWARDS: NoConfig,
    ConditionType.ONLY_FORWARDS: NoConfig,
}
