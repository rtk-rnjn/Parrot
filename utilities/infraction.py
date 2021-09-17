from async_property import async_property
from tabulate import tabulate
from prettytable import PrettyTable 
import datetime

class Infraction:
    def __init__(
            self, 
            bot: Parrot, 
            guild_id: int, 
            user_id: int, 
            reason: str,
            at: datetime.datetime,
            mod: int,
            expires_at: datetime.datetime=None):
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.reason = reason
        self.at = at 
        self.mod = mod 
        self.expires_at = expires_at
        self._parrot_collection = None
        self._warn_db = None

    @async_property
    async def total_warns(self) -> int:
        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')
        
        collection = self._warn_db[str(self.guild.id)]
        data = collection.find_one({'_id': self.user.id})
        if not data:
            return 0
        else:
            return len(data['warns'])

    @async_property
    async def total_warns_server(self) -> int:
        if self._parrot_collection is None:
            parrot_db = await self.bot.db('parrot_db')
            self._parrot_collection = parrot_db['server_config']
        
        data = await self._parrot_collection.find_one({'_id': self.guild.id})
        try:
            return data['warn_count']
        except KeyError:
            await self._parrot_collection.update_one({'_id': guild_id}, {'$set':{'warn_count': 1}})
            return 0
    
    @async_property
    async def to_table(self) -> str:
        my_table = PrettyTable(['Case ID', 'AT', 'Reason', 'Moderator', 'Expires At'])
        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')
        
        collection = self._warn_db[str(self.guild.id)]
        data = collection.find_one({'_id': self.user.id})
        if not data:
            return str(my_table)
        if len(data['warns']) == 0:
            return str(my_table)
        
        for data in data['warns']:
            my_table.add_row(data['case_id'], data['at'], data['reason'], data['mod'], data['expires_at'])

        return str(my_table)

    async def get_case_id(self) -> int:
        if self._parrot_collection is None:
            parrot_db = await self.bot.db('parrot_db')
            self._parrot_collection = parrot_db['server_config']
        
        if self._warn_db is None:
            self._warn_db = await self.bot.db('warn_db')
        
        data = await collection.find_one({'_id': self.guild_id})
        try:
            return data['warn_count']
        except KeyError:
            await self._parrot_collection.update_one({'_id': guild_id}, {'$set':{'warn_count': 1}})
            return 1
        
    async def _make_warn(self) -> dict:
        case_id = self.get_case_id()
        warn = {
            'case_id': case_id,
            'at': self.at,
            'reason': self.reason,
            'mod': self.mod,
            'expires_at': self.expires_at
        }
        await self._parrot_collection.update_one({'_id': self.guild_id}, {'$inc': {'warn_count': 1}})
        return warn

    async def _add_warn(self) -> None:
        warn = self._make_warn()
        collection = self._warn_db[f"{self.guild_id}"]
        user_exists = await collection.find_one({'_id': self.user_id})
        if user_exists:
            await collection.insert_one({'_id': self.user_id, 'warns': [warn]})
        else:
            await collection.update_one({'_id': self.user_id}, {'$addToSet': {'warns': warn}})
    
    async def _del_warn_all(self) -> None:
        collection = self._warn_db[f"{self.guild_id}"]
        user_exists = await collection.find_one({'_id': self.user_id})
        if not user_exists:
            return
        await collection.update_one({'_id': self.user_id}, {'$set': {'warns': []}})
    
    async def _del_warn_by_id(self, case_id: int) -> None:
        collection = self._warn_db[f"{self.guild_id}"]
        await collection.update_one({'_id': self.user_id}, {'$pull': {'warns': {'case_id': case_id}}})
    
    async def _del_warn_by_mod(self, mod: int) -> None:
        collection = self._warn_db[f"{self.guild_id}"]
        await collection.update_one({'_id': self.user_id}, {'$pull': {'warns': {'mod': mod}}}, {'multi': True})