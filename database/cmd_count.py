from pymongo import MongoClient
from utilities.config import my_secret

cluster = MongoClient(
    f"mongodb+srv://user:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["parrot_db"]
collection = db["cmd_count"]


async def if_not_exists(cmd: str, count: int):
    post = {'_id': cmd, 'count': count}
    try:
        collection.insert_one(post)
        return "OK"
    except Exception as e:
        return str(e)


async def increment(cmd: str):
    pre_post = {'_id': cmd}
    try:
        collection.update_one(pre_post, {'$inc': {'count': 1}})
        return 'OK'
    except Exception as e:
        return str(e)
