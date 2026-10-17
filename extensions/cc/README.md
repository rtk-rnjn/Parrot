# Custom Commands (`cc`)

Custom commands let server administrators create their own text commands, powered by [Jinja2](https://jinja.palletsprojects.com/en/stable/templates/) templates. When someone runs a custom command, the bot renders your template and sends the result to the channel.

Because templates are user-supplied code, they run inside a **hardened sandbox** with deliberately limited features. See [Limitations](#limitations).

## Quick start

1. Run `cc manage` (requires the **Administrator** permission).
2. Click **Create**, then fill in:
   - **Command name**: 1-32 characters; letters, numbers, `_` and `-` only. Names are stored in lowercase.
   - **Ignored Roles** *(optional)*: members with any of these roles can't trigger the command.
   - **Ignored Channels** *(optional)*: the command does nothing in these channels.
   - **Response template**: your Jinja2 template (max 3000 characters).
3. Run it like any other command: `<prefix><name>`.

```jinja
Welcome to {{ guild.name }}, {{ author.mention }}! We now have {{ guild.member_count }} members.
```

> A custom command can't reuse the name of an existing bot command.

## Managing commands

| Command | Description |
|---|---|
| `cc manage` | Opens the management panel: select, edit, delete, create, and browse built-in variable/example help. Also shows the 10 most recent invocation logs. |
| `cc edit <name>` | Edit the response and ignored roles/channels of an existing command. |
| `cc delete <name>` | Delete a command. |
| `cc rename <old_name> <new_name>` | Rename a command. The new name must be valid and not already taken. |

`cc` is also available as `customcommand`. All management commands require the **Administrator** permission.

Custom commands only work inside servers (not DMs) and are never triggered by bots.

## Template basics

| Syntax | Purpose |
|---|---|
| `{{ ... }}` | Print a value, e.g. `{{ author.name }}` |
| `{% ... %}` | Run logic: `if`, `for`, `set`, ... |
| `{# ... #}` | Comment (not printed) |
| `value \| filter` | Transform a value with a filter, e.g. `{{ message.content \| upper }}` |

Undefined variables are **errors**, not blank text. If you misspell `author.nmae`, the command fails instead of silently printing nothing.

## Variables

Four objects are available in every template.

### `author`: the member who ran the command

| Attribute | Description |
|---|---|
| `author.id` | User ID |
| `author.name` | Username |
| `author.display_name` | Display name (nickname if set) |
| `author.nick` | Server nickname, or `None` |
| `author.mention` | Mention string (`@user`) |
| `author.avatar_url` | Avatar URL |

### `message`: the message that triggered the command

| Attribute | Description |
|---|---|
| `message.id` | Message ID |
| `message.content` | Full text of the message, including the command itself |

### `guild`: the server

| Attribute | Description |
|---|---|
| `guild.id` | Server ID |
| `guild.name` | Server name |
| `guild.member_count` | Number of members |
| `guild.description` | Server description, or `None` |
| `guild.icon_url` (or `guild.icon`) | Icon URL, or `None` |
| `guild.banner_url` | Banner URL, or `None` |
| `guild.splash` / `guild.discovery_splash` | Splash image URLs, or `None` |
| `guild.vanity_url` | Vanity invite code, or `None` |
| `guild.premium_tier` | Boost tier |
| `guild.premium_subscription_count` | Number of boosts |
| `guild.preferred_locale` | Preferred locale name |
| `guild.afk_timeout` | AFK timeout in seconds |

### `channel`: the channel the command was used in

| Attribute | Description |
|---|---|
| `channel.id` | Channel ID |
| `channel.name` | Channel name |
| `channel.mention` | Clickable channel mention |
| `channel.jump_url` | Link to the channel |
| `channel.position` | Position in the channel list |
| `channel.type` | Channel type name (e.g. `text`) |
| `channel.category` | The parent category (same attributes as `channel`), or `None` |

Printing `author`, `guild`, or `channel` directly (e.g. `{{ guild }}`) prints its name.

### Actions on `author` (use with care)

| Method | Description |
|---|---|
| `author.kick(reason=...)` | Kicks the member who ran the command |
| `author.ban(reason=..., delete_message_days=...)` | Bans the member who ran the command |

These only work if the bot itself has the needed permission and its top role is above the member's top role. Otherwise they do nothing, silently.


## Logic

### Conditionals

```jinja
{% if author.name == 'admin' %}
  Hello, boss!
{% elif guild.member_count > 1000 %}
  We are a huge server!
{% else %}
  Hello, {{ author.display_name }}!
{% endif %}
```

Always close blocks with `{% endif %}`, `{% endfor %}`, etc.

### Loops

```jinja
Here are the words you typed:
{% for word in message.content.split() %}
- {{ word }}
{% endfor %}
```

### Variables and filters

```jinja
{% set user_name = author.display_name %}
Hello, {{ user_name }}!
{{ message.content | upper }}
```

Jinja's [built-in filters](https://jinja.palletsprojects.com/en/stable/templates/#list-of-builtin-filters) (`upper`, `lower`, `length`, `join`, `int`, `default`, ...) all work. Normal string methods (`.split()`, `.replace()`, `.lower()`) work too.

### Controlling whitespace

Loops and conditionals leave blank lines and indentation behind. Add a `-` inside the tag to trim surrounding whitespace:

```jinja
{%- for word in message.content.split() -%}
  {{ word }}{{ ", " if not loop.last }}
{%- endfor %}
```


## Limitations

The sandbox exists to keep the bot safe and responsive. If a template breaks a rule, the command fails and an error traceback is posted in the channel.

1. **No arbitrary Python.** `exec`, `eval`, and similar are not available.
2. **No private attributes.** Anything starting with an underscore (`_`) is blocked, as are Python internals like `__class__`.
3. **Read-only data.** The sandbox is *immutable*: methods that modify lists, dicts, or sets (`append`, `update`, ...) are blocked. Build new values instead.
4. **No built-in functions or globals.** `len()`, `sum()`, `range()`, `dict()`, etc. don't exist. Use filters instead (e.g. `{{ items | length }}`, `{{ items | sum }}`). Only `author`, `message`, `guild`, and `channel` are provided.
5. **No imports or inheritance.** `import`, `from ... import`, `include`, and `extends` are disabled.
6. **Capped repetition and concatenation.**
   - Repeating a sequence more than **10,000** times fails (`'a' * 10001`).
   - A repeated or concatenated string/list longer than **100,000** items fails (`[None] * 100_000_000`).
7. **No exponents.** The power operator (`**`) is disabled entirely.
8. **Output limits.**
   - The template itself is limited to 3000 characters in the editor.
   - Discord messages are limited to 2000 characters; longer output is cut off with `...`.
   - If the template renders to nothing, no message is sent.

## Examples

**Echo**

```jinja
You said: {{ message.content }}
```

**Keyword matching**

```jinja
{% if 'help' in message.content.lower() %}
  It looks like you need help! Check out the rules channel.
{% else %}
  Command received, {{ author.display_name }}.
{% endif %}
```

**Nickname check**

```jinja
{% if author.nick and 'VIP' in author.nick %}
  Access granted for VIP!
{% else %}
  Standard user access.
{% endif %}
```

**Word counter**

```jinja
Your message has {{ message.content.split() | length }} words!
```

**Character replacer**

```jinja
{{ message.content.replace('a', '@') }}
```

**Server goal tracker**

```jinja
Members needed for 1000: {{ 1000 - guild.member_count }}
```

**Looping over a fixed list**

```jinja
{% for item in ['red', 'green', 'blue'] %}
{{ loop.index }}. {{ item }}
{% endfor %}
```

**Nested conditions**

```jinja
{% if author.name == 'admin' %}
  Welcome, admin!
{% else %}
  {% if guild.member_count > 1000 %}
    We are a large server!
  {% else %}
    Hello, {{ author.display_name }}!
  {% endif %}
{% endif %}
```

## Troubleshooting

| Problem | Likely cause |
|---|---|
| Error mentioning `'x' is undefined` | Misspelled variable/attribute, or you used a function that doesn't exist (like `range` or `len`). |
| `... is disabled` / `exceeds configured limit` | You hit a sandbox rule; see [Limitations](#limitations). |
| Command does nothing | Output was empty, or you're in an ignored channel or have an ignored role. |
| "already exists as a bot command" | Pick a different name. |
| Output has strange blank lines | See [Controlling whitespace](#controlling-whitespace). |
