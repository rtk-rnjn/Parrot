from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)

db = cluster['parrot_db']
collection = db['server_config']


async def guild_join(guild_id: int):
    post = {
        '_id': guild_id,
        'prefix': '$',
        'disabled_cogs': [],
        'disabled_cmds': [],
        'mod_role': None,
        'action_log': None,
        'mute_role': None,
    }
    collection.insert_one(post)
    


async def guild_update(guild_id: int, post: dict):
    _post = {
        '_id': guild_id,
    }

    new_post = {"$set": post}

    collection.update_one(_post, new_post)


async def guild_remove(guild_id: int):
    post = {
        '_id': guild_id,
    }

    collection.delete_one(post)
