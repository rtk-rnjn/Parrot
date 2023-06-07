from __future__ import annotations

from typing import Any, Dict

post: Dict[str, Any] = {
    "prefix": "$",
    "mute_role": None,
    "mod_role": None,
    "premium": False,
    "warn_auto": [
        # {
        #     "count": int,
        #     "action": str,
        #     "duration": str,
        # }
    ],
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
        "bots": {"channel_id": None, "channel_type": None, "template": None},
        "members": {"channel_id": None, "channel_type": None, "template": None},
        "channels": {"channel_id": None, "channel_type": None, "template": None},
        "voice": {"channel_id": None, "channel_type": None, "template": None},
        "text": {"channel_id": None, "channel_type": None, "template": None},
        "categories": {"channel_id": None, "channel_type": None, "template": None},
        "emojis": {"channel_id": None, "channel_type": None, "template": None},
        "roles": {"channel_id": None, "channel_type": None, "template": None},
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
    "cmd_config": [
        # {
        #     "cmd_enable": False,
        #     "cmd_name": None,
        #     "role_out": [],
        #     "channel_out": [],
        #     "role_in": [],
        #     "channel_in": [],
        # }
    ],
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
}
