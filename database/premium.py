import os
import pymongo

from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://ritikranjan:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["premium"]
collection_guild = db["premium_guild"]


async def premium_add_guild(guild_id: int):
    post = {
        "_id": guild_id,
    }

    try:
        collection_guild.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def premium_del_guild(guild_id: int):
    post = {
        "_id": guild_id,
    }

    try:
        collection_guild.delete_one(post)
        return "OK"
    except Exception as e:
        return str(e)


collection_user = db["premium_user"]


async def premium_add_user(user_id: int):
    post = {
        "_id": user_id,
    }

    try:
        collection_user.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def premium_del_user(user_id: int):
    post = {
        "_id": user_id,
    }

    try:
        collection_user.delete_one(post)
        return "OK"
    except Exception as e:
        return str(e)
