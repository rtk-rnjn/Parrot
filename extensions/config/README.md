# Configuration

Interactive server settings dashboard for Parrot, built on discord.py components v2.

## Scope

`config` (alias `settings`, also available as a slash command) opens one ephemeral
message that edits every server setting in place: command prefix, moderation roles and
log channel, welcome and leave messages, leveling and reward roles, starboard, giveaways,
tickets, suggestions, birthdays, the voice hub, the telephone line and its block list,
global chat, and the per-event log webhooks.

## Layout

- `dashboard.py` owns the message: a category menu, a container that re-renders the
  current page, a one-line notice for feedback, a confirm step for resets, and
  refresh/close controls.
- `pages/base.py` defines `Page` (summary, accent colour, body, reset) plus the
  select/button wrappers and formatting helpers every page shares.
- `pages/<module>.py` holds one page per settings section. Pages write through
  `bot.database` and then call `commit()`, which reloads the guild document and edits
  the message from the same interaction.
- `pages/webhooks.py` creates, reuses, resolves and deletes the webhooks used by global
  chat and event logs.

Database support lives in `core/utils/database/guild/settings.py`
(`get_guild_settings`, `reset_guild_setting`) and `defaults.py`.
