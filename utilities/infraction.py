from __future__ import annotations
from prettytable import PrettyTable
from core import Parrot
from utilities.database import parrot_db, warn_db

from typing import Optional


class Infraction:
    def __init__(self, bot: Parrot) -> None:
        self.bot = bot
        self._parrot_collection = parrot_db['server_config']
        self._warn_db = warn_db

    async def total_warns(self) -> int:
        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')

        collection = self._warn_db[str(self.guild.id)]
        data = await collection.find_one({'_id': self.user.id})
        if not data:
            return 0
        return len(data['warns'])

    async def total_warns_server(self) -> int:
        data = await self._parrot_collection.find_one({'_id': self.guild.id})
        try:
            return data['warn_count']
        except KeyError:
            await self._parrot_collection.update_one(
                {'_id': self.guild_id}, {'$set': {
                    'warn_count': 1
                }})
            return 0

    async def to_table(self, *, guild_id: int, user_id: int) -> str:
        my_table = PrettyTable(
            ['Case ID', 'AT', 'Reason', 'Moderator', 'Expires At'])
        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')

        collection = self._warn_db[str(guild_id)]
        data = await collection.find_one({'_id': user_id})
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

    async def make_warn(self,
                        *,
                        at: int,
                        reason: str,
                        mod: int,
                        expires_at: Optional[int],
                        guild_id: int,
                        user_id: int,
                        auto: Optional[bool] = True) -> dict:
        case_id = self.get_case_id()
        warn = {
            'case_id': case_id,
            'at': at,
            'reason': reason,
            'mod': mod,
            'expires_at': expires_at
        }
        await self._parrot_collection.update_one({'_id': guild_id},
                                                 {'$inc': {
                                                     'warn_count': 1
                                                 }})
        if auto:
            await self.add_warn(guild_id=guild_id, user_id=user_id, warn=warn)
        return warn

    async def add_warn(self, guild_id: int, user_id: int, warn: dict) -> dict:
        collection = self._warn_db[f"{guild_id}"]
        user_exists = await collection.find_one({'_id': user_id})
        if user_exists:
            await collection.insert_one({'_id': user_id, 'warns': [warn]})
        else:
            await collection.update_one({'_id': user_id},
                                        {'$addToSet': {
                                            'warns': warn
                                        }})
        return warn

    async def del_warn_all(self, guild_id: int, user_id: int) -> None:
        collection = self._warn_db[f"{guild_id}"]
        if user_exists := await collection.find_one({'_id': user_id}):
            await collection.update_one({'_id': user_id}, {'$set': {'warns': []}})

    async def del_warn_by_id(self, guild_id: int, user_id: int, case_id: int) -> None:
        collection = self._warn_db[f"{guild_id}"]
        await collection.update_one({'_id': user_id},
                                    {'$pull': {
                                        'warns.case_id': case_id
                                    }})

    async def del_warn_by_mod(self, guild_id: int, user_id: int, mod: int) -> None:
        collection = self._warn_db[f"{guild_id}"]
        await collection.update_one({'_id': user_id},
                                    {'$pull': {
                                        'warns.mod': mod
                                    }}, {'multi': True})
