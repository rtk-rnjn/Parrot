from __future__ import annotations

from contextlib import suppress
from typing import Any

import discord


def get_action_color(action: discord.AuditLogAction) -> int:
    category = getattr(action, "category", None)
    if category is None:
        return 0x2F3136
    elif category.value == 1:
        return 0x3BA55C
    elif category.value == 2:
        return 0xEC4245
    elif category.value == 3:
        return 0xFAA61A
    return 0x2F3136


def resolve_target(target: Any) -> str:
    attr = getattr(target, "mention", None) or getattr(target, "name", None) or getattr(target, "id", None)
    if attr is None:
        return "Can not determine the target"
    elif isinstance(attr, int):
        return f"<'Can not determine the target': {attr}>"
    else:
        return attr


def get_permissions_changes(entry: discord.AuditLogEntry, change_type: str):
    changes = []
    with suppress(AttributeError, TypeError):
        changes.extend(
            f"{resolve_target(entry.extra)}: **{b[0]}** `{b[1]}` -> `{a[1]}`"
            for b, a in zip(  # noqa: B905
                getattr(entry.before, change_type),
                getattr(entry.after, change_type),
            )
            if b[1] != a[1]
        )
    return "\n".join(changes)


def get_change_value(entry: discord.AuditLogEntry, change_type: str) -> str | None:
    if change_type in {"overwrites", "permissions", "allow", "deny"}:
        return get_permissions_changes(entry, change_type)
    elif change_type == "roles":
        return _get_change_value_roles(entry)
    elif hasattr(entry.before, change_type) and hasattr(entry.after, change_type):
        return f"**{change_type.replace('_', ' ').title()}:** {getattr(entry.before, change_type)} -> {getattr(entry.after, change_type)}"
    return None


def _get_change_value_roles(entry: discord.AuditLogEntry):
    message = ["### Updated Roles"]
    role_removals = set(entry.before.roles) - set(entry.after.roles)
    role_additions = set(entry.after.roles) - set(entry.before.roles)
    for role in role_removals | role_additions:
        sign = "-" if role in role_removals else "+"
        message.append(f"{sign} {role.mention}")

    message = "\n".join(message)
    return f"```diff\n{message}```"
