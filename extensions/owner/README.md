# Owner

Bot-owner-only diagnostics and administration.

## Scope

`owner` (aliases `panel`, `dev`) opens a tabbed components v2 panel: bot runtime and extensions,
Redis `INFO` views and `CONFIG GET`, MongoDB server status, databases and storage, Lavalink nodes
(connect, disconnect, load the public list) and asyncio tasks with guarded cancellation.
`redis-repl` keeps an interactive Redis session in chat.

`panel.py` holds the panel and its tabs; the cog in `__init__.py` only exposes the two commands.
