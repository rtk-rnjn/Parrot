from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]
collection = db["ticket"]


async def ticket_on_join(guild_id: int):
    post = {
        "_id": guild_id,
        "ticket-counter": 0,
        "valid-roles": [],
        "pinged-roles": [],
        "ticket-channel-ids": [],
        "verified-roles": [],
        "message_id": None,
        "log": None,
        "category": None,
        "channel_id": None
    }

    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def ticket_update(guild_id: int, post):

    try:
        collection.update_one({'_id': guild_id}, {"$set": post})
        return "OK"
    except Exception as e:
        return str(e)


async def ticket_on_remove(guild_id: int):
    post = {
        "_id": guild_id,
    }

    try:
        collection.delete_one(post)
        return "OK"
    except Exception as e:
        return str(e)
