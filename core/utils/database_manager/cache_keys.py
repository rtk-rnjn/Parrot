from enum import StrEnum


class RedisKeys(StrEnum):
    """Templates for keys used by the Redis cache."""

    GUILD_COMMAND_PREFIX = "guild:{guild_id}:command_prefix"
    GUILD_MUTE_ROLE_ID = "guild:{guild_id}:mute_role_id"
    GUILD_MUTED_MEMBERS = "guild:{guild_id}:muted_members"

    GUILD_MEMBER_VOILATION_COUNT = "guild:{guild_id}:member:{user_id}:voilation"

    GUILD_AUTOMOD_RULES = "guild:{guild_id}:automod_rules"
    GUILD_AUTOMOD_RULE_TRIGGER = "guild:{guild_id}:automod_rule:{rule_name}:trigger"
    GUILD_AUTOMOD_RULE_CONDITIONS = "guild:{guild_id}:automod_rule:{rule_name}:conditions"
    GUILD_AUTOMOD_RULE_EFFECTS = "guild:{guild_id}:automod_rule:{rule_name}:effects"
    GUILD_AUTOMOD_RULE_ENABLED = "guild:{guild_id}:automod_rule:{rule_name}:enabled"
    GUILD_AUTOMOD_RULE_PRIORITY = "guild:{guild_id}:automod_rule:{rule_name}:priority"
    GUILD_AUTOMOD_RULE_CONDITION_MATCH_MODE = "guild:{guild_id}:automod_rule:{rule_name}:condition_match_mode"

    USER_TIMEZONE = "user:{user_id}:timezone"
