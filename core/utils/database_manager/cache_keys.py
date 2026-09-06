from enum import StrEnum


class RedisKeys(StrEnum):
    """Templates for keys used by the Redis cache."""

    GUILD_COMMAND_PREFIX = "guild:{guild_id}:command_prefix"
    GUILD_MUTE_ROLE_ID = "guild:{guild_id}:mute_role_id"
    GUILD_MUTED_MEMBERS = "guild:{guild_id}:muted_members"

    GUILD_MEMBER_VOILATION_COUNT = "guild:{guild_id}:violations:{voilation_name}:member:{user_id}"

    GUILD_AUTOMOD_RULES = "guild:{guild_id}:automod_rules"
    GUILD_AUTOMOD_RULE_TRIGGER = "guild:{guild_id}:automod_rule:{rule_name}:trigger"
    GUILD_AUTOMOD_RULE_CONDITIONS = "guild:{guild_id}:automod_rule:{rule_name}:conditions"
    GUILD_AUTOMOD_RULE_EFFECTS = "guild:{guild_id}:automod_rule:{rule_name}:effects"
    GUILD_AUTOMOD_RULE_ENABLED = "guild:{guild_id}:automod_rule:{rule_name}:enabled"
    GUILD_AUTOMOD_RULE_PRIORITY = "guild:{guild_id}:automod_rule:{rule_name}:priority"
    GUILD_AUTOMOD_RULE_CONDITION_MATCH_MODE = "guild:{guild_id}:automod_rule:{rule_name}:condition_match_mode"

    GUILD_CUSTOM_COMMAND_NAMES = "guild:{guild_id}:custom_command_names"
    GUILD_CUSTOM_COMMAND_RESPONSE = "guild:{guild_id}:custom_command:{command_name}:response"
    GUILD_CUSTOM_COMMAND_IGNORED_ROLES = "guild:{guild_id}:custom_command:{command_name}:ignored_roles"
    GUILD_CUSTOM_COMMAND_IGNORED_CHANNELS = "guild:{guild_id}:custom_command:{command_name}:ignored_channels"
    GUILD_CUSTOM_COMMAND_ENABLED = "guild:{guild_id}:custom_command:{command_name}:enabled"
    GUILD_CUSTOM_COMMAND_DB = "guild:{guild_id}:custom_command_db"

    GUILD_TAG_NAMES = "guild:{guild_id}:tag_names"
    GUILD_TAG_CONTENT = "guild:{guild_id}:tag:{tag_name}:content"
    GUILD_TAG_NSFW = "guild:{guild_id}:tag:{tag_name}:nsfw"
    GUILD_TAG_CREATOR_ID = "guild:{guild_id}:tag:{tag_name}:creator_id"
    GUILD_TAG_CREATED_AT = "guild:{guild_id}:tag:{tag_name}:created_at"
    GUILD_TAG_ALIASES = "guild:{guild_id}:tag:{tag_name}:aliases"
    GUILD_TAG_USED_COUNT = "guild:{guild_id}:tag:{tag_name}:used_count"
    GUILD_TAG_ALIAS_MAP = "guild:{guild_id}:tag_alias_map"

    GUILD_AFK_USERS = "guild:{guild_id}:afk_users"
    GUILD_AFK_USER_REASON = "guild:{guild_id}:afk_user:{user_id}:reason"

    GUILD_LEVELING_CONFIG_ENABLED = "guild:{guild_id}:leveling_config:enabled"
    GUILD_LEVELING_CONFIG_LEVEL_ROLES = "guild:{guild_id}:leveling_config:level_roles"

    GUILD_LEVELING_DATA = "guild:{guild_id}:leveling_data"

    GUILD_GIVEAWAY_CONFIG_ENABLED = "guild:{guild_id}:giveaway_config:enabled"
    GUILD_GIVEAWAY_CONFIG_CHANNEL_ID = "guild:{guild_id}:giveaway_config:giveaway_channel_id"
    GUILD_GIVEAWAY_CONFIG_ROLE_ID = "guild:{guild_id}:giveaway_config:giveaway_role_id"

    GUILD_WELCOME_CONFIG_ENABLED = "guild:{guild_id}:welcome_config:enabled"
    GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_MESSAGE = "guild:{guild_id}:welcome_config:on_member_join_message"
    GUILD_WELCOME_CONFIG_ON_MEMBER_JOIN_CHANNEL_ID = "guild:{guild_id}:welcome_config:on_member_join_channel_id"
    GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_MESSAGE = "guild:{guild_id}:welcome_config:on_member_leave_message"
    GUILD_WELCOME_CONFIG_ON_MEMBER_LEAVE_CHANNEL_ID = "guild:{guild_id}:welcome_config:on_member_leave_channel_id"
    GUILD_STARBOARD_CONFIG = "guild:{guild_id}:starboard_config"
    GUILD_STARBOARD_BOARD_MESSAGES = "guild:{guild_id}:starboard_board_messages"

    USER_TIMEZONE = "user:{user_id}:timezone"

    SCAM_LINKS_CACHE = "scam_links_cache"
    SCAM_LINK_WARNED = "scam_link_warned:{channel_id}"

    USER_HIGHLIGHT_IGNORED_USERS = "user:{user_id}:highlight_ignored_users"
    USER_HIGHLIGHT_WORDS = "user:{user_id}:{guild_id}:highlight_words"

    USER_TODO_ITEM_IDS = "user:{user_id}:todo_item_ids"
    USER_TODO_ITEM = "user:{user_id}:todo_item:{todo_id}"
