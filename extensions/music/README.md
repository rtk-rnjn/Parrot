# Music

Voice and music playback backed by Lavalink/Pomice.

## Scope

Join and leave voice, play tracks, manage the queue, show now-playing information, skip, stop, and coordinate player votes.

## Behaviour

- Every reply is a components v2 layout (`core.utils.NoticeLayout`), colour-coded: green for success, blurple for information, orange for warnings and red for errors.
- `skip`, `stop`, `leave` and `play` require the caller to be in the bot's voice channel.
- The DJ acts at once; everyone else votes, and an action passes once half of the listeners agree. The DJ is the longest-standing listener who can manage channels, otherwise the member who connected the bot, otherwise the longest-standing listener.
- The queue advances only on Lavalink's `finished` and `loadFailed` track-end reasons, so skips, stops and track exceptions never advance the queue twice.
- Only voice channels are supported; stage channels are refused with a warning.
