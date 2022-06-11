from __future__ import annotations
from typing import Any, Dict

post: Dict[str, Any] = {
    "prefix": "$",
    "mute_role": None,
    "mod_role": None,
    "premium": False,
    "warn_auto": [],
    "counting": None,
    "oneword": None,
    "autowarn": [],
    "warn_count": 0,
    "suggestion_channel": None,
    "vc": None,
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
            #   "template": None
            # }
        ],
    },
    "starboard": {
        "is_locked": False,
        "limit": None,
        "ignore_channel": [],
        "max_duration": None,
        "channel": None,
    },
    "leveling": {
        "enable": False,
        "channel": None,
        "reward": [
            # "role": ROLE_ID,
            # "lvl": LEVEL
        ],
        "ignore_role": [],
        "ignore_channel": [],
    },
    "automod": {
        "spam": {
            "enable": False,
            "channel": [],
            "autowarn": {
                "enable": False,
                "count": None,
                "to_delete": False,
                "punish": {"type": None, "duration": None},
            },
        },
        "antilinks": {
            "enable": False,
            "channel": [],
            "whitelist": [],
            "autowarn": {
                "enable": False,
                "count": None,
                "to_delete": False,
                "punish": {"type": None, "duration": None},
            },
        },
        "profanity": {
            "enable": False,
            "words": [],
            "channel": [],
            "autowarn": {
                "enable": False,
                "count": None,
                "to_delete": False,
                "punish": {"type": None, "duration": None},
            },
        },
        "caps": {
            "enable": False,
            "limit": None,
            "channel": [],
            "autowarn": {
                "enable": False,
                "count": None,
                "to_delete": False,
                "punish": {"type": None, "duration": None},
            },
        },
        "emoji": {
            "enable": False,
            "limit": None,
            "channel": [],
            "autowarn": {
                "enable": False,
                "count": None,
                "to_delete": False,
                "punish": {"type": None, "duration": None},
            },
        },
    },
}
