from __future__ import annotations

import json
from typing import Literal, cast

from discord.utils import MISSING
from pymongo.errors import DuplicateKeyError

from ..cache_keys import RedisKeys
from ..mixin import DatabaseMixin
from ..models import AutomodConfig, ConditionDict, EffectDict, RuleDict, TriggerDict

# Stored in the rule-name set when a guild has no rules, so an empty result
# is cached and we don't hit MongoDB on every message.
_NO_RULES = "\x00none"

AutomodListName = Literal["word_denylist", "word_allowlist", "website_denylist", "website_allowlist"]


class _GuildAutomodMixin(DatabaseMixin):
    async def __cache_rules(self, *, guild_id: int, rules: list[RuleDict]) -> None:
        rules_key = RedisKeys.GUILD_AUTOMOD_RULES.format(guild_id=guild_id)
        async with self.redis_client.pipeline(transaction=True) as pipe:
            if not rules:
                pipe.sadd(rules_key, _NO_RULES)
            for rule in rules:
                fmt = {"guild_id": guild_id, "rule_name": rule["name"]}
                pipe.srem(rules_key, _NO_RULES)
                pipe.sadd(rules_key, rule["name"])
                pipe.set(RedisKeys.GUILD_AUTOMOD_RULE_TRIGGER.format(**fmt), json.dumps(rule["trigger"]))
                pipe.set(RedisKeys.GUILD_AUTOMOD_RULE_CONDITIONS.format(**fmt), json.dumps(rule["conditions"]))
                pipe.set(RedisKeys.GUILD_AUTOMOD_RULE_EFFECTS.format(**fmt), json.dumps(rule["effects"]))
                pipe.set(RedisKeys.GUILD_AUTOMOD_RULE_ENABLED.format(**fmt), int(rule["enabled"]))
                pipe.set(RedisKeys.GUILD_AUTOMOD_RULE_PRIORITY.format(**fmt), rule["priority"])
            await pipe.execute()

    async def __read_cached_rules(self, *, guild_id: int, names: list[str]) -> list[RuleDict] | None:
        """Return rules from Redis, or None if any field of any rule is missing."""
        async with self.redis_client.pipeline(transaction=False) as pipe:
            for name in names:
                fmt = {"guild_id": guild_id, "rule_name": name}
                pipe.get(RedisKeys.GUILD_AUTOMOD_RULE_TRIGGER.format(**fmt))
                pipe.get(RedisKeys.GUILD_AUTOMOD_RULE_CONDITIONS.format(**fmt))
                pipe.get(RedisKeys.GUILD_AUTOMOD_RULE_EFFECTS.format(**fmt))
                pipe.get(RedisKeys.GUILD_AUTOMOD_RULE_ENABLED.format(**fmt))
                pipe.get(RedisKeys.GUILD_AUTOMOD_RULE_PRIORITY.format(**fmt))
            values = await pipe.execute()

        rules: list[RuleDict] = []
        for index, name in enumerate(names):
            trigger, conditions, effects, enabled, priority = values[index * 5 : index * 5 + 5]
            if None in (trigger, conditions, effects, enabled, priority):
                return None
            rules.append(
                {
                    "name": name,
                    "enabled": bool(int(enabled)),
                    "trigger": json.loads(trigger),
                    "conditions": json.loads(conditions),
                    "effects": json.loads(effects),
                    "priority": int(priority),
                }
            )
        return rules

    async def __invalidate_rules_cache(self, *, guild_id: int) -> None:
        """Drop every cached rule for a guild.

        Always invalidates the whole guild: if only one rule were removed, the
        name set could look complete while missing a rule.
        """
        rules_key = RedisKeys.GUILD_AUTOMOD_RULES.format(guild_id=guild_id)
        names = await self.redis_client.smembers(rules_key)
        keys = [rules_key]
        for name in names:
            if name == _NO_RULES:
                continue
            fmt = {"guild_id": guild_id, "rule_name": name}
            keys += [
                RedisKeys.GUILD_AUTOMOD_RULE_TRIGGER.format(**fmt),
                RedisKeys.GUILD_AUTOMOD_RULE_CONDITIONS.format(**fmt),
                RedisKeys.GUILD_AUTOMOD_RULE_EFFECTS.format(**fmt),
                RedisKeys.GUILD_AUTOMOD_RULE_ENABLED.format(**fmt),
                RedisKeys.GUILD_AUTOMOD_RULE_PRIORITY.format(**fmt),
            ]
        await self.redis_client.delete(*keys)

    async def get_automod_rules(self, guild_id: int, /) -> list[RuleDict]:
        """Get all rules for a guild, highest priority first."""
        rules_key = RedisKeys.GUILD_AUTOMOD_RULES.format(guild_id=guild_id)
        names = await self.redis_client.smembers(rules_key)
        if names:
            real_names = sorted(n for n in names if n != _NO_RULES)
            if not real_names:
                return []
            cached = await self.__read_cached_rules(
                guild_id=guild_id,
                names=[(real.decode("utf-8") if isinstance(real, bytes) else real) for real in real_names],
            )
            if cached is not None:
                return sorted(cached, key=lambda rule: rule["priority"], reverse=True)

        guild = await self.guilds_collection.find_one({"_id": guild_id}, {"automod.rules": 1})
        rules = cast(list[RuleDict], (guild or {}).get("automod", {}).get("rules", []))

        await self.__invalidate_rules_cache(guild_id=guild_id)
        await self.__cache_rules(guild_id=guild_id, rules=rules)
        return sorted(rules, key=lambda rule: rule["priority"], reverse=True)

    async def get_enabled_automod_rules(self, guild_id: int, /) -> list[RuleDict]:
        """Get only enabled rules, highest priority first (use this in on_message)."""
        return [rule for rule in await self.get_automod_rules(guild_id) if rule["enabled"]]

    async def get_automod_rule(self, *, guild_id: int, name: str) -> RuleDict | None:
        for rule in await self.get_automod_rules(guild_id):
            if rule["name"] == name:
                return rule
        return None

    async def is_automod_rule_present(self, *, guild_id: int, name: str) -> bool:
        return await self.get_automod_rule(guild_id=guild_id, name=name) is not None

    async def create_automod_rule(
        self,
        *,
        guild_id: int,
        rule: RuleDict,
    ) -> bool:
        """Create a rule. Returns False if a rule with this name already exists."""
        try:
            result = await self.guilds_collection.update_one(
                {"_id": guild_id, "automod.rules.name": {"$ne": rule["name"]}},
                {"$push": {"automod.rules": rule}},
                upsert=True,
            )
        except DuplicateKeyError:
            # Guild document exists and already has a rule with this name.
            return False

        if result.matched_count == 0 and result.upserted_id is None:
            return False

        await self.__invalidate_rules_cache(guild_id=guild_id)
        return True

    async def edit_automod_rule(
        self,
        *,
        guild_id: int,
        name: str,
        new_name: str = MISSING,
        enabled: bool = MISSING,
        trigger: TriggerDict = MISSING,
        conditions: list[ConditionDict] = MISSING,
        effects: list[EffectDict] = MISSING,
        priority: int = MISSING,
    ) -> bool:
        """Edit a rule. Returns False if it doesn't exist, nothing changed, or new_name is taken."""
        updates = {}
        for field, value in (
            ("name", new_name),
            ("enabled", enabled),
            ("trigger", trigger),
            ("conditions", conditions),
            ("effects", effects),
            ("priority", priority),
        ):
            if value is not MISSING:
                updates[f"automod.rules.$.{field}"] = value
        if not updates:
            return False

        query = {"_id": guild_id, "automod.rules": {"$elemMatch": {"name": name}}}
        if new_name is not MISSING and new_name != name:
            query["automod.rules.name"] = {"$ne": new_name}

        result = await self.guilds_collection.update_one(query, {"$set": updates})
        if result.matched_count == 0:
            return False

        await self.__invalidate_rules_cache(guild_id=guild_id)
        return result.modified_count > 0

    async def set_automod_rule_enabled(self, *, guild_id: int, name: str, enabled: bool) -> bool:
        return await self.edit_automod_rule(guild_id=guild_id, name=name, enabled=enabled)

    async def delete_automod_rule(self, *, guild_id: int, name: str) -> bool:
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, "automod.rules": {"$elemMatch": {"name": name}}},
            {"$pull": {"automod.rules": {"name": name}}},
        )
        if result.modified_count > 0:
            await self.__invalidate_rules_cache(guild_id=guild_id)
        return result.modified_count > 0

    async def get_automod_config(self, guild_id: int, /) -> AutomodConfig | None:
        guild = await self.guilds_collection.find_one({"_id": guild_id}, {"automod": 1})
        if guild is None:
            return None
        return guild.get("automod")

    async def get_automod_list(self, *, guild_id: int, list_name: AutomodListName) -> list[str]:
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, f"automod.{list_name}": {"$exists": True}},
            {f"automod.{list_name}": 1},
        )
        if guild is None:
            return []

        return guild["automod"][list_name]

    async def add_automod_list_item(self, *, guild_id: int, list_name: AutomodListName, item: str) -> bool:
        result = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$addToSet": {f"automod.{list_name}": item}},
            upsert=True,
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def remove_automod_list_item(self, *, guild_id: int, list_name: AutomodListName, item: str) -> bool:
        result = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {f"automod.{list_name}": item}},
        )
        return result.modified_count > 0

    @staticmethod
    def __is_valid_custom_list_name(name: str) -> bool:
        # "." and a leading "$" are unsafe in MongoDB field paths.
        return bool(name) and "." not in name and not name.startswith("$")

    async def create_automod_custom_list(self, *, guild_id: int, list_name: str, items: list[str] | None = None) -> bool:
        if not self.__is_valid_custom_list_name(list_name):
            return False
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, f"automod.custom_lists.{list_name}": {"$exists": False}},
            {"$set": {f"automod.custom_lists.{list_name}": items or []}},
            upsert=True,
        )
        return result.modified_count > 0 or result.upserted_id is not None

    async def delete_automod_custom_list(self, *, guild_id: int, list_name: str) -> bool:
        if not self.__is_valid_custom_list_name(list_name):
            return False
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, f"automod.custom_lists.{list_name}": {"$exists": True}},
            {"$unset": {f"automod.custom_lists.{list_name}": ""}},
        )
        return result.modified_count > 0

    async def get_automod_custom_list(self, *, guild_id: int, list_name: str) -> list[str] | None:
        if not self.__is_valid_custom_list_name(list_name):
            return None
        guild = await self.guilds_collection.find_one(
            {"_id": guild_id, f"automod.custom_lists.{list_name}": {"$exists": True}},
            {f"automod.custom_lists.{list_name}": 1},
        )
        if guild is None:
            return None
        return guild["automod"]["custom_lists"][list_name]

    async def add_automod_custom_list_item(self, *, guild_id: int, list_name: str, item: str) -> bool:
        if not self.__is_valid_custom_list_name(list_name):
            return False
        result = await self.guilds_collection.update_one(
            {"_id": guild_id, f"automod.custom_lists.{list_name}": {"$exists": True}},
            {"$addToSet": {f"automod.custom_lists.{list_name}": item}},
        )
        return result.modified_count > 0

    async def remove_automod_custom_list_item(self, *, guild_id: int, list_name: str, item: str) -> bool:
        if not self.__is_valid_custom_list_name(list_name):
            return False
        result = await self.guilds_collection.update_one(
            {"_id": guild_id},
            {"$pull": {f"automod.custom_lists.{list_name}": item}},
        )
        return result.modified_count > 0
