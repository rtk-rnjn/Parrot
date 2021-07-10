from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]
collection = db["msg_count"]


async def if_not_exists(guild_id: int, user_id: int, count: int):
    post = {'_id': guild_id, 'user_id': user_id, 'count': count}
    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def increment(guild_id: int, user_id: int):
    pre_post = {'_id': guild_id, 'user_id': user_id}
    try:
        collection.update_one(pre_post, {'$inc': {'count': 1}})
        return 'OK'
    except Exception as e:
        return str(e)
