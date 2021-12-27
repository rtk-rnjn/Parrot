from __future__ import annotations

from async_property import async_property

from tabulate import tabulate
from prettytable import PrettyTable
from core import Parrot
from utilities.database import parrot_db
import datetime

from typing import Optional


class Infraction:
    def __init__(self, bot: Parrot):
        self.bot = bot
        self._parrot_collection = parrot_db['server_config']
        self._warn_db = None

    async def total_warns(self) -> int:
        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')

        collection = self._warn_db[str(self.guild.id)]
        data = await collection.find_one({'_id': self.user.id})
        if not data:
            return 0
        else:
            return len(data['warns'])

    async def total_warns_server(self) -> int:
        if self._parrot_collection is None:
            parrot_db = await self.bot.db('parrot_db')
            self._parrot_collection = parrot_db['server_config']

        data = await self._parrot_collection.find_one({'_id': self.guild.id})
        try:
            return data['warn_count']
        except KeyError:
            await self._parrot_collection.update_one(
                {'_id': self.guild_id}, {'$set': {
                    'warn_count': 1
                }})
            return 0

    async def to_table(self) -> str:
        my_table = PrettyTable(
            ['Case ID', 'AT', 'Reason', 'Moderator', 'Expires At'])
        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')

        collection = self._warn_db[str(self.guild.id)]
        data = await collection.find_one({'_id': self.user.id})
        if not data:
            return str(my_table)
        if len(data['warns']) == 0:
            return str(my_table)

        for data in data['warns']:
            my_table.add_row(data['case_id'], data['at'], data['reason'],
                             data['mod'], data['expires_at'])

        return str(my_table)

    async def get_case_id(self) -> int:
        if self._parrot_collection is None:
            parrot_db = await self.bot.db('parrot_db')
            self._parrot_collection = parrot_db['server_config']

        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')

        data = await self._parrot_collection.find_one({'_id': self.guild_id})
        try:
            return data['warn_count']
        except KeyError:
            await self._parrot_collection.update_one(
                {'_id': self.guild_id}, {'$set': {
                    'warn_count': 1
                }})
            return 1

    async def make_warn(self, *, at: int, reason: str, mod: int, expires_at: Optional[int]) -> dict:
        case_id = self.get_case_id()
        warn = {
            'case_id': case_id,
            'at': at,
            'reason': reason,
            'mod': mod,
            'expires_at': expires_at
        }
        await self._parrot_collection.update_one({'_id': self.guild_id},
                                                 {'$inc': {
                                                     'warn_count': 1
                                                 }})
        return warn

    async def add_warn(self) -> dict:
        warn = self._make_warn()
        collection = self._warn_db[f"{self.guild_id}"]
        user_exists = await collection.find_one({'_id': self.user_id})
        if user_exists:
            await collection.insert_one({'_id': self.user_id, 'warns': [warn]})
        else:
            await collection.update_one({'_id': self.user_id},
                                        {'$addToSet': {
                                            'warns': warn
                                        }})
        return warn

    async def del_warn_all(self) -> None:
        collection = self._warn_db[f"{self.guild_id}"]
        user_exists = await collection.find_one({'_id': self.user_id})
        if not user_exists:
            return
        await collection.update_one({'_id': self.user_id},
                                    {'$set': {
                                        'warns': []
                                    }})

    async def del_warn_by_id(self, case_id: int) -> None:
        collection = self._warn_db[f"{self.guild_id}"]
        await collection.update_one({'_id': self.user_id},
                                    {'$pull': {
                                        'warns.case_id': case_id
                                        }
                                    })

    async def del_warn_by_mod(self, mod: int) -> None:
        collection = self._warn_db[f"{self.guild_id}"]
        await collection.update_one({'_id': self.user_id},
                                    {'$pull': {
                                        'warns.mod': mod
                                        }
                                    }, {'multi': True})
