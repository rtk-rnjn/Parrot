# Reminders & Timezones

Forget things less. Tell the bot what and when, and it pings you at the right moment. You can make reminders repeat, snooze them when they go off, and manage them all from one panel.

> Examples on this page use `!` as the prefix. If your server uses a different one, swap it in.

---

## All commands at a glance

| Command | Other names | What it does |
|---|---|---|
| `remind <time> <what>` | `reminder`, `remindme`, `remindin` | Sets a reminder |
| `reminders` | none | Opens your reminder panel (view, edit, delete, create) |
| `timezone` | `tz` | Shows your timezone and lets you pick a new one |
| `timezone set [name]` | `change`, `update` | Sets your timezone |
| `timezone info <name>` | none | Shows the current time and UTC offset of any timezone |

These work in servers and in DMs with the bot.

**Do this first:** set your timezone with `!timezone`. Until you do, the bot reads every time you type as **UTC**, so "tomorrow 9am" might not mean what you think.

---

## Setting a reminder

### `remind`

The fast way. Type the time first, then what you want to be reminded about.

```
!remind 2h take the pizza out
!remind 1d30m call mom
!remind 1w submit the assignment
```

Right after, the bot confirms with the exact time, and gives you two things under the message:

- A **Repeat** dropdown, so you can make it come back every day, week or month
- A **Cancel reminder** button, in case you change your mind

Only you can use those controls.

---

### How to write the time

The time goes at the very start. Use a number followed by a unit, and stick them together with no spaces.

| You type | It means |
|---|---|
| `30s` | 30 seconds |
| `10m` | 10 minutes |
| `2h` | 2 hours |
| `1d` | 1 day |
| `2w` | 2 weeks |
| `3mo` | 3 months |
| `1y` | 1 year |
| `1h30m` | 1 hour 30 minutes |
| `1d12h` | 1 day 12 hours |

Spelled-out versions like `2hours` or `3days` work too. There's one catch: don't put a space *inside* the time. `1h30m` is good, `1h 30m` is not (the bot would read `30m` as part of your reminder text).

You can also paste a Discord timestamp (like `<t:1893456000>`) as the time.

**Want to type a date or something like "tomorrow 9am"?** Use the reminder panel below. It has a *When* box that understands plain language.

---

### The reminder panel

```
!reminders
```

This opens a panel with all your active reminders, soonest first, five to a page. For each one you see when it will go off, what it says, and whether it repeats.

What you can do there:

- **New reminder** (the plus button): opens a form with three boxes:
  - *Remind me to*: what to remind you about (up to 500 characters)
  - *When*: type it naturally, like `in 2 hours`, `tomorrow 9am` or `2026-12-01 18:00`
  - *Repeat*: doesn't repeat, every day, every week, or every month
- **Edit** (the pencil next to a reminder): opens the same form with everything filled in. Leave the time box alone and it keeps the original time.
- **Delete**: pick one or more reminders from the dropdown and they're deleted straight away.
- **Arrows**: move between pages.

The panel only works for the person who opened it.

If you edit a reminder that has already gone off, the bot lets you know it already fired.

---

## When a reminder goes off

The bot posts in the **same channel** where you set it and pings you:

> @you, here's your reminder: take the pizza out

If it can't post there (it lost access, or the channel is gone), it sends you a **DM** instead.

Under the message you'll find:

- **Snooze for...**: pick 5 minutes, 15 minutes, 30 minutes, 1 hour, 3 hours, or tomorrow
- **Custom snooze**: type your own time
- **Original message**: a link back to where you set it (when there is one)

A snoozed reminder comes back at the new time. If the reminder repeats, snoozing doesn't break the repeat. The next regular one is already lined up.

Reminders are saved, so they survive bot restarts. If the bot happened to be offline when yours was due, it goes off as soon as the bot is back.

---

## Repeating reminders

Pick one of these in the Repeat dropdown (under a new reminder, or inside the panel):

- **Every day**
- **Every week**
- **Every month**
- **Does not repeat** (the default)

Repeats stick to your **local clock time**. A reminder for 9:00 AM stays at 9:00 AM for you, even when daylight saving kicks in, as long as your timezone is set properly.

To stop a repeating reminder, delete it in the `!reminders` panel.

---

## Timezones

Your timezone is how the bot reads the times you type, such as "tomorrow 9am". It also decides what your local clock looks like for repeating reminders. Short times like `2h` don't depend on it.

### `timezone`

```
!timezone
```

Shows your current timezone (or tells you it isn't set and that times are being read as UTC), with a dropdown of popular choices:

India, New York, Chicago, Denver, Los Angeles, Toronto, São Paulo, London, Paris, Berlin, Athens, Istanbul, Moscow, Dubai, Dhaka, Bangkok, Shanghai, Tokyo, Brisbane, Sydney, Auckland.

Pick one and you're done. The bot confirms with your local time.

### `timezone set`

Don't see yours in the menu? Type it:

```
!timezone set Asia/Kolkata
!timezone set IST
!timezone set Pacific Time
!timezone set America/Chicago
```

Official names like `Asia/Kolkata` always work. Common short names (`EST`, `PST`, `IST`, `Eastern Time` and so on) work too. If you type something close to a few options, the bot shows a short list so you can choose the right one. Run it with nothing after it to get the dropdown instead.

### `timezone info`

Check the time somewhere else.

```
!timezone info Asia/Tokyo
!timezone info London
```

You get the timezone's name, its current time, and how far it is from UTC.

---

## Quick FAQ

**My reminder went off at the wrong time.**
Check your timezone with `!timezone`. If it isn't set, everything is read as UTC.

**How do I write "tomorrow at 9am"?**
Use `!reminders`, press **New reminder**, and type it in the *When* box.

**Can I set a reminder for a specific date?**
Yes, in the panel. Something like `2026-12-01 18:00` works.

**How do I cancel a reminder?**
Press **Cancel reminder** under the bot's confirmation, or delete it any time from `!reminders`.

**How do I stop a repeating reminder?**
Delete it from `!reminders`. Snoozing only delays one reminder. It doesn't cancel the repeat.

**It says the time is in the past.**
The time you gave was earlier than right now. Check the timezone and the date.
