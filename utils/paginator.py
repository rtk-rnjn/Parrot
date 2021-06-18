# Author: https://github.com/davidetacchini

import asyncio
from typing import List, Union, Optional
from contextlib import suppress

import discord


class Paginator:

    __slots__ = (
        "pages",
        "timeout",
        "compact",
        "has_input",
        "has_lock",
        "_ctx",
        "_bot",
        "_loop",
        "_message",
        "_current",
        "_previous",
        "_end",
        "_reactions",
        "__tasks",
        "__is_running",
        "__is_locked",
        "__mutex",
    )

    def __init__(self,
                 *,
                 pages: Optional[Union[List[discord.Embed],
                                       discord.Embed]] = None,
                 compact: bool = False,
                 timeout: float = 90.0,
                 has_input: bool = True,
                 has_lock: bool = False):
        self.pages = pages
        self.compact = compact
        self.timeout = timeout
        self.has_input = has_input
        self.has_lock = has_lock

        self._ctx = None
        self._bot = None
        self._loop = None
        self._message = None

        self._current = 0
        self._previous = 0
        self._end = 0
        self._reactions = {
            "⏮": 0.0,
            "◀": -1,
            "⏹️": "stop",
            "▶": +1,
            "⏭": None,
        }

        self.__tasks = []
        self.__is_running = True
        self.__is_locked = True
        self.__mutex = asyncio.Lock()

        if self.has_input is True:
            self._reactions["🔢"] = "input"

        if self.has_lock is True:
            self._reactions["🔒"] = "lock"

        if self.pages is not None:
            if len(self.pages) == 2:
                self.compact = True
                self.has_input = False

        if self.compact is True:
            keys = ("⏮", "⏭")
            for key in keys:
                del self._reactions[key]

    def go_to_page(self, number):
        if number > int(self._end):
            page = int(self._end)
        else:
            page = number - 1
        self._current = page

    async def get_input(self):
        to_delete = []
        message = await self._ctx.send("What page do you want to go to?")
        to_delete.append(message)

        def check(m):
            if self.__is_locked:
                if m.author.id != self._ctx.author.id:
                    return False
            if m.channel.id != self._ctx.channel.id:
                return False
            if not m.content.isdigit():
                return False
            return True

        try:
            message = await self._bot.wait_for("message",
                                               check=check,
                                               timeout=30.0)
        except asyncio.TimeoutError:
            to_delete.append(
                await self._ctx.send("You took too long to enter a number."))
            await asyncio.sleep(5)
        else:
            to_delete.append(message)
            self.go_to_page(int(message.content))

        with suppress(Exception):
            await self._ctx.channel.delete_messages(to_delete)

    async def lock_or_unlock(self, user_id):
        # only the author can (un)lock the session
        if self._ctx.author.id != user_id:
            return
        self.__is_locked = not self.__is_locked
        if self.__is_locked:
            await self._ctx.send(
                "Session locked. Only you can interact with it.")
        else:
            await self._ctx.send(
                "Session unlocked. Everyone can interact with it.")

    async def controller(self, reaction, user_id):
        if self.__mutex.locked():
            return
        async with self.__mutex:
            if reaction == "stop":
                await self.stop()
            elif reaction == "input":
                await self.get_input()
            elif reaction == "lock":
                await self.lock_or_unlock(user_id)
            elif isinstance(reaction, int):
                self._current += reaction
                if self._current < 0 or self._current > self._end:
                    self._current -= reaction
            else:
                self._current = int(reaction)

    def check(self, payload):
        if self.__is_locked:
            if payload.user_id != self._ctx.author.id:
                return False
        if payload.message_id != self._message.id:
            return False
        return str(payload.emoji) in self._reactions

    async def add_reactions(self):
        for reaction in self._reactions:
            with suppress(discord.Forbidden, discord.HTTPException):
                await self._message.add_reaction(reaction)

    async def paginator(self):
        with suppress(discord.HTTPException, discord.Forbidden, IndexError):
            self._message = await self._ctx.send(embed=self.pages[0])

        if len(self.pages) > 1:
            self.__tasks.append(self._loop.create_task(self.add_reactions()))

        while self.__is_running:
            with suppress(Exception):
                tasks = [
                    asyncio.ensure_future(
                        self._bot.wait_for("raw_reaction_add",
                                           check=self.check)),
                    asyncio.ensure_future(
                        self._bot.wait_for("raw_reaction_remove",
                                           check=self.check)),
                ]

                done, pending = await asyncio.wait(
                    tasks,
                    timeout=self.timeout,
                    return_when=asyncio.FIRST_COMPLETED)

                for task in pending:
                    task.cancel()

                if len(done) == 0:
                    # clear the reactions once the timeout has elapsed
                    return await self.stop(timed_out=True)

                payload = done.pop().result()
                reaction = self._reactions.get(str(payload.emoji))

                self._previous = self._current
                await self.controller(reaction, payload.user_id)

                if self._previous == self._current:
                    continue

                with suppress(Exception):
                    await self._message.edit(embed=self.pages[self._current])

    async def stop(self, *, timed_out=False):
        with suppress(discord.Forbidden, discord.HTTPException):
            if timed_out:
                await self._message.clear_reactions()
            else:
                await self._message.delete()

        with suppress(Exception):
            self.__is_running = False
            for task in self.__tasks:
                task.cancel()
            self.__tasks.clear()

    async def start(self, ctx):

        self._ctx = ctx
        self._bot = ctx.bot
        self._loop = ctx.bot.loop

        if isinstance(self.pages, discord.Embed):
            return await self._ctx.send(embed=self.pages)

        if not isinstance(self.pages, (list, discord.Embed)):
            raise TypeError("Can't paginate an instance of <class '%s'>." %
                            self.pages.__class__.__name__)

        if len(self.pages) == 0:
            raise RuntimeError("Can't paginate an empty list.")

        self._end = float(len(self.pages) - 1)
        if self.compact is False:
            self._reactions["⏭"] = self._end
        self.__tasks.append(self._loop.create_task(self.paginator()))
