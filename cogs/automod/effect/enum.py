from enum import StrEnum


class EffectType(StrEnum):
    DELETE_MESSAGE = "delete_message"
    ADD_VIOLATION = "add_violation"
    KICK_USER = "kick_user"
    BAN_USER = "ban_user"
    MUTE_USER = "mute_user"
    WARN_USER = "warn_user"
    SET_NICKNAME = "set_nickname"
    RESET_VIOLATIONS = "reset_violations"
    DELETE_MULTIPLE_MESSAGES = "delete_multiple_messages"
    GIVE_ROLE = "give_role"
    ENABLE_SLOWMODE = "enable_slowmode"
    REMOVE_ROLE = "remove_role"
    SEND_MESSAGE = "send_message"
    TIMEOUT_USER = "timeout_user"
    SEND_ALERT = "send_alert"
