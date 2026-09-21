from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Literal, NotRequired, TypedDict, Unpack

import discord
import pymongo
from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import ConnectionFailure
from pymongo.results import DeleteResult, InsertOneResult

if TYPE_CHECKING:
    from core import Parrot


__all__ = ("AsyncTimerDispatcher", "TimerData")

VALID_EVENT_NAMES = Literal[
    "reminder",
    "mute",
    "todo_due",
    "giveaway",
]


class TimerData(TypedDict):
    """Schema for a timer document stored in MongoDB.

    ``_id`` is optional because a timer does not have a MongoDB-generated ID
    until it has been inserted into the collection. Documents returned by
    MongoDB will normally contain this field.

    Attributes
    ----------
    _id:
        MongoDB's unique identifier for the timer.
    expires_at:
        UTC timestamp at which the timer should be dispatched.
    created_at:
        UTC timestamp at which the timer was created.
    event_name:
        Base name of the event to dispatch when the timer expires.
    metadata:
        Arbitrary application-specific data passed to the dispatched event.
    """

    _id: NotRequired[ObjectId]
    expires_at: datetime
    created_at: datetime
    event_name: VALID_EVENT_NAMES
    metadata: Mapping[str, object]


class AsyncTimerDispatcher:
    """Manage persistent timers backed by MongoDB.

    The manager maintains one long-running asyncio task that watches the
    earliest timer in MongoDB. Rather than polling the database at a fixed
    interval, the task sleeps until the current timer expires.
    """

    def __init__(self, bot: Parrot, /) -> None:
        """Initialize the timer manager using the bot's MongoDB and event loop."""

        self.timers_collection: AsyncCollection[TimerData] = bot.database.mongo_db["timers"]

        # Event used to put the dispatcher to sleep while there are no timers.
        # Unlike an asyncio.Queue, the event does not carry the timer itself;
        # the database remains the source of truth.
        self._have_data = asyncio.Event()

        # This is only a scheduling hint/cache. MongoDB remains authoritative,
        # so the value can become stale if timers are modified elsewhere.
        self._current_timer: TimerData | None = None

        # The dispatcher is intentionally kept as a Task reference so it can
        # be cancelled when a newly-created/deleted timer changes which
        # database record should be processed next.
        self.timer_task: asyncio.Task[None] | None = None

        # The bot's event loop is used to create the dispatcher task. This ensures
        # that cancellation and recreation happen in the same asyncio execution
        # context as the bot.
        self.bot = bot

    async def __get_active_timer(self) -> TimerData | None:
        """Return the timer that expires first."""
        return await self.timers_collection.find_one(
            {},
            sort=[("expires_at", pymongo.ASCENDING)],
        )

    async def __wait_for_active_timer(self) -> TimerData | None:
        """Wait until MongoDB contains a timer and return the earliest one.

        The dispatcher does not continuously query MongoDB when there are no
        timers. Instead, it clears the Event and waits for ``create_timer()``
        to set it again. This avoids a polling loop consuming an event-loop
        iteration every few seconds while the system is idle.

        The database is queried again after the Event wakes because the Event
        only signals that *some* timer may exist; it does not contain the
        timer itself.
        """
        timer = await self.__get_active_timer()

        if timer:
            self._have_data.set()
            return timer

        self._have_data.clear()
        self._current_timer = None

        # Event.wait() suspends this coroutine rather than blocking the
        # asyncio event loop. Other bot tasks continue running while the
        # dispatcher waits for create_timer() to signal new data.
        await self._have_data.wait()

        return await self.__get_active_timer()

    async def start(self) -> None:
        """Run the timer dispatcher until the bot shuts down.

        The dispatcher always works with the earliest timer in MongoDB.
        Once that timer is known, the coroutine sleeps until its expiration
        instead of repeatedly polling the database.

        If a database/network connection is interrupted, the current task is
        cancelled and replaced with a fresh dispatcher task. Cancellation is
        deliberately re-raised for ``asyncio.CancelledError`` so callers can
        reliably stop the dispatcher rather than accidentally treating normal
        task cancellation as a recoverable connection failure.
        """
        try:
            while not self.bot.is_closed():
                timer = self._current_timer = await self.__wait_for_active_timer()

                if timer is None:
                    error_message = (
                        "Dispatcher woke up but no timer was found in MongoDB. "
                        "This should never happen because the Event was set to signal "
                        "the presence of a timer. The dispatcher will continue waiting for new timers."
                    )
                    raise RuntimeError(error_message)

                await self.__dispatch_timer(**timer)

                # Now we need to ``asyncio.sleep(0)`` to yield control to the event loop so that other tasks
                # can run before we check for the next timer. This prevents a tight loop that could starve other tasks.
                await asyncio.sleep(0)

        except OSError, discord.ConnectionClosed, ConnectionFailure:
            await self.restart()

        except asyncio.CancelledError:
            # Task cancellation is a control-flow mechanism in asyncio, not
            # an error that should trigger automatic dispatcher recreation.
            raise

    async def __call_timer(self, **data: Unpack[TimerData]) -> None:
        """Atomically consume an expired timer and dispatch its completion event.

        The timer is deleted before the application event is dispatched.
        This prevents the same persistent timer from being processed again if
        the dispatcher subsequently restarts.

        The delete result is checked because another dispatcher/process may
        have already consumed the same timer. Only the coroutine that
        successfully deletes the document is allowed to dispatch the event.
        """
        deleted: DeleteResult = await self.timers_collection.delete_one(
            {"_id": data.get("_id")},
        )

        if deleted.deleted_count == 0:
            return

        self.bot.dispatch(
            f"{data['event_name']}_timer_complete".lower(),
            metadata=data["metadata"],
        )

    async def __dispatch_timer(self, **data: Unpack[TimerData]) -> None:
        """Dispatch a single timer without involving the main dispatcher loop."""

        await discord.utils.sleep_until(data["expires_at"])

        await self.__call_timer(**data)

    async def create_timer(
        self,
        *,
        event_name: VALID_EVENT_NAMES,
        expires_at: datetime,
        metadata: Mapping[str, object],
    ) -> InsertOneResult:
        """Persist a timer and notify the dispatcher that timer data exists.

        If the new timer expires before the timer currently being awaited,
        the existing dispatcher task is cancelled and restarted. This is
        necessary because ``asyncio.sleep()`` cannot automatically notice
        that another coroutine has inserted an earlier timer into MongoDB.
        """
        # MongoDB receives a snapshot of the timer. Its generated ``_id`` is
        # available on the document when it is read back from the collection.
        post: TimerData = {
            "expires_at": expires_at,
            "created_at": discord.utils.utcnow(),
            "event_name": event_name,
            "metadata": metadata,
        }

        insert_data = await self.timers_collection.insert_one(post)

        post["_id"] = insert_data.inserted_id

        # Wake a dispatcher currently blocked in Event.wait(). The Event
        # remains set while timers exist; it is not consumed by wait().
        self._have_data.set()

        if self._current_timer and self._current_timer["expires_at"] > expires_at:
            self._current_timer = post

            await self.restart()

        return insert_data

    async def get(self, **filters: Unpack[TimerData]) -> TimerData | None:
        """Return the first timer matching the supplied fields."""
        return await self.timers_collection.find_one(filters)

    async def delete(
        self,
        *,
        event_name: VALID_EVENT_NAMES,
        metadata_filter: Mapping[str, object],
        multiple: bool = False,
    ) -> DeleteResult:
        """Delete a matching timer and restart the dispatcher if necessary."""
        filters = {"event_name": event_name, **{f"metadata.{k}": v for k, v in metadata_filter.items()}}
        if multiple:
            data = await self.timers_collection.delete_many(filters)
        else:
            data = await self.timers_collection.delete_one(filters)

        if data.deleted_count == 0:
            return data

        await self.restart()

        return data

    async def restart(self) -> None:
        """Cancel the current dispatcher and start it again.

        This forces the dispatcher to discard its cached scheduling state and
        select the earliest timer currently present in MongoDB.

        Restarting is useful after external changes to the timers collection
        that the manager itself did not observe.
        """
        self._current_timer = None

        if self.timer_task is not None:
            self.timer_task.cancel()
            self.timer_task = self.bot.loop.create_task(self.start())

    async def search(self, *, event_name: VALID_EVENT_NAMES, metadata_filter: Mapping[str, object]) -> list[TimerData]:
        """Return all timers matching the supplied fields."""
        filters = {"event_name": event_name, **{f"metadata.{k}": v for k, v in metadata_filter.items()}}
        cursor = self.timers_collection.find(filters, sort=[("expires_at", pymongo.ASCENDING)])
        return await cursor.to_list(length=None)
