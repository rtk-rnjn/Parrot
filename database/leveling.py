
from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]
collection = db["leveling"]


async def leveling_on_join(guild_id: int, user_id: int):
    post = {'_id': guild_id, 'user_id': user_id, 'xp': 10, 'level': 1}

    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def leveling_update(guild_id: int, xp: int, lvl: int):
    post = {
        '_id': guild_id,
    }
    new_post = {"$set": {'xp': xp, "lvl": lvl}}

    try:
        collection.update_one(post, new_post)
        return "OK"
    except Exception as e:
        return str(e)
