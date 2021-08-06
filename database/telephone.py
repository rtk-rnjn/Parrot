from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]
collection = db["telephone"]


async def telephone_on_join(guild_id: int):
    post = {
        "_id": guild_id,
        "channel": None,
        "pingrole": None,
        "is_line_busy": False,
        "memberping": None,
        "blocked": []
    }

    collection.insert_one(post)



async def telephone_update(guild_id: int, event: str, value):
    post = {
        "_id": guild_id,
    }

    new_post = {"$set": {event: value}}
    collection.update_one(post, new_post)



async def telephone_on_remove(guild_id: int):
    post = {
        "_id": guild_id,
    }

    collection.delete_one(post)

