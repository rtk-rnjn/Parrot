# Parrot Discord Bot

A good moderation and Ticket Service bot. Basically made for helping the mods! Configuring the bot is relativly easy
### Self Host? 

No Help will be given if You are self Hosting. Tho' Bot is very easy to understand there is No Thetha Theroy. Yes, if you need any Python Help. You can ask me out at my Discord Server. 

If you found any Error. In some of the command then please let me know, or you can ask for Pull Request. It would be helpful. Thanks

Bot Invite Link: [Invite Link](https://discord.com/api/oauth2/authorize?client_id=800780974274248764&permissions=8&scope=bot)

---

## Bot Setup

#### - **Bot Prefix**

Default prefix is `$` or `@Parrot#9209` (Mention) but if you found is difficult to type you can change the bot prefix. But you can't change the `@Parrot#9209` as prefix. Also, prefix is case **sensitive** and length of prefix must be less than 6 character
> ```
[p]serverconfig botprefix YOUR_PREFIX_HERE 
```

<br>

#### - **Moderator Logging**

You must be aware what command is being used on whom by whom, especially Mod commands. Parrot can log every action whenever the mod command like `kick` `ban` is used. Pass `None` if you want to remove
> ```
[p]serverconfig actionlog [CHANNEL]
```

<br>

#### - **Mute Role**

As every moderation bot there is one thing, setting up `MUTE_ROLE`. Parrot can do it without you setup. As per Parrot Bot defination Mute Role should not have `send_messages` permissions. But you can change that too. Pass `None` if you want to remove
> ```
[p]serverconfig muterole ROLE
```

<br>

#### - **Moderator Role**

Sometimes giving permissions kick ban can be dangerous. If people are not trust worthy. Mod role are like you can use the mod command even if you aren't having real server permission. Pass `None` if you want to remove
> ```
[p]serverconfig modrole ROLE
```

---
## Global-Chat Setup

This thing is insane. Feature inspired from World Chat bot. Configuring the `#global-chat` is kinda easy too. Pass `None` if you want to remove

#### - **Making the channel**

You yourself don't need to do that to be honest. Once you trigger the command bot will create a channel (and webhook of that channel) on the top of the server. Once the channel is created, you can change it's or and whatever you want to do with that.
> ```
[p]serverconfig gchat
```

<br>

#### - **Ignore-Role in #global-chat**

Again there are anonying people who just spam. People with ignore role can't chat in `#global-chat`. Pass `None` if you want to remove. [I didn't test this feature yet, if incase the this thing is not working then let me know]
> ```
[p]serverconfig gsetup ignorerole ROLE
```

---

## Telephone Setup
Another insane feature, I am still improving this. Inspired by Yggdrasil Bot. You can talk to other server people without joining it.

#### - **Channel Setup**

Like in real life your telephone is fixed at a point. Not like Cell Phone. So similarly all kind of calls are made in that channel.
> ```
[p]telsetup channel [CHANNEL]
```

<br>

#### - **Member Ping**

This is usual that how we come to know someone is calling. Pass `None` if you want to remove. [I didn't test this feature yet, if incase the this thing is not working then let me know]
> ```
[p]telsetup memberping MEMBER
```

<br>

#### - **Ping Role**

What if the member is offline? You can ping the Role if you want. Pass `None` if you want to remove. [I guess `@everyone` would work too]
> ```
[p]telsetup pingrole ROLE
```

<br>

#### - **Block**

Some server are really anonying. Like the continously make phone calls. Just to disturb by pinging. You can block those cringe.
> ```
[p]telsetup block SERVER
```

<br>

#### - **Unblock**

Suppose the cringe server is now DMing your to forgive them. LOL. And they said not doing those thing again.
> ```
[p]telsetup unblock SERVER
```

---

## Ticket Setup

If you are unaware then let me know Parrot Support ticket system very nicely. Setting up is easy too. Uff

#### - **Reaction**

Ticket can be created on reaction basis. This can be setup easily by:
> ```
[p]ticketconfig auto [CHANNEL] [MESSAGE]

#### - **Category**

This is optional. By default all the ticket channel are created on the top of the server. If you setup the category then all new category will be created in that category.
> ```
[p]ticketconfig setcategory CATEGORY
```

<br>

#### - **Add Admin**

There should be Ticket Moderator. Isn't it? This command gives all users with a specific role access to the `admin-level` commands of *Parrot Ticket Bot ONLY*
> ```
[p]ticketconfig addadminrole ROLE
```

<br>

#### - **Remove Admin**

When you find that ticket mod you choose don't deserve to be mod. Isn't it? This command removes all users with a specific role access to the `admin-level` commands of *Parrot Ticket Bot ONLY*
> ```
[p]ticketconfig deladminrole ROLE
```

<br>

#### - **Access to Ticket Channel**

This role is important if you want your mods to get the access to that channel
> ```
[p]ticketconfig addaccess ROLE
```

<br>

#### - **Remove Access from Ticket Channel**

When you find the mods aren't really use full when channel is created. So you decided to remove them.
> ```
[p]ticketconfig delaccess ROLE
```

<br>

#### - **Logging Setup**

Logging is somewhere important if you run a dedicated server and want to know every single action.
> ```
[p]ticketconfig setlog [CHANNEL]
```

<br>

#### - **Ping Role**

Sometimes its needed to be get pinged when the new ticket is created.
> ```
[p]ticketconfig addpingedrole ROLE
```

<br>

#### - **Remove Ping Role**

Now, if you want to remove the role if you don't want that role to be get pinged.
> ```
[p]ticketconfig delpingedrole ROLE
```

<br>
---
```
NOTE: 

1. Member having `admin-level` can not have access to the ticket channel unless they have `access` role. `admin-level` can change the `access` and `pinged-role` setting ONLY.

2. Bot will moderate indiscriminately. Means it hardly care about the role level. So it is adviced to place the bot role below the staff role or moderator role.
```

```
TODO:

1. To make tag system
2. To make help commands more good
3. To make AutoModeration
4. To make more Todo list. LOL
```
---
# Commands

## Moderation

A simple moderator's tool for managing the server.

----
| Commands | Descriptions | Aliases|
| -- | -- | -- |
| role | Role Management of the server. | None | 
| ban | To ban a member from guild. | hackban | 
| massban | To Mass ban list of members, from the guild | None | 
| softban | To Ban a member from a guild then immediately unban | softkill | 
| block | Blocks a user from replying message in that channel. | None | 
| clone | To clone the channel or to nukes the channel (clones and delete). | nuke | 
| kick | To kick a member from guild. | None | 
| masskick | To kick a member from guild. | None | 
| lock | To lock the channel | None | 
| unlock | To unlock the channel (Text channel) | None | 
| mute | To restrict a member to sending message in the Server | None |
| unmute | To allow a member to sending message in the Text Channels, if muted. | None | 
| clean | To delete bulk message. | purge | 
| purgeuser | To delete bulk message, of a specified user. | None | 
| purgebots | To delete bulk message, of bots | None |
| purgeregex | To delete bulk message, matching the regex | None | 
| slowmode | To set slowmode in the specified channel | None |
| unban | To Unban a member from a guild | None | 
| unblock | Unblocks a user from the text channel | None |
| mod | Why to learn the commands. This is all in one mod command. | None |

__**Note: Bot will ban indiscriminately, means member of lower rank can moderate, member of higher rank. So it is advice to place the bot role just below the mod role/staff role**__

## Utilities

Basic commands for the bots.


----
|Command  | Description  | Aliases|
|--|--|--|
| ping | Get the latency of bot. | None | 
| avatar | Get the avatar of the user. Make sure you don't misuse. | av | 
| owner | Get the freaking bot owner name. | None | 
| guildicon | Get the freaking server icon | guildavatar, serverlogo, servericon | 
| serverinfo | Get the basic stats about the server | guildinfo, si, gi | 
| stats | Get the bot stats | None | 
| userinfo | Get the basic stats about the user | memberinfo, ui, mi | 
| invite | Get the invite of the bot! Thanks for seeing this command | None |

## Fun
Parrot gives you huge amount of fun commands, so that you won't get bored

---
|Command  | Description  | Aliases|
| -- | -- | -- |
| ttt | None | None | 
| 8ball | 8ball Magic, nothing to say much | None | 
| choose | Confuse something with your decision? Let Parrot choose from your choice. NOTE: The `Options` should be seperated by commas `,`. | None | 
| color | To get colour information using the hexadecimal codes. | colours, colour | 
| decode | Decode the code to text from Base64 encryption | None | 
| encode | Encode the text to Base64 Encryption and in Binary | None | 
| fact | Return a random Fact. It's useless command, I know NOTE: Available animals - Dog, Cat, Panda, Fox, Bird, Koala | None | 
| gay | Image Generator. Gay Pride. | None | 
| glass | Provide a glass filter on your profile picture, try it! | None | 
| horny | Image generator, Horny card generator. | None | 
| roast | Insult your enemy, Ugh! | insult | 
| itssostupid | :\ I don't know what is this, I think a meme generator. | its-so-stupid | 
| jail | Image generator. Makes you behind the bars. Haha | None | 
| lolice | This command is not made by me. : \ | None | 
| meme | Random meme generator. | None | 
| fakepeople | Fake Identity generator. | None | 
| simpcard | Good for those, who are hell simp! LOL | None | 
| slap | Slap virtually with is shit command. | hit | 
| translate | This command is useful, to be honest, if and only if you use correctly, else it gives error. Not my fault. | trans | 
| trigger | User Triggered! | triggered | 
| urbandictionary | LOL. This command is insane. | def, urban | 
| wasted | Overlay 'WASTED' on your profile picture, just like GTA:SA | None | 
| ytcomment | Makes a comment in YT. Best ways to fool your fool friends. :') | youtube-comment | 
| dare | I dared you to use this command. | None | 
| truth | Truth: Who is your crush? | None | 
| aki | Answer the questions and let the bot guess your character! | None |
| dial | To make server calls | None |

## Ticket
A simple ticket service, trust me it's better than YAG. LOL!

---
|Command  | Description  | Aliases|
|--|--|--|
| new | This creates a new ticket. Add any words after the command if you'd like to send a message when we initially create your ticket. | None | 
| close | Use this to close a ticket. This command only works in ticket channels. | None | 
| save | Use this to save the transcript of a ticket. This command only works in ticket channels. | None | 
| ticketconfig | To config the Ticket Parrot Bot in the server | None |

## Miscellaneous
Those commands which can't be listed

---
|Command  | Description  | Aliases|
|--| -- | --| 
| bigemoji | To view the emoji in bigger form | emote | 
| calculator | This is basic calculator with all the expression supported. Syntax is similar to python math module. | calc, cal | 
| maths | Another calculator but quite advance one NOTE: Available operation - Simplify, Factor, Derive, Integrate, Zeroes, Tangent, Area, Cos, Sin, Tan, Arccos, Arcsin, Arctan, Abs, Log For more detailed use, visit: `https://github.com/aunyks/newton-api/blob/master/README.md` | None | 
| news | This command will fetch the latest news from all over the world. | None | 
| search | Simple google search Engine. | googlesearch, google, s | 
| snipe | "Snipes" someone's message that's deleted | None | 
| truthtable | A simple command to generate Truth Table of given data. Make sure you use proper syntax. Syntax: `Truthtable -var *variable1*, *variable2*, *variable3* ... -con *condition1*, *condition2*, *condition3* ...` (Example: `tt -var a, b -con a and b, a or b`) | trutht, tt, ttable | 
| weather | Weather API, for current weather forecast, supports almost every city. | w | 
| wikipedia | Web articles from Wikipedia. | wiki | 
| youtube | Search for videos on YouTube. | yt | 
| embed | A nice command to make custom embeds, from a `Python Dictionary` or form `JSON`. Provided it is in the format that Discord expects it to be in. You can find the documentation on `https://discord.com/developers/docs/resources/channel#embed-object`. | None | 
| snowflakeid | To get the ID of discord models | None | 
| snowflaketime | Get the time difference in seconds, between two discord SnowFlakes | None |	

<br>

There are NSFW, and Meme Generator commands too :)

__You can get the more info by doing `[p]help <command_name>`__

