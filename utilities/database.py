from __future__ import annotations

from utilities.config import my_secret
import motor.motor_asyncio

from utilities.log import get_logger


cluster = motor.motor_asyncio.AsyncIOMotorClient(
    f"mongodb+srv://user:{my_secret}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

parrot_db = cluster["parrot_db"]
msg_db = cluster["msg_db"]
tags = cluster["tags"]
todo = cluster["todo"]
enable_disable = cluster["enable_disable"]
warn_db = cluster["warn_db"]


async def cmd_increment(cmd: str) -> None:
    collection = parrot_db["cmd_count"]
    await collection.update_one({"_id": cmd}, {"$inc": {"count": 1}}, upsert=True)


async def telephone_update(guild_id: int, event: str, value) -> None:
    collection = parrot_db["telephone"]
    if _ := await collection.find_one({"_id": guild_id}):
        await collection.update_one({"_id": guild_id}, {"$set": {event: value}})
        return

    post = {
        "_id": guild_id,
        "channel": None,
        "pingrole": None,
        "is_line_busy": False,
        "memberping": None,
        "blocked": [],
    }
    await collection.insert_one(post)


async def ticket_update(guild_id: int, post: dict):
    collection = parrot_db["ticket"]
    data = await collection.find_one({"_id": guild_id})
    if not data:
        await collection.insert_one(
            {
                "_id": guild_id,
                "ticket_counter": 0,
                "valid_roles": [],
                "pinged_roles": [],
                "ticket_channel_ids": [],
                "verified_roles": [],
                "message_id": None,
                "log": None,
                "category": None,
                "channel_id": None,
            }
        )

    await collection.update_one({"_id": guild_id}, {"$set": post})


async def guild_join(guild_id: int):
    collection = parrot_db["server_config"]
    post = {
        "_id": guild_id,
        "prefix": "$",
        "mod_role": None,
        "action_log": None,
        "mute_role": None,
        "warn_count": 0,
    }
    await collection.insert_one(post)

    collection = parrot_db["global_chat"]
    post = {
        "_id": guild_id,
        "channel_id": None,
        "webhook": None,
        "ignore-role": None,
    }
    await collection.insert_one(post)

    collection = parrot_db["telephone"]
    post = {
        "_id": guild_id,
        "channel": None,
        "pingrole": None,
        "is_line_busy": False,
        "memberping": None,
        "blocked": [],
    }
    await collection.insert_one(post)

    collection = parrot_db["ticket"]
    post = {
        "_id": guild_id,
        "ticket_counter": 0,
        "valid_roles": [],
        "pinged_roles": [],
        "ticket_channel_ids": [],
        "verified_roles": [],
        "message_id": None,
        "log": None,
        "category": None,
        "channel_id": None,
    }
    await collection.insert_one(post)


async def guild_remove(guild_id: int):
    collection = parrot_db["server_config"]
    await collection.delete_one({"_id": guild_id})

    collection = parrot_db[f"{guild_id}"]
    await collection.drop()

    collection = parrot_db["global_chat"]
    await collection.delete_one({"_id": guild_id})

    collection = parrot_db["telephone"]
    await collection.delete_one({"_id": guild_id})

    collection = parrot_db["ticket"]
    await collection.delete_one({"_id": guild_id})

    collection = enable_disable[f"{guild_id}"]
    await collection.drop()


async def ban(user_id: int, **kw):
    collection = parrot_db["banned_users"]
    await collection.insert_one({"_id": user_id, **kw})


async def unban(user_id: int, **kw):
    collection = parrot_db["banned_users"]
    await collection.delete_one({"_id": user_id,})