from .configs import (
    AllCapsConfig,
    AttachmentConfig,
    CountConfig,
    DiscordAutomodConfig,
    LengthConfig,
    ListConfig,
    MentionConfig,
    NoConfig,
    RegexConfig,
    TimeWindowConfig,
    ViolationConfig,
)
from .enum import TriggerType

type TriggerConfig = (
    NoConfig
    | CountConfig
    | TimeWindowConfig
    | ListConfig
    | RegexConfig
    | LengthConfig
    | MentionConfig
    | AttachmentConfig
    | ViolationConfig
    | AllCapsConfig
    | DiscordAutomodConfig
)

_CONFIG_TYPES: dict[TriggerType, type[TriggerConfig]] = {
    TriggerType.ALL_CAPS: AllCapsConfig,
    TriggerType.MESSAGE_MENTIONS: CountConfig,
    TriggerType.ANY_LINK: NoConfig,
    TriggerType.VIOLATIONS: ViolationConfig,
    TriggerType.WORD_DENYLIST: ListConfig,
    TriggerType.WORD_ALLOWLIST: ListConfig,
    TriggerType.WEBSITE_DENYLIST: ListConfig,
    TriggerType.WEBSITE_ALLOWLIST: ListConfig,
    TriggerType.SERVER_INVITES: NoConfig,
    TriggerType.GOOGLE_FLAGGED_BAD_LINKS: NoConfig,
    TriggerType.USER_MESSAGES: TimeWindowConfig,
    TriggerType.CHANNEL_MESSAGES: TimeWindowConfig,
    TriggerType.USER_MENTIONS: MentionConfig,
    TriggerType.CHANNEL_MENTIONS: MentionConfig,
    TriggerType.MESSAGE_REGEX: RegexConfig,
    TriggerType.MESSAGE_NOT_REGEX: RegexConfig,
    TriggerType.CONSECUTIVE_IDENTICAL_MESSAGES: TimeWindowConfig,
    TriggerType.NICKNAME_REGEX: RegexConfig,
    TriggerType.NICKNAME_NOT_REGEX: RegexConfig,
    TriggerType.NICKNAME_WORD_ALLOWLIST: ListConfig,
    TriggerType.NICKNAME_WORD_DENYLIST: ListConfig,
    TriggerType.USER_ATTACHMENTS: AttachmentConfig,
    TriggerType.CHANNEL_ATTACHMENTS: AttachmentConfig,
    TriggerType.JOIN_USERNAME_WORD_ALLOWLIST: ListConfig,
    TriggerType.JOIN_USERNAME_WORD_DENYLIST: ListConfig,
    TriggerType.JOIN_USERNAME_REGEX: RegexConfig,
    TriggerType.JOIN_USERNAME_NOT_REGEX: RegexConfig,
    TriggerType.JOIN_USERNAME_INVITE: NoConfig,
    TriggerType.NEW_MEMBER: NoConfig,
    TriggerType.MESSAGE_WITHOUT_ATTACHMENTS: NoConfig,
    TriggerType.MESSAGE_WITH_ATTACHMENTS: NoConfig,
    TriggerType.FLAGGED_SCAM_LINKS: NoConfig,
    TriggerType.MESSAGE_LENGTH_GT: LengthConfig,
    TriggerType.MESSAGE_LENGTH_LT: LengthConfig,
    TriggerType.USER_LINKS: TimeWindowConfig,
    TriggerType.CHANNEL_LINKS: TimeWindowConfig,
    TriggerType.DISCORD_AUTOMOD: DiscordAutomodConfig,
}
