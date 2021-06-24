import os
import pymongo

from pymongo import MongoClient
from utilities.congif import my_secret

cluster = MongoClient(
    f"mongodb+srv://ritikranjan:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]
collection = db["server_logging"]


async def logging_on_join(guild_id: int):
    post = {
        '_id': guild_id,
        'role_given': None,
        'channel_created': None,
        'vc_moved': None,
        'vc_left': None,
        'message_edited': None,
        'member_updated': None,
        'message_bulk_deleted': None,
        'server_updated': None,
        'channel_deleted': None,
        'role_created': None,
        'nickname_changed': None,
        'member_joined': None,
        'member_banned': None,
        'member_left': None,
        'role_updated': None,
        'vc_joined': None,
        'channel_updated': None,
        'message_deleted': None,
        'role_deleted': None,
        'member_unbanned': None,
        'role_removed': None
    }

    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def logging_update(guild_id: int, event: str, channel_id: int):

    arr = [
        'member_joined', 'member_left', 'member_banned', 'member_unbanned',
        'channel_created', 'channel_deleted', 'channel_updated',
        'role_created', 'role_updated', 'role_deleted', 'role_given',
        'role_removed', 'member_updated', 'nickname_changed', 'vc_joined',
        'vc_left', 'vc_moved', 'message_edited', 'message_deleted',
        'message_bulk_deleted', 'server_updated'
    ]

    if event.lower() in arr:
        get_post = {'_id': guild_id}
        new_post = {"$set": {event.lower(): channel_id}}

    try:
        collection.update_one(get_post, new_post)
        return "OK"
    except Exception as e:
        return str(e)


async def logging_on_remove(guild_id: int):
    post = {
        '_id': guild_id,
    }

    try:
        collection.delete_one(post)
        return "OK"
    except Exception as e:
        return str(e)
