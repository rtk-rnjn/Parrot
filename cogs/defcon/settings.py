import discord

# This is a dictionary of all the defcon settings. You can add more defcon levels (if premium)
DEFCON_SETTINGS = {
    1: {
        "name": "DEFCON 1",
        "description": "Maximum readiness. Server lockdown. Includes all settings from DEFCON 2",
        "color": discord.Color.red(),
        "SETTINGS": {
            "ALLOW_INVITE_CREATE": False,
            "ALLOW_SERVER_JOIN": False,
            "HIDE_CHANNELS": True,
            "LOCK_VOICE_CHANNELS": True,
            "LOCK_TEXT_CHANNELS": True,
            "LOCK_ASSIGN_ROLES": True,
            "ALLOW_CREATE_ROLE": False,
        },
    },
    2: {
        "name": "DEFCON 2",
        "description": "Lockdown. No one can join server. All channels will remain visible, no moderator can assign roles, no one can create roles",
        "color": discord.Color.orange(),
        "SETTINGS": {
            "ALLOW_INVITE_CREATE": False,
            "ALLOW_SERVER_JOIN": False,
            "HIDE_CHANNELS": False,
            "LOCK_VOICE_CHANNELS": True,
            "LOCK_TEXT_CHANNELS": True,
            "LOCK_ASSIGN_ROLES": True,
            "ALLOW_CREATE_ROLE": False,
        },
    },
    3: {
        "name": "DEFCON 3",
        "description": "Strict slowmode. Not allowing sending discord invites, images, gif(s), excess emotes. All channels will remain visible, but lock voice channels",
        "color": discord.Color.gold(),
        "SETTINGS": {
            "ALLOW_INVITE_CREATE": True,
            "ALLOW_SERVER_JOIN": True,
            "HIDE_CHANNELS": False,
            "LOCK_VOICE_CHANNELS": True,
            "LOCK_TEXT_CHANNELS": False,
            "LOCK_ASSIGN_ROLES": False,
            "SLOWMODE": True,
            "SLOWMODE_TIME": 10,
        },
    },
    4: {
        "name": "DEFCON 4",
        "description": "Moderate slowmode. No one can join server, not allowing sending discord invites. All channels will remain visible",
        "color": discord.Color.green(),
        "SETTINGS": {
            "ALLOW_INVITE_CREATE": True,
            "ALLOW_SERVER_JOIN": True,
            "HIDE_CHANNELS": False,
            "LOCK_VOICE_CHANNELS": False,
            "LOCK_TEXT_CHANNELS": False,
            "LOCK_ASSIGN_ROLES": False,
            "SLOWMODE": True,
            "SLOWMODE_TIME": 3,
        },
    },
    5: {
        "name": "DEFCON 5",
        "description": "No slowmode. No one can join server, not allowing sending discord invites. All channels will remain visible. Peaceful mode",
        "color": discord.Color.blue(),
        "SETTINGS": {
            "ALLOW_INVITE_CREATE": True,
            "ALLOW_SERVER_JOIN": True,
            "HIDE_CHANNELS": False,
            "LOCK_VOICE_CHANNELS": False,
            "LOCK_TEXT_CHANNELS": False,
            "LOCK_ASSIGN_ROLES": False,
            "SLOWMODE": False,
            "SLOWMODE_TIME": 0,
        },
    },
}


# Actions

ACTION_SETTINGS = {
    "ALLOW_INVITE_CREATE": {
        "name": "Allow Invite Creation",
        "description": "Allow users to create discord invites",
        "default": True,
    },
    "ALLOW_CREATE_ROLE": {
        "name": "Allow Create Role",
        "description": "Allow users to create roles",
        "default": True,
    },
    "ALLOW_SERVER_JOIN": {
        "name": "Allow Server Join",
        "description": "Allow users to join the server",
        "default": True,
    },
    "HIDE_CHANNELS": {
        "name": "Hide Channels",
        "description": "Hide all channels from users",
        "default": False,
    },
    "LOCK_VOICE_CHANNELS": {
        "name": "Lock Voice Channels",
        "description": "Lock all voice channels from users",
        "default": False,
    },
    "LOCK_TEXT_CHANNELS": {
        "name": "Lock Text Channels",
        "description": "Lock all text channels from users",
        "default": False,
    },
    "LOCK_ASSIGN_ROLES": {
        "name": "Lock Assign Roles",
        "description": "Lock all roles from users",
        "default": False,
    },
    "SLOWMODE": {
        "name": "Slowmode",
        "description": "Enable slowmode",
        "default": False,
    },
    "SLOWMODE_TIME": {
        "name": "Slowmode Time",
        "description": "Slowmode time in seconds",
        "default": 0,
    },
}

DEFAULT_TRUSTABLES = {
    "roles": [],
    "members": [],
    "members_with_admin": True,
    "members_above_bot_role": False,
}
