# Extra Events

### 1. `on_member_kick`

Called when a [`Member`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Member "discord.Member") is kicked from a [`Guild`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild "discord.Guild").

This requires [`Intents.members`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Intents.members "discord.Intents.members") to be enabled.

> **Note: Bot will only dispatch event if it is having `KICK_MEMBERS` and `VIEW_AUDIT_LOGS` permissions.**

**Parameters:**
- `member` ([`Member`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Member "discord.Member")) – Member who was kicked.
- `entry` ([`AuditLogEntry`](https://discordpy.readthedocs.io/en/latest/api.html#discord.AuditLogEntry "discord.AuditLogEntry")) – The audit log entry.

---

### 2. `on_invite`

Called when [`Member`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Member "discord.Member") is joined the [`Guild`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild "discord.Guild").

This requires [`Intents.members`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Intents.members "discord.Intents.members") to be enabled.

> **Note: Bot will only dispatch event if it is having `MANAGE_CHANNELS` and `VIEW_AUDIT_LOGS` permissions. Also this dispatch is only for premium guilds**

**Parameters:**

- `member`  ([`Member`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Member "discord.Member")) – Member who joined.
- `old_invite` (Optional[[`Invite`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Invite "discord.Invite")]) – Old invite from which member was invited.
- `new_invite` (Optional[[`Invite`](https://discordpy.readthedocs.io/en/latest/api.html#discord.Invite "discord.Invite")]) – New invite from which member was invited.
