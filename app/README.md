# Rest API for Parrot - Discord Bot

## Endpoints

### GET /

Returns `{"status": "running"}`

---

### GET /get/guilds

Returns a list of guilds the bot is in.

**Example Response**

```json
{
    "status": "success",
    "guilds": [
        {
            "id": ...,
            "name": ...,
            "icon": ...,
            "owner": {
                "id": ...,
                "name": ...,
                "avatar_url": ...,
            },
            "icon_url": ...,
            "member_count": ...,
            "channels": [],
            "roles": [],
            "emojis": [],
            "threads": []
        },
        ...,
    ]
}
```

### GET /get/guilds/{guild_id}

Returns a array of one element of guild object for the given guild id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/channels

Returns a list of channels in the given guild id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/channels/{channel_id}

Returns a array of one element of channel object for the given channel id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/roles

Returns a list of roles in the given guild id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/roles/{role_id}

Returns a array of one element of role object for the given role id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/members

Returns a list of members in the given guild id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/members/{member_id}

Returns a array of one element of member object for the given member id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/emojis

Returns a list of emojis in the given guild id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/emojis/{emoji_id}

Returns a array of one element of emoji object for the given emoji id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/threads

Returns a list of threads in the given guild id. If the bot is not in the guild, returns an empty array.

### GET /get/guilds/{guild_id}/threads/{thread_id}

Returns a array of one element of thread object for the given thread id. If the bot is not in the guild, returns an empty array.

---

### GET /get/users

Returns a list of users the bot can see.

### GET /get/users/{user_id}

Returns a array of one element of user object for the given user id. If the bot can't see the user, returns an empty array.

---

### GET /get/messages/{channel_id}/{message_id}

Return message object for the given channel id and message id. If the bot can't see the channel, returns {}

---

### GET /get/commands

Returns a list of commands the bot has

### GET /get/commands/{command_name}

Returns a array of one element of command object for the given command name. If the bot doesn't have the command, returns an empty array.

<!-- TODO: Complete README -->