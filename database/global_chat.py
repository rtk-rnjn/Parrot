from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]
collection = db["global_chat"]


async def gchat_on_join(guild_id: int):
    post = {
        '_id': guild_id,
        'channel_id': None,
        'webhook': None,
        'ignore-role': None,
    }

    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def gchat_update(guild_id: int, post: dict):
    
    try:
        collection.update_one({'_id': guild_id}, {'$set': post})
        return "OK"
    except Exception as e:
        return str(e)


async def gchat_on_remove(guild_id: int):
    post = {
        '_id': guild_id,
    }

    try:
        collection.delete_one(post)
        return "OK"
    except Exception as e:
        return str(e)
