from __future__ import annotations

from .configs import (
    AlertConfig,
    BanConfig,
    DeleteMessagesConfig,
    MessageConfig,
    MuteConfig,
    NicknameConfig,
    NoConfig,
    RoleConfig,
    SendMessageConfig,
    SlowmodeConfig,
    TimeoutConfig,
    ViolationConfig,
)
from .enum import EffectType

type EffectConfig = (
    NoConfig
    | MessageConfig
    | BanConfig
    | MuteConfig
    | TimeoutConfig
    | NicknameConfig
    | DeleteMessagesConfig
    | RoleConfig
    | SlowmodeConfig
    | SendMessageConfig
    | AlertConfig
    | ViolationConfig
)

_EFFECT_CONFIG_TYPES: dict[EffectType, type[EffectConfig]] = {
    EffectType.DELETE_MESSAGE: NoConfig,
    EffectType.ADD_VIOLATION: ViolationConfig,
    EffectType.KICK_USER: MessageConfig,
    EffectType.BAN_USER: BanConfig,
    EffectType.MUTE_USER: MuteConfig,
    EffectType.WARN_USER: MessageConfig,
    EffectType.SET_NICKNAME: NicknameConfig,
    EffectType.RESET_VIOLATIONS: ViolationConfig,
    EffectType.DELETE_MULTIPLE_MESSAGES: DeleteMessagesConfig,
    EffectType.GIVE_ROLE: RoleConfig,
    EffectType.REMOVE_ROLE: RoleConfig,
    EffectType.ENABLE_SLOWMODE: SlowmodeConfig,
    EffectType.SEND_MESSAGE: SendMessageConfig,
    EffectType.TIMEOUT_USER: TimeoutConfig,
    EffectType.SEND_ALERT: AlertConfig,
}
