# Database Layer

The database layer is exposed through `DatabaseManager`, which is attached to the bot as `bot.database`. It is a facade built from small mixins so each domain keeps its storage operations together.

## Layout

```text
core/utils/database/
|-- __init__.py           DatabaseManager, connections, lifecycle, registration
|-- models.py             TypedDict models for MongoDB documents
|-- cache_keys.py         Redis key templates
|-- mixin.py              Shared DatabaseMixin contract
|-- scam_links.py         Scam-link cache operations
|-- bot/                  Reserved bot-wide operations
|-- guild/                Guild configuration and feature operations
`-- user/                 User configuration and feature operations
```

`timers_manager.py` is adjacent to this package rather than part of it. It uses the manager's MongoDB database for the `timers` collection.

## Storage map

| Scope | MongoDB collection/document | Redis keys | Main modules |
| --- | --- | --- | --- |
| Guild | `guilds`, keyed by `_id` | Prefix, mute role, AFK, leveling, event, telephone, and feature keys | `guild/` |
| User | `users`, keyed by `_id` | Timezone, highlights, and todo keys | `user/` |
| Giveaway | `giveaways`, keyed by `_id` | Giveaway configuration keys | `guild/giveaway.py` |
| Scam links | No MongoDB document | `scam_links_cache`, `scam_link_warned:{channel_id}` | `scam_links.py` |
| Timers | `timers`, keyed by `_id` | None | `../timers_manager.py` |

MongoDB is the source of truth for persistent configuration. Redis is used for fast reads, set membership, counters, and short-lived state. Methods that read through Redis should fall back to MongoDB when the cache is cold and populate the cache when appropriate.

MongoDB fields are never removed by feature operations. Clearable values are
stored as `null` with `$set`; cache keys may still be deleted during cache
invalidation. Readers treat null values as absent state.

## Naming conventions

Public methods follow the operation first, then the resource:

- `get_*` reads one value or collection of values.
- `is_*` answers a boolean question.
- `set_*` replaces a value.
- `add_*` and `remove_*` change membership.
- `enable_*` and `disable_*` toggle a feature.
- `create_*`, `edit_*`, and `delete_*` manage records or configuration documents.

Use the complete noun in configuration APIs: `get_guild_configuration`, `create_guild_configuration`, and `create_user_configuration`. New telephone APIs use names such as `get_telephone_blocked_servers` and `add_telephone_blocked_server`.

Every database mixin inherits `DatabaseMixin`. Mixins are stateless domain
slices: they declare the typed storage dependencies they use, expose public
operations, and keep implementation helpers private. The violation module
and API use the correctly spelled `violation` term.

## Lifecycle

`DatabaseManager` creates one asynchronous MongoDB client and one Redis client during bot startup. The bot owns the manager and should call:

- `ping_mongo_server()` and `ping_redis_server()` for readiness checks.
- `register_guild()` and `register_user()` before writing feature data for a new entity.
- `invalidate_redis()` when a full cache reset is required.
- `close()` during shutdown.

The raw `mongo_client`, `mongo_db`, and `redis_client` properties are infrastructure escape hatches. Prefer a domain method when one exists so cache invalidation and persistence stay consistent.

## Adding a feature

1. Add or update the relevant `TypedDict` in `models.py`.
2. Put guild or user operations in the matching mixin module.
3. Use a descriptive Redis key template in `cache_keys.py` when caching is needed.
4. Keep MongoDB field names aligned with the model and use `_id` for document identity.
5. Update callers and this map when adding a new collection or scope.
6. Run `python -m compileall -q core/utils/database` and the configured lint/type checks.
