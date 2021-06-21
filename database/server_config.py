import os
import pymongo

from pymongo import MongoClient

my_secret = os.environ['pass']

cluster = MongoClient(
    f"mongodb+srv://ritikranjan:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

db = cluster['parrot_db']
collection = db['server_config']


async def guild_join(guild_id: int):
    post = {
        '_id': guild_id,
        'prefix': '$',
        'disabled_cogs': [],
        'disabled_cmd': [],
        'mod_role': [],
        'action_log': None
    }

    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def guild_update(guild_id: int, event: str, value):
    post = {
        '_id': guild_id,
    }

    new_post = {"$set": {event: value}}

    try:
        collection.update_one(post, new_post)
        return "OK"
    except Exception as e:
        return str(e)


async def guild_remove(guild_id: int):
    post = {
        '_id': guild_id,
    }

    try:
        collection.delete_one(post)
        return "OK"
    except Exception as e:
        return str(e)
