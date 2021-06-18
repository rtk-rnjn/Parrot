import os
import pymongo

from pymongo import MongoClient

my_secret = os.environ['pass']

cluster = MongoClient(
		f"mongodb+srv://ritikranjan:{str(my_secret)}@cluster0.xjask.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
)
db = cluster["economy"]
collection = db["global_economy"]


async def telephone_on_join(guild_id: int):
		post = {
				"_id": guild_id,
				"channel": None,
				"pingrole": None,
				"is_line_busy": False,
				"memberping": None,
				"blocked": []
		}

		try:
				collection.insert_one(post)
				return "OK"
		except Exception as e:
				return str(e)


async def telephone_update(guild_id: int, event: str, value):
		post = {
				"_id": guild_id,
		}

		new_post = {"$set": {event: value}}
		try:
				collection.update_one(post, new_post)
				return "OK"
		except Exception as e:
				return str(e)


async def telephone_on_remove(guild_id:int):
		post = {
				"_id": guild_id,
			}

		try:
				collection.delete_one(post)
				return "OK"
		except Exception as e:
				return str(e)
