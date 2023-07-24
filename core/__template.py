from __future__ import annotations

from typing import Any

post: dict[str, Any] = {
    "prefix": "$",
    "mute_role": None,
    "mod_role": None,
    "premium": False,
    "dj_role": None,
    "warn_expiry": None,
    "muted": [],
    "warn_count": 0,
    "suggestion_channel": None,
    "global_chat": {
        "enable": False,
        "channel_id": None,
        "ignore_role": [],
        "webhook": None,
    },
    "giveaway": [],
    "hub": None,
    "stats_channels": {
        "bots": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "members": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "channels": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "voice": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "text": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "categories": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "emojis": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "roles": {
            "channel_id": None,
            "channel_type": None,
            "template": None,
        },
        "role": [
            # {
            #   "role_id": None,
            #   "channel_id": None,
            #   "channel_type": None,
            #   "template": None
            # }
        ],
    },
    "starboard_config": {
        "is_locked": False,
        "limit": None,
        "ignore_channel": [],
        "max_duration": None,
        "channel": None,
        "can_self_star": True,
    },
    "leveling": {
        "enable": False,
        "channel": None,
        "reward": [
            # {
            #     "role": ROLE_ID,
            #     "lvl": LEVEL
            # }
        ],
        "ignore_role": [],
        "ignore_channel": [],
    },
    "telephone": {
        "enable": False,
        "channel_id": None,
        "ping_role": None,
        "is_line_busy": False,
        "member_ping": None,
        "blocked": [],
    },
    "cmd_config": {
        # "CMD_GLOBAL_ENABLE_{CMD_NAME}": BOOL,
        # "CMD_ROLE_ENABLE_{CMD_NAME}": [],
        # "CMD_ROLE_DISABLE_{CMD_NAME}": [],
        # "CMD_CHANNEL_ENABLE_{CMD_NAME}": [],
        # "CMD_CHANNEL_DISABLE_{CMD_NAME}": [],
        # "CMD_CATEGORY_ENABLE_{CMD_NAME}": [],
        # "CMD_CATEGORY_DISABLE_{CMD_NAME}": [],
    },
    "opts": {
        "gitlink_enabled": True,
        "equation_enabled": True,
    },
    "ticket_config": {
        "enable": False,
        "category": None,
        "message_id": None,
        "channel_id": None,
        "log": None,
        "pinged_roles": [],
        "verified_roles": [],
        "ticket_channel_ids": [],
        "ticket_counter": 0,
    },
    "autoresponder": {
        # "{RESPONDER_ID}": {
        #     "enabled": True,
        #     "response": "RESPONSE",
        #     "trigger": "TRIGGER",
        #     "ignore_role": [],
        #     "ignore_channel": [],
        # }
    },
    "default_defcon": {
        "enabled": False,
        "level": 0,
        "trustables": {
            "roles": [],
            "members": [],
            "members_with_admin": True,
        },
        "locked_channels": [],
        "hidden_channels": [],
        "broadcast": {
            "enabled": False,
            "channel": None,
        },
    },
}
