from __future__ import annotations

from dataclasses import dataclass

import discord

FIELD_LIMIT = 1024
EMBED_BUDGET = 5500
MAX_FIELDS = 24

BLUE = 0x5865F2
ORANGE = 0xE67E22
TEAL = 0x1ABC9C
RED = 0xE74C3C
GREEN = 0x2ECC71
GOLD = 0xF1C40F
PURPLE = 0x9B59B6

type Field = tuple[str, str]


@dataclass(frozen=True, slots=True)
class Section:
    group: str
    title: str
    description: str
    colour: int
    fields: tuple[Field, ...] = ()


def split_text(text: str, limit: int = FIELD_LIMIT) -> list[str]:
    chunks: list[str] = []
    current = ""
    for raw_line in text.split("\n"):
        line = raw_line
        while len(line) > limit:
            cut = line.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:cut])
            line = line[cut:].lstrip()
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def render(section: Section) -> list[discord.Embed]:
    prepared: list[Field] = []
    for name, value in section.fields:
        for index, chunk in enumerate(split_text(value)):
            prepared.append((name if index == 0 else f"{name} (cont.)", chunk))

    base = len(section.title) + len(section.description) + 30
    groups: list[list[Field]] = [[]]
    used = base
    for name, value in prepared:
        size = len(name) + len(value)
        if groups[-1] and (len(groups[-1]) >= MAX_FIELDS or used + size > EMBED_BUDGET):
            groups.append([])
            used = base
        groups[-1].append((name, value))
        used += size

    embeds: list[discord.Embed] = []
    for index, group in enumerate(groups, 1):
        title = section.title if len(groups) == 1 else f"{section.title} ({index}/{len(groups)})"
        embed = discord.Embed(
            title=title,
            description=section.description if index == 1 else None,
            colour=section.colour,
        )
        for name, value in group:
            embed.add_field(name=name, value=value, inline=False)
        embeds.append(embed)
    return embeds


GUIDE = (
    Section(
        "Guide",
        "Advanced Automoderator",
        (
            "A rule engine for your server. Every rule answers three questions:\n\n"
            "**What am I looking for?** \N{RIGHTWARDS ARROW} the **trigger**\n"
            "**Does it apply here, and to this person?** \N{RIGHTWARDS ARROW} the **conditions**\n"
            "**What should happen?** \N{RIGHTWARDS ARROW} the **effects**\n\n"
            "Rules are small and independent. Build several focused rules and let them cooperate "
            "(for example through violations) instead of one giant rule."
        ),
        BLUE,
        (
            (
                "Trigger - exactly one",
                (
                    "The behaviour the rule listens for: a message pattern, a rate limit, a member joining, "
                    "a nickname, a violation count. A rule can't be saved without one.\n"
                    "Need *this OR that*? Make two rules."
                ),
            ),
            (
                "Conditions - zero or more",
                (
                    "Filters on **who** and **where**. **Every** condition must pass; there is no OR. "
                    "Each condition type appears once per rule, and conflicting pairs replace each other. "
                    "Conditions only ever **narrow** a rule, never widen it."
                ),
            ),
            (
                "Effects - one or more (max 15)",
                (
                    "What happens once the trigger fired and all conditions passed. **All** configured effects run. "
                    "Some effects can be added several times with different settings (roles, channels, violation names)."
                ),
            ),
            (
                "Mental model",
                "`IF trigger AND condition AND condition THEN effect AND effect`",
            ),
            (
                "Golden rules",
                (
                    "\N{BULLET} Scope every rule to channels or categories.\n"
                    "\N{BULLET} Exempt your moderators with *Ignored Roles*.\n"
                    "\N{BULLET} Start with *Send Alert* only, then add punishments once it behaves.\n"
                    "\N{BULLET} Punish through **violations** instead of instant bans.\n"
                    "\N{BULLET} Make sure every number is **reachable** (see *When a Rule Can Never Fire*)."
                ),
            ),
            (
                "Quick start",
                (
                    "1. `/automod add name:no-links`\n"
                    "2. **Set trigger** \N{RIGHTWARDS ARROW} Message & Links \N{RIGHTWARDS ARROW} *Any Link*\n"
                    "3. **Add** a condition \N{RIGHTWARDS ARROW} *Ignored Roles* \N{RIGHTWARDS ARROW} your moderator roles\n"
                    "4. **Add** a condition \N{RIGHTWARDS ARROW} *Active Channels* \N{RIGHTWARDS ARROW} `#general`\n"
                    "5. **Add** an effect \N{RIGHTWARDS ARROW} *Delete Message*\n"
                    "6. **Save rule**, then test it with a non-staff account."
                ),
            ),
        ),
    ),
    Section(
        "Guide",
        "Building Rules",
        "Everything about creating, editing and browsing rules.",
        BLUE,
        (
            (
                "Commands",
                (
                    "`/automod add <name>` - start a new rule\n"
                    "`/automod edit <name>` - reopen a rule in the builder (name autocompletes)\n"
                    "`/automod delete <name>` - delete after a confirmation\n"
                    "`/automod list` - browse all rules\n\n"
                    "By default these need **Manage Server**. Server admins can change who may use them under "
                    "*Server Settings \N{RIGHTWARDS ARROW} Integrations*."
                ),
            ),
            (
                "The builder card",
                (
                    "One message shows the whole rule: settings, trigger, conditions and effects. "
                    "The card is **orange** while the rule is incomplete and turns **green** once it can be saved. "
                    "*Save rule* stays disabled until the rule has a trigger and at least one effect."
                ),
            ),
            (
                "Adding a trigger, condition or effect",
                (
                    "Press **Set trigger** or **Add**. Choose a group with the buttons, then pick an item from the menu. "
                    "Items with options open a form; items without options are added immediately. "
                    "Items already on the rule are marked with \N{WHITE HEAVY CHECK MARK}."
                ),
            ),
            (
                "Forms and validation",
                (
                    "Forms are validated before anything is added. Bad numbers, invalid regexes and malformed "
                    "durations show a message and change nothing.\n\n"
                    "Durations accept `30m`, `12h`, `7d`, `2w` and combinations such as `1d 12h`. A bare number uses the "
                    "field's default unit: minutes, or seconds for short timers (*Max Age*, *Slowmode Delay*, *Delete After*)."
                ),
            ),
            (
                "Replacing and stacking",
                (
                    "\N{BULLET} **Conditions:** one per type. Adding it again replaces the old settings.\n"
                    "\N{BULLET} **Conflicting conditions replace each other:** Ignore Bots \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Only Bots \N{MIDDLE DOT} New Message \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Edited Message \N{MIDDLE DOT} "
                    "Active in Threads \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Ignore Threads \N{MIDDLE DOT} Ignore Forwards \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Only Forwards.\n"
                    "\N{BULLET} **Effects:** one per type, except *Add Violation*, *Reset Violations*, *Give Role*, *Remove Role*, "
                    "*Send Message* and *Send Alert*, which can be added repeatedly. An identical copy is not duplicated.\n"
                    "\N{BULLET} **Kick \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Ban** and **Mute \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Timeout** replace each other."
                ),
            ),
            (
                "Removing",
                "Use the **Remove\N{HORIZONTAL ELLIPSIS}** menu under the Conditions or Effects block. The trigger can be changed, but a rule can't exist without one.",
            ),
            (
                "Settings",
                (
                    "**Name:** 1-100 characters, unique per server. Renaming is checked immediately.\n"
                    "**Priority:** a whole number, default 0. Higher numbers are evaluated first.\n"
                    "**Enabled:** disabled rules are kept but never run."
                ),
            ),
            (
                "Browsing and editing",
                (
                    "`/automod list` sorts by priority (highest first), then name, five rules per page. "
                    "\N{LARGE GREEN CIRCLE} means enabled, \N{MEDIUM WHITE CIRCLE} disabled. Press **View** on a rule to see everything, then **Edit** or **Delete**.\n\n"
                    "Edits are only stored when you press **Save changes**. **Cancel** discards them."
                ),
            ),
            (
                "Limits",
                "A rule can hold at most **15 effects**, one trigger, and one condition per condition type.",
            ),
        ),
    ),
    Section(
        "Guide",
        "How Rules Are Evaluated",
        "Knowing the order of operations answers most \N{LEFT DOUBLE QUOTATION MARK}why didn't it fire?\N{RIGHT DOUBLE QUOTATION MARK} questions.",
        BLUE,
        (
            (
                "Order of operations",
                (
                    "1. An event arrives: a message is sent or edited, a member joins, a nickname changes, or a violation is recorded.\n"
                    "2. Enabled rules are considered, highest **priority** first.\n"
                    "3. The **trigger** is checked. No match \N{RIGHTWARDS ARROW} the rule stops.\n"
                    "4. Every **condition** is checked. One failure \N{RIGHTWARDS ARROW} the rule stops.\n"
                    "5. Every **effect** runs."
                ),
            ),
            (
                "Priority",
                (
                    "Higher numbers are evaluated earlier; negative numbers are allowed. Rules with equal priority have no "
                    "guaranteed order. Priority orders evaluation; it does not make one rule cancel another."
                ),
            ),
            (
                "Rules are independent",
                (
                    "A single message can match several rules, and each one runs on its own. Overlap is fine when the rules do "
                    "different jobs, but two rules that both send a message produce two messages."
                ),
            ),
            (
                "Event types",
                (
                    "**Message** - everything in the message, link, word and rate-limit groups. All conditions and effects apply.\n"
                    "**Member join** - `NEW_MEMBER` and every `JOIN_USERNAME_*` trigger.\n"
                    "**Nickname** - every `NICKNAME_*` trigger.\n"
                    "**Violation** - `VIOLATIONS` and `X_VIOLATION_IN_Y_MINUTES`."
                ),
            ),
            (
                "Matching conditions and effects to the event",
                (
                    "Join, nickname and violation events carry no message or channel, so:\n"
                    "\N{BULLET} Avoid channel, category, thread, new/edited and forward conditions on them. There is nothing to check, "
                    "and the rule may never pass.\n"
                    "\N{BULLET} Avoid *Delete Message* and *Delete Multiple Messages*; they need a message.\n"
                    "\N{BULLET} Role, account-age and bot conditions work well.\n"
                    "\N{BULLET} `MEMBER_DURATION_ABOVE` is pointless on a join; the member just arrived."
                ),
            ),
            (
                "Units at a glance",
                (
                    "Rate-limit windows and condition durations are in **whole minutes or longer** (minimum 1 minute). "
                    "Short effect timers (slowmode delay, delete-after, bulk-delete age) are in **seconds** and up."
                ),
            ),
        ),
    ),
)

TRIGGERS = (
    Section(
        "Triggers",
        "Triggers - Message Content",
        "Triggers that inspect what a message says or contains.",
        ORANGE,
        (
            (
                "`ALL_CAPS`",
                (
                    "Fires when a large enough share of a message is uppercase.\n"
                    "**Config:** *Minimum Characters* (1-9999): shorter messages are ignored. *Percentage* (1-100): uppercase share required. Defaults: 3 and 100.\n"
                    "**Tip:** the default catches `OK` and `LOL`. For normal chat try 15 characters at 70%.\n"
                    "**Never fires if** Minimum Characters is above the longest possible message: 2000 characters, or 4000 for Nitro users. A limit of 5000 can never be reached."
                ),
            ),
            (
                "`MESSAGE_MENTIONS`",
                (
                    "Fires when a message mentions more than the configured number of unique users.\n"
                    "**Config:** *Count* (1-99999).\n"
                    "**Tip:** 5 is a common ceiling. Mentioning one person repeatedly counts once.\n"
                    "**Never fires if** Count exceeds what fits in a message. A mention takes about 22 characters, so 2000 characters hold roughly 90 (about 180 at 4000)."
                ),
            ),
            (
                "`MESSAGE_REGEX`",
                (
                    "Fires when the message matches the pattern.\n"
                    "**Config:** *Regex Pattern*, up to 500 characters, RE2 syntax (see *Regular Expressions*).\n"
                    "**Tips:** patterns are case-sensitive, so start with `(?i)`. Anchor with `^` and `$` when you mean the whole message.\n"
                    "**Note:** invalid or unsupported patterns are rejected when you save."
                ),
            ),
            (
                "`MESSAGE_NOT_REGEX`",
                (
                    "Fires when the message does **not** match the pattern. That is true for almost every message, so scope it tightly.\n"
                    "**Example:** in `#counting`, require `^[0-9]+$` and delete everything else.\n"
                    "**Always pair with** *Active Channels* and *Ignored Roles*."
                ),
            ),
            (
                "`MESSAGE_WITH_ATTACHMENTS`",
                "Fires when a message has at least one uploaded file. Pasted image links and link previews are not attachments.",
            ),
            (
                "`MESSAGE_WITHOUT_ATTACHMENTS`",
                (
                    "Fires when a message has no uploaded file, which includes every plain text message.\n"
                    "**Use it for** image-only channels, and always scope it with *Active Channels*."
                ),
            ),
            (
                "`MESSAGE_LENGTH_GT`",
                (
                    "Fires when a message is longer than the limit.\n"
                    "**Config:** *Length* (1-99999).\n"
                    "**Never fires if** Length is 2000 or more (4000 if members have Nitro). Raw text counts, so a mention takes about 22 characters and a custom emoji roughly 20-30."
                ),
            ),
            (
                "`MESSAGE_LENGTH_LT`",
                (
                    "Fires when a message is shorter than the limit.\n"
                    "**Config:** *Length* (1-99999).\n"
                    "**Notes:** Length 1 only matches messages with no text at all, such as image-only posts. Low values catch one-character spam but also legitimate replies like `k` or `ty`, so use them in channels where short messages are unusual."
                ),
            ),
            (
                "`DISCORD_AUTOMOD`",
                (
                    "Fires when Discord's built-in AutoMod flags the message. No config.\n"
                    "**Why use it:** react to native rules with your own effects (violations, timeouts, alerts).\n"
                    "**Watch out:** if the native rule is set to *Block message*, the message is never posted, so *Delete Message* has nothing to delete. Use user-level effects instead."
                ),
            ),
            (
                "`X_CONSECUTIVE_IDENTICAL_MESSAGES`",
                (
                    "Fires when a user sends the same message *Count* times in a row within *Within (minutes)*.\n"
                    "**Tip:** Count 3-4 within 1-2 minutes. Count 1 fires on every message."
                ),
            ),
        ),
    ),
    Section(
        "Triggers",
        "Triggers - Words, Links & Scams",
        "Triggers based on word lists, domains and known-bad links.",
        ORANGE,
        (
            (
                "`WORD_DENYLIST`",
                (
                    "Fires when the message contains a word from the list.\n"
                    "**Config:** *List Name* (optional, up to 100 characters).\n"
                    "**Notes:** entries are single words. For phrases, spacing tricks and substrings use a regex. "
                    "A trigger with no list attached has nothing to compare against, so attach one before relying on it."
                ),
            ),
            (
                "`WORD_ALLOWLIST`",
                (
                    "Fires when the message contains a word that is **not** in the list.\n"
                    "**Be careful:** every word you want to allow must be on the list. An empty list fires on any message that contains words.\n"
                    "**Use it for** tightly controlled channels only."
                ),
            ),
            (
                "`WEBSITE_DENYLIST`",
                (
                    "Fires when the message links to a domain on the list.\n"
                    "**Format:** domain only (`example.com`), no `https://` and no path. Subdomains are included automatically."
                ),
            ),
            (
                "`WEBSITE_ALLOWLIST`",
                (
                    "Fires when the message links to a domain that is **not** on the list. Messages without links don't fire.\n"
                    "**Tip:** members posting GIFs from Discord's picker send `tenor.com` or `giphy.com` links, so allow those if you want GIFs."
                ),
            ),
            (
                "`ANY_LINK`",
                (
                    "Fires on any valid link. No config.\n"
                    "**Notes:** this includes links to your own sites and GIF links. Obfuscated links such as `example[.]com` are not valid links, so use a regex for those."
                ),
            ),
            (
                "`SERVER_INVITES`",
                (
                    "Fires when the message contains a Discord server invite. No config.\n"
                    "**Notes:** with no options it can't tell advertising from friendly invites. Exempt partner channels with *Ignored Channels* and staff with *Ignored Roles*."
                ),
            ),
            (
                "`FLAGGED_SCAM_LINKS`",
                (
                    "Fires when the message contains a link flagged as a scam. No config.\n"
                    "**Notes:** no list catches every new scam instantly, so layer it with `WEBSITE_DENYLIST` and regex rules.\n"
                    "**Strong effect set:** *Delete Message* + *Delete Multiple Messages* + *Timeout User* + *Send Alert*. Scam links usually come from compromised accounts, and a timeout lets the owner recover them."
                ),
            ),
        ),
    ),
    Section(
        "Triggers",
        "Triggers - Rate Limits",
        "Triggers that count activity inside a time window.",
        ORANGE,
        (
            (
                "How windows work",
                (
                    "Every rate-limit trigger has *Count* (1-99999) and *Within (minutes)* (1-99999). "
                    "The smallest window is **one minute**; \N{LEFT DOUBLE QUOTATION MARK}10 messages in 10 seconds\N{RIGHT DOUBLE QUOTATION MARK} can't be expressed. "
                    "Use a 1-minute window with a lower count, or `X_CONSECUTIVE_IDENTICAL_MESSAGES` for repeat spam."
                ),
            ),
            (
                "User triggers",
                (
                    "`X_USER_MESSAGE_IN_Y_MINUTES` - one user sends X messages\n"
                    "`X_USER_LINKS_IN_Y_MINUTES` - one user sends X links\n"
                    "`X_USER_ATTACHMENTS_IN_Y_MINUTES` - one user sends X attachments\n"
                    "`X_USER_MESSAGE_MENTIONS_IN_Y_MINUTES` - one user sends X mentions\n"
                    "Each person is counted separately."
                ),
            ),
            (
                "Channel triggers",
                (
                    "`X_CHANNEL_MESSAGE_IN_Y_MINUTES`\n"
                    "`X_CHANNEL_LINKS_IN_Y_MINUTES`\n"
                    "`X_CHANNEL_ATTACHMENTS_IN_Y_MINUTES`\n"
                    "`X_CHANNEL_MESSAGE_MENTIONS_IN_Y_MINUTES`\n"
                    "These count everyone together. They describe the **channel**, not a person, so prefer channel-level effects "
                    "(*Enable Slowmode*, *Send Alert*) over punishing whoever sent the last message."
                ),
            ),
            (
                "Choosing numbers",
                (
                    "Typical starting points:\n"
                    "\N{BULLET} Chat flood: 8-10 messages in 1 minute\n"
                    "\N{BULLET} Link spam: 3 links in 1 minute\n"
                    "\N{BULLET} Attachment spam: 5 files in 1 minute\n"
                    "\N{BULLET} Mention spam: 10 mentions in 1 minute\n"
                    "\N{BULLET} Channel raid: 40+ messages in 1 minute (tune to your busiest hour)"
                ),
            ),
            (
                "Counts must be reachable",
                (
                    "Channel slowmode caps how fast a user can post: roughly one message per slowmode interval. "
                    "With a 15-second slowmode a user sends about 4-5 messages a minute, so \N{LEFT DOUBLE QUOTATION MARK}8 messages in 1 minute\N{RIGHT DOUBLE QUOTATION MARK} never fires for them. "
                    "Members with *Manage Messages* or *Manage Channels* bypass slowmode."
                ),
            ),
            (
                "Long windows",
                "Prefer short windows (1-10 minutes). The longer the window, the more ordinary activity piles up, and the more false positives you get.",
            ),
        ),
    ),
    Section(
        "Triggers",
        "Triggers - Members, Nicknames & Violations",
        "Triggers that react to people instead of messages.",
        ORANGE,
        (
            (
                "`NEW_MEMBER`",
                (
                    "Fires every time a member joins. No config.\n"
                    "**Always add a condition**, such as *Account Age Below*, or the rule hits everyone who joins."
                ),
            ),
            (
                "Join username triggers",
                (
                    "`JOIN_USERNAME_REGEX` - username matches a regex\n"
                    "`JOIN_USERNAME_NOT_REGEX` - username doesn't match a regex\n"
                    "`JOIN_USERNAME_WORD_DENYLIST` - username contains a listed word\n"
                    "`JOIN_USERNAME_WORD_ALLOWLIST` - username contains a word that isn't listed\n"
                    "`JOIN_USERNAME_INVITE` - username contains a server invite\n\n"
                    "These are checked when the member joins. Usernames are at most 32 characters, so patterns that need more can never match."
                ),
            ),
            (
                "Nickname triggers",
                (
                    "`NICKNAME_REGEX` \N{MIDDLE DOT} `NICKNAME_NOT_REGEX`\n"
                    "`NICKNAME_WORD_DENYLIST` \N{MIDDLE DOT} `NICKNAME_WORD_ALLOWLIST`\n\n"
                    "These look at the member's server nickname. Nicknames are at most 32 characters. Config is the same as the message versions.\n"
                    "**Loop warning:** if *Set Nickname* applies a name that matches the trigger again, the rule fires repeatedly."
                ),
            ),
            (
                "`VIOLATIONS`",
                (
                    "Fires when a user has collected a number of a **named** violation within a window.\n"
                    "**Config:** *Violation Name* (up to 100 characters), *Number of Violations*, *Within (minutes)*.\n"
                    "The name must match the one used by *Add Violation*. See *Violations System*."
                ),
            ),
            (
                "`X_VIOLATION_IN_Y_MINUTES`",
                (
                    "Fires when a user accumulates *Count* violations within *Within (minutes)*.\n"
                    "Use it when you care about total misbehaviour rather than one specific violation name."
                ),
            ),
        ),
    ),
)

CONDITIONS = (
    Section(
        "Conditions",
        "Conditions - How They Combine",
        "Conditions decide whether a triggered rule is allowed to continue.",
        TEAL,
        (
            (
                "Logic",
                "**Every condition must pass.** There is no OR. If you need *channel A or category B*, make two rules.",
            ),
            (
                "They narrow, never widen",
                (
                    "Adding a condition can only make a rule apply to **less**. For example, *Active Channels* plus *Active Categories* "
                    "means the message must be in a listed channel **and** inside a listed category, not one or the other."
                ),
            ),
            (
                "Ranges from pairs",
                (
                    "*Account Age Above 7d* plus *Account Age Below 30d* means accounts between 7 and 30 days old. "
                    "The same works for *Member Duration*. If the lower bound is not smaller than the upper bound, nobody passes."
                ),
            ),
            (
                "Selections",
                (
                    "Roles, channels and categories each allow up to **25** per condition. Beyond that, use categories, "
                    "or invert the logic with the matching *Ignored \N{HORIZONTAL ELLIPSIS}* condition."
                ),
            ),
            (
                "Duration format",
                (
                    "`30m` \N{MIDDLE DOT} `12h` \N{MIDDLE DOT} `7d` \N{MIDDLE DOT} `2w` \N{MIDDLE DOT} `1d 12h` \N{MIDDLE DOT} a bare number means minutes. Minimum 1 minute. "
                    "Months and years aren't units; use `52w` for about a year."
                ),
            ),
            (
                "Conflicting pairs",
                (
                    "These replace each other when added, so they can't contradict:\n"
                    "Ignore Bots \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Only Bots\n"
                    "New Message \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Edited Message\n"
                    "Active in Threads \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Ignore Threads\n"
                    "Ignore Forwards \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Only Forwards"
                ),
            ),
        ),
    ),
    Section(
        "Conditions",
        "Conditions - Who",
        "Conditions about the person who triggered the rule.",
        TEAL,
        (
            (
                "`IGNORED_ROLES`",
                (
                    "Skips users who have **any** selected role (up to 25).\n"
                    "**Best practice:** add your moderator roles to every rule so staff can discuss rule-breaking content without punishment."
                ),
            ),
            (
                "`REQUIRED_ROLES`",
                (
                    "Only applies to users with the selected roles.\n"
                    "**Require all roles** off (default): any one role is enough. On: the user needs every selected role.\n"
                    "**Never passes if** the roles are never held together, or a required role has been deleted."
                ),
            ),
            (
                "`ACCOUNT_AGE_ABOVE` \N{MIDDLE DOT} `ACCOUNT_AGE_BELOW`",
                (
                    "Compares the age of the Discord account (since it was created). Above = older than the duration, below = newer.\n"
                    "**Typical:** `ACCOUNT_AGE_BELOW 3d` to treat brand-new accounts more strictly."
                ),
            ),
            (
                "`MEMBER_DURATION_ABOVE` \N{MIDDLE DOT} `MEMBER_DURATION_BELOW`",
                (
                    "Compares time spent in **this** server. Leaving and rejoining resets it.\n"
                    "**Typical:** `MEMBER_DURATION_BELOW 1d` so new members can't post links yet.\n"
                    "**Never passes** with `MEMBER_DURATION_ABOVE` on `NEW_MEMBER`; a member who just joined hasn't been here long."
                ),
            ),
            (
                "`IGNORE_BOTS` \N{MIDDLE DOT} `ONLY_BOTS`",
                (
                    "Ignore or exclusively target bot accounts. Adding one removes the other.\n"
                    "**Tip:** add `IGNORE_BOTS` to rules whose *Send Message* or *Send Alert* text could match their own trigger."
                ),
            ),
        ),
    ),
    Section(
        "Conditions",
        "Conditions - Where & What",
        "Conditions about the location and kind of message.",
        TEAL,
        (
            (
                "`IGNORED_CHANNELS` \N{MIDDLE DOT} `ACTIVE_CHANNELS`",
                (
                    "Skip the selected channels, or apply only in them (up to 25).\n"
                    "**Selectable:** text, voice, announcement, forum, media and stage channels. Threads are not selectable on their own; "
                    "use the thread conditions below. Forum posts are threads."
                ),
            ),
            (
                "`IGNORED_CATEGORIES` \N{MIDDLE DOT} `ACTIVE_CATEGORIES`",
                "Skip or require whole categories (up to 25). Channels created later inside an *active* category are covered automatically.",
            ),
            (
                "`ACTIVE_IN_THREADS` \N{MIDDLE DOT} `IGNORE_THREADS`",
                "Only apply inside threads, or skip threads entirely. Adding one removes the other.",
            ),
            (
                "`NEW_MESSAGE` \N{MIDDLE DOT} `EDITED_MESSAGE`",
                (
                    "Only apply to brand-new messages, or only to edited ones. Adding one removes the other.\n"
                    "**Warning:** with `NEW_MESSAGE`, edits are ignored, so someone can post something clean and edit it into a violation. "
                    "Use it only for rules where edits don't matter, such as rate limits."
                ),
            ),
            (
                "`IGNORE_FORWARDS` \N{MIDDLE DOT} `ONLY_FORWARDS`",
                "Skip messages that include forwarded content, or apply only to those. Adding one removes the other.",
            ),
            (
                "Combination traps",
                (
                    "\N{BULLET} Same channel in *Ignored Channels* and *Active Channels* \N{RIGHTWARDS ARROW} that channel never passes.\n"
                    "\N{BULLET} *Active Channels* and *Active Categories* together \N{RIGHTWARDS ARROW} must satisfy both.\n"
                    "\N{BULLET} *Active in Threads* with *Active Channels* that exclude where your threads live \N{RIGHTWARDS ARROW} never passes."
                ),
            ),
        ),
    ),
)

EFFECTS = (
    Section(
        "Effects",
        "Effects - Overview",
        "Effects are the actions a rule performs after the trigger fires and every condition passes.",
        RED,
        (
            (
                "How they run",
                (
                    "**All** configured effects run. A rule holds at most **15**. Don't rely on one effect finishing before another "
                    "starts; design effects so they work in any order."
                ),
            ),
            (
                "What each effect needs",
                (
                    "**A message:** Delete Message, Delete Multiple Messages\n"
                    "**A member:** Warn, Mute, Timeout, Kick, Ban, Set Nickname, Give/Remove Role, violations\n"
                    "**A channel:** Enable Slowmode, Send Message, Send Alert\n"
                    "Effects that need something the event doesn't provide (a message on a join event, say) can't do anything."
                ),
            ),
            (
                "Bot permissions",
                (
                    "Delete messages \N{RIGHTWARDS ARROW} *Manage Messages*\n"
                    "Timeout \N{RIGHTWARDS ARROW} *Moderate Members*\n"
                    "Kick \N{RIGHTWARDS ARROW} *Kick Members*\n"
                    "Ban \N{RIGHTWARDS ARROW} *Ban Members*\n"
                    "Nickname \N{RIGHTWARDS ARROW} *Manage Nicknames*\n"
                    "Roles \N{RIGHTWARDS ARROW} *Manage Roles*\n"
                    "Slowmode \N{RIGHTWARDS ARROW} *Manage Channels*\n"
                    "Send Message / Alert \N{RIGHTWARDS ARROW} *View Channel* and *Send Messages* in the target channel (*Embed Links* for alerts)"
                ),
            ),
            (
                "Role hierarchy",
                (
                    "The bot's highest role must be **above** the target's highest role. The server owner can't be kicked, banned, timed out or renamed, "
                    "and administrators can't be timed out. The bot can't hand out roles above its own, bot-managed roles, or @everyone."
                ),
            ),
            (
                "Repeatable effects",
                (
                    "*Add Violation*, *Reset Violations*, *Give Role*, *Remove Role*, *Send Message* and *Send Alert* can appear several times with different settings. "
                    "All other effects exist once per rule. *Kick \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Ban* and *Mute \N{RIGHTWARDS ARROW OVER LEFTWARDS ARROW} Timeout* replace each other."
                ),
            ),
            (
                "User may be gone",
                "After *Kick* or *Ban* the member is no longer in the server, so *Timeout*, *Give Role*, *Set Nickname* and similar effects can't succeed. Don't combine them.",
            ),
        ),
    ),
    Section(
        "Effects",
        "Effects - Messages & Channels",
        "Effects that remove content, post messages or slow a channel down.",
        RED,
        (
            (
                "`DELETE_MESSAGE`",
                (
                    "Deletes the message that triggered the rule. No config.\n"
                    "Needs *Manage Messages* in that channel. If someone else already deleted the message, nothing happens."
                ),
            ),
            (
                "`DELETE_MULTIPLE_MESSAGES`",
                (
                    "Removes several recent messages from the user.\n"
                    "**Config:** *Message Count* (1-100, default 3) and *Max Age* (default 15s; `15s`, `2m`, `1h`; a bare number means seconds).\n"
                    "**Limits:** Discord can't bulk-delete messages older than 14 days, and 100 is the most per request.\n"
                    "**Use with** spam and scam rules to clean up everything the user just posted."
                ),
            ),
            (
                "`SEND_MESSAGE`",
                (
                    "Posts a message.\n"
                    "**Config:** *Message* (required, up to 1000 characters), *Channel* (empty = the channel where the rule fired), "
                    "*Delete After* (e.g. `10s`; empty keeps it), *Ping the user*.\n"
                    "**Tip:** short public notices with *Delete After 10s* keep channels tidy.\n"
                    "**Loop warning:** text that matches the rule's own trigger can re-trigger it. Add `IGNORE_BOTS`."
                ),
            ),
            (
                "`SEND_ALERT`",
                (
                    "Sends an alert embed, usually to a mod-log channel.\n"
                    "**Config:** *Alert Message* (required, up to 1000 characters), *Channel* (empty = the channel where the rule fired).\n"
                    "The bot needs *Embed Links* there. Alerts are the safest first effect for any new rule."
                ),
            ),
            (
                "`ENABLE_SLOWMODE`",
                (
                    "Turns on slowmode in the channel where the rule fired.\n"
                    "**Config:** *Slowmode Delay* (1 second to 6 hours; a bare number means seconds) and *Duration* (empty = stays on until someone removes it).\n"
                    "**Tips:** always set a *Duration* so it lifts itself. Members with *Manage Messages* or *Manage Channels* ignore slowmode."
                ),
            ),
        ),
    ),
    Section(
        "Effects",
        "Effects - Punishments",
        "Effects that act on the member. Use them last, or behind a violation threshold.",
        RED,
        (
            (
                "`WARN_USER`",
                (
                    "Warns the user. *Message* (optional, up to 1000 characters) is what they're told.\n"
                    "Messages sent to users may not arrive if they have DMs closed."
                ),
            ),
            (
                "`TIMEOUT_USER`",
                (
                    "Applies Discord's native timeout.\n"
                    "**Config:** *Duration* (required; from 1 minute to 28 days), *Message* (optional).\n"
                    "Needs *Moderate Members*. Administrators and the owner can't be timed out."
                ),
            ),
            (
                "`MUTE_USER`",
                (
                    "Mutes the user.\n"
                    "**Config:** *Duration* (`30m`, `12h`, `7d`, `2w`; empty = permanent), *Message* (optional).\n"
                    "**Mute vs Timeout:** a mute can be permanent; a timeout is always temporary and capped at 28 days."
                ),
            ),
            (
                "`KICK_USER`",
                "Removes the member; they can rejoin. *Message* (optional) tells them why.\nNeeds *Kick Members* and a higher role than the target.",
            ),
            (
                "`BAN_USER`",
                (
                    "Bans the member.\n"
                    "**Config:** *Duration* (empty = permanent), *Message* (optional), *Delete Message History* (0-7 days).\n"
                    "**Tip:** deleting 1 day of history removes a spammer's recent messages in one step. Needs *Ban Members*."
                ),
            ),
            (
                "Choosing a punishment",
                (
                    "\N{BULLET} First offence \N{RIGHTWARDS ARROW} *Delete Message* + *Add Violation*\n"
                    "\N{BULLET} Repeat \N{RIGHTWARDS ARROW} *Timeout* (minutes to hours)\n"
                    "\N{BULLET} Persistent \N{RIGHTWARDS ARROW} longer timeout or *Kick*\n"
                    "\N{BULLET} Reserve *Ban* for scams, raids and ban-worthy content. Never use it for a single minor offence."
                ),
            ),
        ),
    ),
    Section(
        "Effects",
        "Effects - Violations, Roles & Nicknames",
        "Effects that change a user's record, roles or name.",
        RED,
        (
            (
                "`ADD_VIOLATION`",
                (
                    "Adds a violation to the user's record.\n"
                    "**Config:** *Violation Name* (optional, up to 100 characters). Name violations explicitly (`links`, `spam`, `caps`) so thresholds can target them."
                ),
            ),
            (
                "`RESET_VIOLATIONS`",
                (
                    "Clears a violation record for the user.\n"
                    "**Config:** *Violation Name* (optional, up to 100 characters).\n"
                    "**Use it** at the end of an escalation rule so the ladder starts over after the punishment."
                ),
            ),
            (
                "`GIVE_ROLE`",
                (
                    "Gives the user a role.\n"
                    "**Config:** *Role* (required) and *Duration* (`30m`, `12h`, `7d`, `2w`; empty = permanent).\n"
                    "The role must be below the bot's top role and can't be bot-managed or @everyone. Needs *Manage Roles*."
                ),
            ),
            (
                "`REMOVE_ROLE`",
                "Takes a role away from the user. Same config and requirements as *Give Role*. Leave *Duration* empty for a permanent removal.",
            ),
            (
                "`SET_NICKNAME`",
                (
                    "Changes the user's nickname.\n"
                    "**Config:** *Nickname* (up to 32 characters; empty clears the nickname).\n"
                    "Needs *Manage Nicknames* and a higher role than the target. Never set a nickname that matches your own nickname trigger."
                ),
            ),
        ),
    ),
)

REFERENCE = (
    Section(
        "Reference",
        "Violations System",
        "Violations are counters, not punishments. They let you escalate gradually.",
        GREEN,
        (
            (
                "How it works",
                (
                    "1. A rule adds a **named violation** with *Add Violation*.\n"
                    "2. A second rule uses the `VIOLATIONS` trigger to watch for *N violations of that name within M minutes*.\n"
                    "3. That rule punishes and, ideally, resets the record."
                ),
            ),
            (
                "Naming",
                (
                    "The name in `VIOLATIONS` must match the name given to *Add Violation*. Use short, lowercase, purpose-based names: `links`, `spam`, `slurs`. "
                    "Unnamed violations are harder to target, so always name them."
                ),
            ),
            (
                "`VIOLATIONS` vs `X_VIOLATION_IN_Y_MINUTES`",
                (
                    "`VIOLATIONS` watches one named violation and needs a name, a number and a window. "
                    "`X_VIOLATION_IN_Y_MINUTES` only needs a count and a window and looks at total violations."
                ),
            ),
            (
                "Example ladder",
                (
                    "```\n"
                    "links-strike     (priority 0)\n"
                    "  Trigger  Any Link\n"
                    "  Effects  Delete Message\n"
                    "           Add Violation: links\n"
                    "\n"
                    "links-escalate   (priority 10)\n"
                    "  Trigger  Violations: links, 3 within 60 min\n"
                    "  Effects  Timeout 1h\n"
                    "           Reset Violations: links\n"
                    "```"
                ),
            ),
            (
                "Avoid loops",
                "Don't add a violation of the same name inside the rule that triggers on it. The record would keep growing and the rule keep firing.",
            ),
        ),
    ),
    Section(
        "Reference",
        "Lists",
        "Reusable lists referenced by word and website triggers.",
        GREEN,
        (
            (
                "Word lists",
                "Separate entries with spaces or new lines. Each entry is a **single word** with no spaces. For phrases, use a regular-expression trigger.",
            ),
            (
                "Website lists",
                "Write only the domain, with no protocol or path: `example.com`. Subdomains are included automatically.",
            ),
            (
                "Denylist vs allowlist",
                (
                    "**Denylist:** fires on a listed entry. An empty denylist never fires.\n"
                    "**Allowlist:** fires on anything *not* listed. An empty allowlist fires on every message with words or links."
                ),
            ),
            (
                "Attaching a list",
                "Triggers take the list by name (*List Name*, optional, up to 100 characters). A trigger without a list has nothing to compare against.",
            ),
            (
                "Tips",
                (
                    "\N{BULLET} Keep one purpose per list.\n"
                    "\N{BULLET} Entries are whole words, so catching variants (`fr33`, `f r e e`) needs a regex.\n"
                    "\N{BULLET} Review lists when you notice false positives."
                ),
            ),
        ),
    ),
    Section(
        "Reference",
        "Regular Expressions",
        "Patterns use RE2. They are fast and can't hang the bot, but a few features are missing.",
        GREEN,
        (
            (
                "Supported",
                (
                    "`.` `[a-z]` `[^abc]` `\\d` `\\w` `\\s` `\\b` \N{MIDDLE DOT} groups `(...)` and `(?:...)` \N{MIDDLE DOT} alternation `a|b` \N{MIDDLE DOT} "
                    "quantifiers `*` `+` `?` `{n,m}` and lazy `*?` \N{MIDDLE DOT} anchors `^` `$` \N{MIDDLE DOT} flags `(?i)` case-insensitive and `(?s)` dot matches newlines."
                ),
            ),
            (
                "Not supported",
                (
                    "Lookahead `(?=...)` `(?!...)`, lookbehind `(?<=...)` `(?<!...)`, backreferences such as `(.)\\1`, atomic and possessive groups. "
                    "Patterns that use them are rejected when you save."
                ),
            ),
            (
                "Handy patterns",
                (
                    "`(?i)free\\s+nitro` - \N{LEFT DOUBLE QUOTATION MARK}free nitro\N{RIGHT DOUBLE QUOTATION MARK} in any case\n"
                    "`^[0-9]+$` - message is only digits\n"
                    "`(?i)\\b(buy|sell)\\b.{0,40}\\b(nitro|robux)\\b` - trade spam\n"
                    "`(?i)f\\W*r\\W*e\\W*e` - \N{LEFT DOUBLE QUOTATION MARK}free\N{RIGHT DOUBLE QUOTATION MARK} with separators between the letters\n"
                    "`(?i)(https?://)?[a-z0-9.-]+\\[\\.\\][a-z]{2,}` - `example[.]com` style links"
                ),
            ),
            (
                "Rules of thumb",
                (
                    "\N{BULLET} Patterns are case-sensitive unless you add `(?i)`.\n"
                    "\N{BULLET} Anchor with `^` and `$` when you mean the whole message.\n"
                    "\N{BULLET} Maximum 500 characters.\n"
                    "\N{BULLET} Detecting \N{LEFT DOUBLE QUOTATION MARK}any character repeated 10 times\N{RIGHT DOUBLE QUOTATION MARK} needs a backreference, which RE2 lacks. Use `a{10,}` for specific characters or `X_CONSECUTIVE_IDENTICAL_MESSAGES`."
                ),
            ),
        ),
    ),
    Section(
        "Reference",
        "Limits Reference",
        "Every number you can run into.",
        GREEN,
        (
            (
                "Rules",
                (
                    "```\n"
                    "Rule name .............. 1-100 characters\n"
                    "Priority ............... whole number\n"
                    "Effects per rule ....... 15\n"
                    "Triggers per rule ...... 1\n"
                    "Conditions ............. 1 per condition type\n"
                    "Roles/channels/cats .... 25 per condition\n"
                    "```"
                ),
            ),
            (
                "Text fields",
                (
                    "```\n"
                    "Regex pattern .......... 500 characters\n"
                    "Warn/kick/ban/mute/\n"
                    "timeout/send/alert ..... 1000 characters\n"
                    "Nickname ............... 32 characters\n"
                    "Violation / list name .. 100 characters\n"
                    "Counts and lengths ..... up to 99999\n"
                    "```"
                ),
            ),
            (
                "Time and size",
                (
                    "```\n"
                    "Rate-limit window ...... 1 minute or more\n"
                    "Condition durations .... 1 minute or more\n"
                    "Timeout ................ 1 minute - 28 days\n"
                    "Slowmode delay ......... 1 second - 6 hours\n"
                    "Bulk delete ............ 1-100 messages\n"
                    "Ban history cleanup .... 0-7 days\n"
                    "```"
                ),
            ),
            (
                "Discord's own limits",
                (
                    "\N{BULLET} Messages: 2000 characters (4000 with Nitro)\n"
                    "\N{BULLET} Usernames and nicknames: 32 characters\n"
                    "\N{BULLET} Bulk delete can't remove messages older than 14 days\n"
                    "\N{BULLET} Slowmode maximum 6 hours; timeout maximum 28 days\n"
                    "\N{BULLET} Select menus return at most 25 choices"
                ),
            ),
        ),
    ),
)

TROUBLESHOOTING = (
    Section(
        "Troubleshooting",
        "When a Rule Can Never Fire",
        "These setups are valid to save but impossible to satisfy. Check them first.",
        GOLD,
        (
            (
                "Thresholds beyond Discord's limits",
                (
                    "\N{BULLET} `ALL_CAPS` Minimum Characters **5000**: messages stop at 2000 (4000 with Nitro).\n"
                    "\N{BULLET} `MESSAGE_LENGTH_GT` at **2000 or more** (4000 or more with Nitro).\n"
                    "\N{BULLET} `MESSAGE_MENTIONS` Count above roughly **90**.\n"
                    "\N{BULLET} A regex that needs more than 2000 characters.\n"
                    "\N{BULLET} Nickname or username patterns that need more than **32** characters.\n"
                    "**Rule of thumb:** an ordinary message must be able to reach the threshold."
                ),
            ),
            (
                "Unreachable rate limits",
                (
                    "\N{BULLET} 8 messages per minute in a channel whose slowmode allows 4-5.\n"
                    "\N{BULLET} Window of less than a minute (the minimum is 1).\n"
                    "\N{BULLET} Channel counts bigger than the channel's real traffic."
                ),
            ),
            (
                "Contradicting conditions",
                (
                    "\N{BULLET} Same channel in *Ignored Channels* and *Active Channels*.\n"
                    "\N{BULLET} *Active Channels* and *Active Categories* that don't overlap.\n"
                    "\N{BULLET} *Account Age Above 30d* with *Account Age Below 7d* (same for *Member Duration*).\n"
                    "\N{BULLET} *Required Roles* with *Require all* and roles nobody holds together, or a deleted role.\n"
                    "\N{BULLET} *Active in Threads* with channels where nobody makes threads."
                ),
            ),
            (
                "Wrong event for the setup",
                (
                    "\N{BULLET} `MEMBER_DURATION_ABOVE` on `NEW_MEMBER`.\n"
                    "\N{BULLET} Channel, category, thread, new/edited or forward conditions on join, nickname or violation triggers.\n"
                    "\N{BULLET} *Delete Message* on triggers that have no message.\n"
                    "\N{BULLET} *Timeout*, *Give Role* or *Set Nickname* after *Kick* or *Ban*."
                ),
            ),
            (
                "Empty or missing lists",
                (
                    "\N{BULLET} A denylist with no entries never fires.\n"
                    "\N{BULLET} A trigger with no list attached has nothing to match.\n"
                    "\N{BULLET} An allowlist with no entries fires on everything instead (the opposite problem)."
                ),
            ),
            (
                "State problems",
                (
                    "\N{BULLET} The rule is **disabled**.\n"
                    "\N{BULLET} Edits weren't saved. Press **Save changes**.\n"
                    "\N{BULLET} Your test account is exempt (moderator role, or administrator)."
                ),
            ),
        ),
    ),
    Section(
        "Troubleshooting",
        "Permissions & Discord Limits",
        "When the rule fires but the effect doesn't land.",
        GOLD,
        (
            (
                "Bot-wide switches",
                (
                    "Content-based triggers need the bot's **Message Content** intent, and join and nickname triggers need the **Server Members** intent. "
                    "If content triggers do nothing anywhere, this is the usual cause. The bot's owner enables these in the Developer Portal."
                ),
            ),
            (
                "Channel permissions",
                (
                    "Server-wide permissions aren't enough when a channel overwrite denies them. The bot needs **View Channel** to see messages, "
                    "**Manage Messages** to delete them, and **Send Messages** (plus **Embed Links** for alerts) wherever it posts."
                ),
            ),
            (
                "Role hierarchy",
                (
                    "The bot's top role must sit above the target's top role. Move the bot's role up in *Server Settings \N{RIGHTWARDS ARROW} Roles*. "
                    "Owners and administrators are protected from kicks, bans and timeouts."
                ),
            ),
            (
                "Moderator bypasses",
                (
                    "Slowmode doesn't apply to members with *Manage Messages* or *Manage Channels*. "
                    "Your own test account may be exempt without you realising."
                ),
            ),
            (
                "Delivery limits",
                (
                    "\N{BULLET} Messages sent to users may not arrive if their DMs are closed.\n"
                    "\N{BULLET} Bulk delete skips messages older than 14 days.\n"
                    "\N{BULLET} During large raids, Discord's API rate limits can delay effects.\n"
                    "\N{BULLET} A message already deleted by someone else can't be deleted again."
                ),
            ),
        ),
    ),
    Section(
        "Troubleshooting",
        "Common Bypasses",
        "How people get around rules, and how to close the gaps.",
        GOLD,
        (
            (
                "Editing a clean message",
                "Don't add `NEW_MESSAGE` to content rules, or edits slip through. Use it only for rate limits.",
            ),
            (
                "Spelling tricks",
                (
                    "`fr33`, `f r e e`, zero-width characters and look-alike letters beat plain word lists. "
                    "Use regex with `\\W*` between letters, and review logs for new variants."
                ),
            ),
            (
                "Obfuscated links",
                "`example[.]com` and `example dot com` aren't valid links, so `ANY_LINK` and website lists miss them. Add a regex rule.",
            ),
            (
                "Link shorteners",
                "A denylist sees the shortener's domain, not the destination. Prefer allowlists in sensitive channels, or denylist the shortener.",
            ),
            (
                "Splitting across messages",
                "Words and regexes inspect one message at a time. Rate-limit triggers catch volume, so layer both.",
            ),
            (
                "Uncovered channels",
                "A rule scoped with *Active Channels* never covers new channels. Scope by *Active Categories* instead, so new channels in that category are covered automatically.",
            ),
            (
                "Compromised staff",
                "*Ignored Roles* trusts the role, not the person. Keep that role small, and give staff accounts two-factor authentication.",
            ),
        ),
    ),
    Section(
        "Troubleshooting",
        "Troubleshooting Checklist",
        "Work through the list that matches your symptom.",
        GOLD,
        (
            (
                "The rule never fires",
                (
                    "1. Is it **enabled** and saved? Check `/automod list`.\n"
                    "2. Is the trigger reachable? Compare it with *When a Rule Can Never Fire*.\n"
                    "3. Remove all conditions, test, then add them back one at a time.\n"
                    "4. Are you testing as an exempt account?\n"
                    "5. Is it a new message or an edit, and do your conditions allow that?\n"
                    "6. Can the bot see the channel?"
                ),
            ),
            (
                "It fires but nothing happens",
                (
                    "1. Does the bot have the permission listed under *Effects - Overview*?\n"
                    "2. Is the bot's top role above the target's?\n"
                    "3. Does the effect fit the event (message effect on a join)?\n"
                    "4. Is the user already gone (kick or ban earlier)?\n"
                    "5. Is the target an administrator or the owner?"
                ),
            ),
            (
                "It fires too often",
                (
                    "\N{BULLET} `MESSAGE_NOT_REGEX`, allowlists and `WITHOUT_ATTACHMENTS` without *Active Channels*.\n"
                    "\N{BULLET} `NEW_MEMBER` without an account-age condition.\n"
                    "\N{BULLET} `ALL_CAPS` left at 3 characters and 100%.\n"
                    "\N{BULLET} Two overlapping rules doing the same thing."
                ),
            ),
            (
                "It fires repeatedly",
                (
                    "\N{BULLET} *Send Message* or *Send Alert* text that matches its own trigger. Add `IGNORE_BOTS`.\n"
                    "\N{BULLET} *Set Nickname* applying a name that still matches the nickname trigger.\n"
                    "\N{BULLET} A violation added by the same rule that triggers on it."
                ),
            ),
            (
                "Testing safely",
                (
                    "Create a private test channel and set *Active Channels* to it. Start with *Send Alert* only, test with a non-staff account, "
                    "then swap in real effects and widen the scope."
                ),
            ),
        ),
    ),
)

PRACTICE = (
    Section(
        "Practice",
        "Best Practices",
        "Habits that keep a rule set effective and quiet.",
        PURPLE,
        (
            (
                "Design",
                (
                    "\N{BULLET} **One purpose per rule.** Name rules by what they do: `links-general`, `spam-user`, `raid-new-accounts`.\n"
                    "\N{BULLET} **Scope everything** with channels or categories, and exempt staff with *Ignored Roles*.\n"
                    "\N{BULLET} **Escalate** through violations rather than punishing on the first offence.\n"
                    "\N{BULLET} **Specific beats broad.** Several narrow rules beat one that tries to cover everything."
                ),
            ),
            (
                "Rolling out",
                (
                    "1. Alert-only in a test channel.\n"
                    "2. Alert-only in the real channels. Read the logs for false positives.\n"
                    "3. Add *Delete Message* and *Add Violation*.\n"
                    "4. Add punishments through a threshold rule."
                ),
            ),
            (
                "Messages to members",
                (
                    "\N{BULLET} Say what was wrong and what to do instead.\n"
                    "\N{BULLET} Use *Delete After 10s* on public notices.\n"
                    "\N{BULLET} Don't reveal exact thresholds; people optimise against them."
                ),
            ),
            (
                "Punishments",
                (
                    "\N{BULLET} Delete first, punish second.\n"
                    "\N{BULLET} Keep timeouts short at first (minutes) and grow them with repeat offences.\n"
                    "\N{BULLET} Use *Ban* with 1 day of message history for scams and raids only.\n"
                    "\N{BULLET} Prefer *Timeout* for compromised accounts so owners can recover them."
                ),
            ),
            (
                "Maintenance",
                (
                    "\N{BULLET} Review the logs weekly and tune thresholds.\n"
                    "\N{BULLET} Keep disabled rules disabled instead of editing them to \N{LEFT DOUBLE QUOTATION MARK}off\N{RIGHT DOUBLE QUOTATION MARK}.\n"
                    "\N{BULLET} After deleting roles or channels, re-check rules that reference them.\n"
                    "\N{BULLET} Re-test after changing bot permissions or role order."
                ),
            ),
        ),
    ),
    Section(
        "Practice",
        "Example Rules - Content",
        "Ready-to-adapt recipes. Replace names and IDs with your own.",
        PURPLE,
        (
            (
                "No links in #general",
                (
                    "```\n"
                    "Trigger     Any Link\n"
                    "Conditions  Active Channels: #general\n"
                    "            Ignored Roles: @Moderator\n"
                    "Effects     Delete Message\n"
                    "            Add Violation: links\n"
                    '            Send Message: "Links aren\'t allowed here."\n'
                    "              Delete After 10s, Ping the user\n"
                    "```"
                ),
            ),
            (
                "Image-only #showcase",
                (
                    "```\n"
                    "Trigger     Message Without Attachments\n"
                    "Conditions  Active Channels: #showcase\n"
                    "            Ignored Roles: @Moderator\n"
                    "Effects     Delete Message\n"
                    '            Send Message: "Posts here need an image."\n'
                    "              Delete After 10s\n"
                    "```"
                ),
            ),
            (
                "Counting channel",
                (
                    "```\n"
                    "Trigger     Message Not Regex: ^[0-9]+$\n"
                    "Conditions  Active Channels: #counting\n"
                    "            Ignored Roles: @Moderator\n"
                    "Effects     Delete Message\n"
                    "```"
                ),
            ),
            (
                "Shouting",
                (
                    "```\n"
                    "Trigger     All Caps: 15 characters, 70%\n"
                    "Conditions  Ignored Roles: @Moderator\n"
                    'Effects     Warn User: "Please don\'t shout."\n'
                    "            Add Violation: caps\n"
                    "```"
                ),
            ),
            (
                "Invite ads",
                (
                    "```\n"
                    "Trigger     Server Invites\n"
                    "Conditions  Ignored Channels: #partners\n"
                    "            Ignored Roles: @Moderator\n"
                    "Effects     Delete Message\n"
                    "            Add Violation: ads\n"
                    "```"
                ),
            ),
            (
                "New members and links",
                (
                    "```\n"
                    "Trigger     Any Link\n"
                    "Conditions  Member Duration Below: 1d\n"
                    "            Ignored Roles: @Moderator\n"
                    "Effects     Delete Message\n"
                    '            Send Message: "Links unlock after a day."\n'
                    "              Delete After 10s\n"
                    "```"
                ),
            ),
            (
                "Scam links",
                (
                    "```\n"
                    "Trigger     Flagged Scam Links\n"
                    "Effects     Delete Message\n"
                    "            Delete Multiple Messages: 10, max age 5m\n"
                    "            Timeout User: 28d\n"
                    "            Send Alert: #mod-log\n"
                    "```"
                ),
            ),
        ),
    ),
    Section(
        "Practice",
        "Example Rules - Escalation & Raids",
        "Recipes that combine rate limits, violations and member events.",
        PURPLE,
        (
            (
                "Link ladder (two rules)",
                (
                    "```\n"
                    "links-strike\n"
                    "  Trigger  Any Link\n"
                    "  Effects  Delete Message\n"
                    "           Add Violation: links\n"
                    "\n"
                    "links-escalate (priority 10)\n"
                    "  Trigger  Violations: links, 3 within 60 min\n"
                    "  Effects  Timeout User: 1h\n"
                    "           Reset Violations: links\n"
                    "```"
                ),
            ),
            (
                "Message flood",
                (
                    "```\n"
                    "Trigger     X User Message In Y Minutes: 8 in 1\n"
                    "Conditions  Ignored Roles: @Moderator\n"
                    "Effects     Delete Multiple Messages: 8, max age 1m\n"
                    "            Timeout User: 10m\n"
                    "            Add Violation: spam\n"
                    "```"
                ),
            ),
            (
                "Channel raid shield",
                (
                    "```\n"
                    "Trigger     X Channel Message In Y Minutes: 40 in 1\n"
                    "Effects     Enable Slowmode: 30s, duration 10m\n"
                    "            Send Alert: #mod-log\n"
                    "```"
                ),
            ),
            (
                "Brand-new accounts",
                (
                    "```\n"
                    "Trigger     New Member\n"
                    "Conditions  Account Age Below: 3d\n"
                    "Effects     Give Role: @Unverified\n"
                    "            Send Alert: #mod-log\n"
                    "```\n"
                    "Restrict what @Unverified can do through role permissions."
                ),
            ),
            (
                "Nickname enforcement",
                (
                    "```\n"
                    "Trigger     Nickname Word Denylist: bad-names\n"
                    "Effects     Set Nickname: Moderated Nickname\n"
                    "            Add Violation: nickname\n"
                    "```\n"
                    "Make sure the replacement name isn't on the list."
                ),
            ),
            (
                "Offensive usernames on join",
                (
                    "```\n"
                    "Trigger     Join Username Word Denylist: bad-names\n"
                    'Effects     Kick User: "Please pick another username."\n'
                    "            Send Alert: #mod-log\n"
                    "```"
                ),
            ),
            (
                "Attachment spam",
                (
                    "```\n"
                    "Trigger     X User Attachments In Y Minutes: 5 in 1\n"
                    "Conditions  Ignored Roles: @Moderator\n"
                    "Effects     Delete Multiple Messages: 5, max age 1m\n"
                    "            Timeout User: 5m\n"
                    "```"
                ),
            ),
        ),
    ),
    Section(
        "Practice",
        "Logs",
        "Use the Logs tab to inspect rule execution and troubleshoot configurations.",
        PURPLE,
        (
            (
                "Logged information",
                "\N{BULLET} Which user triggered the rule\n\N{BULLET} Which rule fired\n\N{BULLET} When the rule fired\n\N{BULLET} Which trigger caused the rule to fire",
            ),
            (
                "Not logged",
                "Logs are not a complete record of messages and do not record moderation actions themselves.",
            ),
            (
                "Using logs well",
                "Read them while a new rule is in alert-only mode. Frequent hits from staff or off-topic channels mean you need to tighten conditions.",
            ),
        ),
    ),
)

SECTIONS = (*GUIDE, *TRIGGERS, *CONDITIONS, *EFFECTS, *REFERENCE, *TROUBLESHOOTING, *PRACTICE)


def contents_page(entries: list[tuple[str, str, int]]) -> discord.Embed:
    lines: list[str] = []
    current_group = ""
    for group, title, page in entries:
        if group != current_group:
            lines.append(f"\n**{group}**")
            current_group = group
        lines.append(f"`{page:>2}` {title}")
    return discord.Embed(title="Contents", description="\n".join(lines).strip(), colour=BLUE)


def automod_embeds() -> list[discord.Embed]:
    rendered = [render(section) for section in SECTIONS]

    first = rendered[0]
    entries: list[tuple[str, str, int]] = []
    next_page = len(first) + 2
    for section, embeds in zip(SECTIONS[1:], rendered[1:], strict=True):
        entries.append((section.group, section.title, next_page))
        next_page += len(embeds)

    pages = [*first, contents_page(entries)]
    for embeds in rendered[1:]:
        pages.extend(embeds)
    return pages
