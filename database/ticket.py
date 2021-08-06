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

    collection.insert_one(post)


async def ticket_update(guild_id: int, post):
    collection.update_one({'_id': guild_id}, {"$set": post})


async def ticket_on_remove(guild_id: int):
    post = {
        "_id": guild_id,
    }

    collection.delete_one(post)
