from __future__ import annotations

import discord


def automod_embeds() -> list[discord.Embed]:
    """Return the Advanced Automoderator documentation pages."""

    pages: list[discord.Embed] = []

    def page(title: str, description: str, *, color: discord.Colour | None = None) -> discord.Embed:
        embed = discord.Embed(title=title, description=description, color=color)
        pages.append(embed)
        return embed

    (
        page(
            "Advanced Automoderator",
            (
                "A flexible rule-based moderation system built around "
                "**triggers**, **conditions**, and **effects**.\n\n"
                "Each rule is independent. A rule contains exactly one "
                "trigger, optional conditions, and one or more effects."
            ),
        )
        .add_field(
            name="Rule",
            value=("Defines a complete moderation behavior. Every rule is evaluated independently."),
            inline=False,
        )
        .add_field(
            name="Trigger",
            value=("Defines what event or behavior causes the rule to be evaluated. Each rule has **exactly one trigger**."),
            inline=False,
        )
        .add_field(
            name="Conditions",
            value=(
                "Optional restrictions that determine whether the rule should continue. When multiple conditions exist, **all conditions must pass**."
            ),
            inline=False,
        )
        .add_field(
            name="Effects",
            value=("Actions performed after the trigger fires and all conditions pass. **All configured effects execute**."),
            inline=False,
        )
    )

    (
        page(
            "Rules",
            (
                "Rules are the fundamental unit of Advanced Automoderator. There are no rulesets; every rule is configured and evaluated independently."
            ),
        )
        .add_field(
            name="Rule Structure",
            value=(
                "**1 Trigger**\n"
                "The event or behavior that starts the rule.\n\n"
                "**0+ Conditions**\n"
                "Additional requirements that must all be satisfied.\n\n"
                "**1+ Effects**\n"
                "Actions performed when the rule passes."
            ),
            inline=False,
        )
        .add_field(
            name="Evaluation",
            value=(
                "1. The trigger is evaluated.\n"
                "2. If the trigger does not fire, the rule stops.\n"
                "3. If it fires, all configured conditions are checked.\n"
                "4. If every condition passes, all effects are executed."
            ),
            inline=False,
        )
        .add_field(
            name="Example",
            value=(
                "`ANY_LINK`\n"
                "→ `ACTIVE_CHANNELS`\n"
                "→ `DELETE_MESSAGE` + `ADD_VIOLATION`\n\n"
                "The rule fires when a link is detected, checks that the "
                "message is in an active channel, then deletes the message "
                "and adds a violation."
            ),
            inline=False,
        )
    )

    (
        page(
            "Triggers — Messages",
            "Triggers that evaluate message content or message properties.",
        )
        .add_field(
            name="`ALL_CAPS`",
            value="Fires when a message exceeds the configured percentage of uppercase characters.",
            inline=False,
        )
        .add_field(
            name="`MESSAGE_MENTIONS`",
            value="Fires when a message exceeds the configured threshold for unique user mentions.",
            inline=False,
        )
        .add_field(
            name="`MESSAGE_REGEX`",
            value="Fires when a message matches the configured regular expression.",
            inline=False,
        )
        .add_field(
            name="`MESSAGE_NOT_REGEX`",
            value="Fires when a message does not match the configured regular expression.",
            inline=False,
        )
        .add_field(
            name="`MESSAGE_WITHOUT_ATTACHMENTS`",
            value="Fires when a message contains no attachments.",
            inline=False,
        )
        .add_field(
            name="`MESSAGE_WITH_ATTACHMENTS`",
            value="Fires when a message contains one or more attachments.",
            inline=False,
        )
        .add_field(
            name="`MESSAGE_LENGTH_GT`",
            value="Fires when a message contains more than the configured number of characters.",
            inline=False,
        )
        .add_field(
            name="`MESSAGE_LENGTH_LT`",
            value="Fires when a message contains fewer than the configured number of characters.",
            inline=False,
        )
        .add_field(
            name="`X_CONSECUTIVE_IDENTICAL_MESSAGES`",
            value="Fires when a user sends the configured number of identical messages consecutively.",
            inline=False,
        )
    )

    (
        page(
            "Triggers — Links & Security",
            "Triggers for links, domains, invites, and external moderation systems.",
        )
        .add_field(
            name="`ANY_LINK`",
            value="Fires when a message contains any valid link.",
            inline=False,
        )
        .add_field(
            name="`WORD_DENYLIST`",
            value="Fires when a message contains a word from the selected denylist.",
            inline=False,
        )
        .add_field(
            name="`WORD_ALLOWLIST`",
            value="Fires when a message contains a word that is not in the selected allowlist.",
            inline=False,
        )
        .add_field(
            name="`WEBSITE_DENYLIST`",
            value="Fires when a message contains a link to a domain from the selected denylist.",
            inline=False,
        )
        .add_field(
            name="`WEBSITE_ALLOWLIST`",
            value="Fires when a message contains a link to a domain that is not in the selected allowlist.",
            inline=False,
        )
        .add_field(
            name="`SERVER_INVITES`",
            value="Fires when a message contains a server invite link.",
            inline=False,
        )
        .add_field(
            name="`FLAGGED_SCAM_LINKS`",
            value="Fires when a message contains a link that has been flagged as a scam.",
            inline=False,
        )
        .add_field(
            name="`DISCORD_AUTOMOD`",
            value="Fires when the message triggers Discord's native Automod.",
            inline=False,
        )
    )

    (
        page(
            "Triggers — Users & Members",
            "Triggers that evaluate usernames, nicknames, violations, or membership events.",
        )
        .add_field(
            name="Nickname",
            value=(
                "`NICKNAME_REGEX` — Nickname matches a regular expression.\n"
                "`NICKNAME_NOT_REGEX` — Nickname does not match a regular expression.\n"
                "`NICKNAME_WORD_ALLOWLIST` — Nickname contains a word outside the allowlist.\n"
                "`NICKNAME_WORD_DENYLIST` — Nickname contains a word from the denylist."
            ),
            inline=False,
        )
        .add_field(
            name="Joining Users",
            value=(
                "`NEW_MEMBER` — A new member joins the server.\n"
                "`JOIN_USERNAME_REGEX` — Joining user's username matches a regex.\n"
                "`JOIN_USERNAME_NOT_REGEX` — Joining user's username does not match a regex.\n"
                "`JOIN_USERNAME_WORD_ALLOWLIST` — Username contains a word outside the allowlist.\n"
                "`JOIN_USERNAME_WORD_DENYLIST` — Username contains a denied word.\n"
                "`JOIN_USERNAME_INVITE` — Username contains a server invite."
            ),
            inline=False,
        )
        .add_field(
            name="Violations",
            value=("`VIOLATIONS` — Fires when the user has accumulated the configured number of violations."),
            inline=False,
        )
    )

    (
        page(
            "Triggers — Rate Limits",
            "Triggers that detect repeated activity within a configured time window.",
        )
        .add_field(
            name="User Activity",
            value=(
                "`X_USER_MESSAGE_IN_Y_MINUTES` — User sends X messages in Y minutes.\n"
                "`X_USER_LINKS_IN_Y_MINUTES` — User sends X links in Y minutes.\n"
                "`X_USER_ATTACHMENTS_IN_Y_MINUTES` — User sends X attachments in Y minutes.\n"
                "`X_USER_MESSAGE_MENTIONS_IN_Y_MINUTES` — User sends X mentions in Y minutes.\n"
                "`X_VOILATION_IN_Y_MINUTES` — User accumulates X violations in Y minutes."
            ),
            inline=False,
        )
        .add_field(
            name="Channel Activity",
            value=(
                "`X_CHANNEL_MESSAGE_IN_Y_MINUTES` — Channel receives X messages in Y minutes.\n"
                "`X_CHANNEL_LINKS_IN_Y_MINUTES` — Channel receives X links in Y minutes.\n"
                "`X_CHANNEL_ATTACHMENTS_IN_Y_MINUTES` — Channel receives X attachments in Y minutes.\n"
                "`X_CHANNEL_MESSAGE_MENTIONS_IN_Y_MINUTES` — Channel receives X mentions in Y minutes."
            ),
            inline=False,
        )
    )

    (
        page(
            "Conditions — Channels & Categories",
            "Conditions that restrict where a rule can apply.",
        )
        .add_field(
            name="`IGNORED_CHANNELS`",
            value="Skip messages from the selected channels.",
            inline=False,
        )
        .add_field(
            name="`ACTIVE_CHANNELS`",
            value="Only apply the rule in the selected channels.",
            inline=False,
        )
        .add_field(
            name="`IGNORED_CATEGORIES`",
            value="Skip messages from channels in the selected categories.",
            inline=False,
        )
        .add_field(
            name="`ACTIVE_CATEGORIES`",
            value="Only check the rule in the selected categories.",
            inline=False,
        )
        .add_field(
            name="`ACTIVE_IN_THREADS`",
            value="Only apply the rule inside threads.",
            inline=False,
        )
        .add_field(
            name="`IGNORE_THREADS`",
            value="Skip messages sent inside threads.",
            inline=False,
        )
    )

    (
        page(
            "Conditions — Users & Roles",
            "Conditions that restrict rules based on users, roles, or account history.",
        )
        .add_field(
            name="`IGNORED_ROLES`",
            value="Ignore users who have any of the selected roles.",
            inline=False,
        )
        .add_field(
            name="`REQUIRED_ROLES`",
            value="Only apply the rule to users who have the selected roles.",
            inline=False,
        )
        .add_field(
            name="`ACCOUNT_AGE_ABOVE`",
            value="Only apply the rule to accounts older than the selected age.",
            inline=False,
        )
        .add_field(
            name="`ACCOUNT_AGE_BELOW`",
            value="Only apply the rule to accounts newer than the selected age.",
            inline=False,
        )
        .add_field(
            name="`MEMBER_DURATION_ABOVE`",
            value="Only apply the rule to members who have been in the server longer than the selected duration.",
            inline=False,
        )
        .add_field(
            name="`MEMBER_DURATION_BELOW`",
            value="Only apply the rule to members who joined more recently than the selected duration.",
            inline=False,
        )
    )

    (
        page(
            "Conditions — Messages",
            "Conditions that control what kind of messages a rule can process.",
        )
        .add_field(
            name="`IGNORE_BOTS`",
            value="Ignore messages sent by bots.",
            inline=False,
        )
        .add_field(
            name="`ONLY_BOTS`",
            value="Only apply the rule to messages sent by bots.",
            inline=False,
        )
        .add_field(
            name="`NEW_MESSAGE`",
            value="Only apply the rule to brand-new messages.",
            inline=False,
        )
        .add_field(
            name="`EDITED_MESSAGE`",
            value="Only apply the rule to edited messages.",
            inline=False,
        )
        .add_field(
            name="`IGNORE_FORWARDS`",
            value="Ignore messages that include forwarded content.",
            inline=False,
        )
        .add_field(
            name="`ONLY_FORWARDS`",
            value="Only apply the rule to messages that include forwarded content.",
            inline=False,
        )
        .add_field(
            name="Condition Logic",
            value=("When multiple conditions are configured, **every condition must be satisfied** before the effects are executed."),
            inline=False,
        )
    )

    (
        page(
            "Effects — Moderation",
            "Effects that directly moderate messages, users, or violation records.",
        )
        .add_field(
            name="Messages",
            value=(
                "`DELETE_MESSAGE` — Delete the message that triggered the rule.\n"
                "`DELETE_MULTIPLE_MESSAGES` — Remove several recent messages from the user."
            ),
            inline=False,
        )
        .add_field(
            name="User Actions",
            value=(
                "`WARN_USER` — Warn the user.\n"
                "`MUTE_USER` — Mute the user.\n"
                "`TIMEOUT_USER` — Apply a Discord timeout.\n"
                "`KICK_USER` — Kick the user.\n"
                "`BAN_USER` — Ban the user."
            ),
            inline=False,
        )
        .add_field(
            name="Violations",
            value=("`ADD_VIOLATION` — Add a violation to the user's record.\n`RESET_VIOLATIONS` — Clear a specific violation record."),
            inline=False,
        )
    )

    (
        page(
            "Effects — Roles & Nicknames",
            "Effects that modify the user's roles or nickname.",
        )
        .add_field(
            name="`GIVE_ROLE`",
            value=("Give the user a role for a configured amount of time or permanently."),
            inline=False,
        )
        .add_field(
            name="`REMOVE_ROLE`",
            value="Remove a role from the user.",
            inline=False,
        )
        .add_field(
            name="`SET_NICKNAME`",
            value="Change the user's nickname.",
            inline=False,
        )
    )

    (
        page(
            "Effects — Communication",
            "Effects that communicate moderation events or modify channel behavior.",
        )
        .add_field(
            name="`SEND_MESSAGE`",
            value="Send a custom message to a selected channel.",
            inline=False,
        )
        .add_field(
            name="`SEND_ALERT`",
            value="Send an alert embed to a selected channel.",
            inline=False,
        )
        .add_field(
            name="`ENABLE_SLOWMODE`",
            value="Enable slowmode in the channel where the rule fired.",
            inline=False,
        )
        .add_field(
            name="Effect Logic",
            value=("A rule may contain multiple effects. Once the trigger fires and all conditions pass, **all configured effects are executed**."),
            inline=False,
        )
    )

    (
        page(
            "Lists",
            "Reusable lists that can be referenced by word and website triggers.",
        )
        .add_field(
            name="Word Lists",
            value=(
                "Multiple entries can be separated by spaces or newlines.\n\n"
                "Each entry must be a single word and cannot contain spaces.\n\n"
                "For complete phrases, use a regular expression trigger."
            ),
            inline=False,
        )
        .add_field(
            name="Website Lists",
            value=("Specify only the domain without a protocol or path.\n\nExample: `example.com`\n\nSubdomains are automatically included."),
            inline=False,
        )
    )

    (
        page(
            "Logs & Troubleshooting",
            "Use the Logs tab to inspect rule execution and troubleshoot configurations.",
        )
        .add_field(
            name="Logged Information",
            value=("• Which user triggered the rule\n• Which rule fired\n• When the rule fired\n• Which trigger caused the rule to fire"),
            inline=False,
        )
        .add_field(
            name="Not Logged",
            value=("Logs are not a complete record of messages and do not record moderation actions themselves."),
            inline=False,
        )
        .add_field(
            name="Troubleshooting",
            value=(
                "If a rule does not behave as expected, verify:\n\n"
                "1. The trigger configuration.\n"
                "2. Every configured condition.\n"
                "3. The configured effects.\n"
                "4. The relevant permissions.\n"
                "5. The resulting log entry."
            ),
            inline=False,
        )
    )

    return pages
