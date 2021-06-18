import os
import pymongo

from pymongo import MongoClient

my_secret = os.environ['pass']

cluster = MongoClient(
    f"mongodb+srv://ritikranjan:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
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
        "verified-roles": []
    }

    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def ticket_update(guild_id: int, event: str, value):

    post = collection.find_one({'_id': guild_id})

    new_post = {"$set": {event: value}}

    try:
        collection.update_one(post, new_post)
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
