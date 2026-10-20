# Tags

Tags are saved snippets of text that you can pull up by name. Think of them as your server's own set of shortcuts: rules, FAQ answers, links, inside jokes, copy-paste replies you're tired of typing out.

Type `!tag rules` and the bot posts whatever someone saved under the name `rules`.

> Examples on this page use `!` as the prefix. If your server uses a different one, swap it in.

Tags belong to **one server**. A tag made in your server can't be seen from another, and the commands only work inside a server.

---

## All commands at a glance

| Command | Other names | What it does |
|---|---|---|
| `tag <name>` | none | Shows a tag |
| `tags` | none | Lists every tag in the server |
| `tag all` | `list`, `ls` | Same as `tags` |
| `tag create <name> <content>` | `add`, `new`, `+` | Makes a new tag |
| `tag edit <name> <new content>` | `update` | Changes what a tag says |
| `tag delete <name>` | `remove`, `rm`, `del` | Deletes a tag |
| `tag raw <name>` | none | Shows a tag as plain text, mentions and all |
| `tag search <text>` | none | Finds tags by name or alias |
| `tag count <name>` | `usage`, `stats` | Shows how often a tag has been used |
| `tag top users` | none | Who uses tags the most |
| `tag top used` | `tags` | Which tags are used the most |
| `tag transfer <name> <member>` | none | Gives a tag to someone else |
| `tag nsfw <name>` | `mark-nsfw` | Marks a tag as 18+ |
| `tag alias add <tag> <alias>` | `create`, `new` | Gives a tag a second name |
| `tag alias remove <tag> <alias>` | `delete`, `rm`, `del` | Removes one of those names |

---

## Using tags

### Showing a tag

```
!tag rules
!tag faq install
```

Type the name (or an alias) and the bot replies with the saved text. It never pings anyone, even if the tag has mentions in it. Each time you view a tag, it counts towards the usage stats.

If the tag doesn't exist, you'll be told.

### Browsing

```
!tags
```

Lists every tag in the server, ten to a page. Use the buttons to flip through. `!tag all` does the same thing.

### Searching

```
!tag search rule
```

Looks through tag names **and aliases** for your text and shows what it finds, ten per page.

### Raw view

```
!tag raw welcome
```

Shows the tag's text without letting mentions do anything. Handy when you want to **copy** a tag to edit it, or see what's really inside.

---

## Making and managing tags

### Creating a tag

```
!tag create rules Be kind. No spam. Have fun.
!tag create "server ip" play.example.com
```

The first word is the **name**, and everything after it is the **content**. If you want a name with spaces, put it in quotes, like `"server ip"` above.

- Anyone can create tags.
- Names must be unique. If a tag or alias already uses that name, the bot says so.
- Mentions in the content get neutralized so a tag can't be used to sneak in pings.
- If you create a tag **in an NSFW channel**, it's automatically marked as NSFW.

### Editing a tag

```
!tag edit rules Be kind. No spam. No politics. Have fun.
```

Replaces the text with whatever you type. Edits are for the tag's owner.

### Deleting a tag

```
!tag delete rules
```

Only the **tag's owner** or a **server administrator** can delete a tag. The bot asks you to confirm first, so you won't delete one by accident.

### Transferring ownership

```
!tag transfer rules @someone
```

Hands the tag over to another member. Same rule as deleting: only the owner or an administrator, and you'll be asked to confirm.

### Marking a tag NSFW

```
!tag nsfw spicy-meme
```

NSFW tags only show up in NSFW (age-restricted) channels. Try to view one anywhere else and the bot refuses. Only the owner or an administrator can mark a tag.

---

## Aliases

An alias is a second name for the same tag. If your tag is called `frequently-asked-questions`, you probably want `faq` to work too.

```
!tag alias add frequently-asked-questions faq
!tag alias remove frequently-asked-questions faq
```

- The alias can't already be used by another tag or alias.
- Once added, `!tag faq` shows the same text as the full name.
- `!tag alias` on its own shows the list of alias commands.

---

## Stats

### Usage of one tag

```
!tag count rules
```

Tells you how many times the tag has been used in total, and by how many different people.

### Leaderboards

```
!tag top users     → people who use tags the most
!tag top used      → the most popular tags
```

Both show a ranked list. If nothing has been used yet, you'll be told that too. `!tag top` on its own shows the list of these commands.

---

## Quick FAQ

**Can anyone make a tag?**
Yes. Anyone in the server can create one. Only the owner (or an admin) can delete, transfer or mark it NSFW.

**How do I make a tag with a name that has spaces?**
Put the name in quotes when you create it: `!tag create "my tag" some text`.

**The tag text pinged nobody. Is that normal?**
Yes. The bot posts tags with pings turned off on purpose.

**A tag says I need an NSFW channel.**
That tag is marked 18+. Use it in an age-restricted channel.

**I can't remember what a tag is called.**
Try `!tags` to see them all, or `!tag search <word>`.
