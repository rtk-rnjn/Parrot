from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Literal, TypedDict, Unpack

import discord
import pymongo
from bson import ObjectId
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import ConnectionFailure
from pymongo.results import DeleteResult, InsertOneResult

if TYPE_CHECKING:
    from core import Bot


_log = logging.getLogger(__name__)

__all__ = ("AsyncTimerDispatcher", "TimerData")

VALID_EVENT_NAMES = Literal["reminder", "mute", "todo_due", "giveaway", "automod_unban", "automod_role", "automod_slowmode"]


class TimerData[T: Mapping[str, object]](TypedDict):
    """Schema for a timer document stored in MongoDB."""

    _id: ObjectId
    expires_at: datetime
    created_at: datetime
    event_name: VALID_EVENT_NAMES
    metadata: T


class AsyncTimerDispatcher:
    """Manage persistent timers backed by MongoDB.

    The manager maintains one long-running asyncio task that watches the
    earliest timer in MongoDB. Rather than polling the database at a fixed
    interval, the task sleeps until the current timer expires.
    """

    def __init__(self, bot: Bot, /) -> None:
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
        return await self.timers_collection.find_one({}, sort=[("expires_at", pymongo.ASCENDING)])

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

    async def _start(self) -> None:
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
            _log.exception("Timer dispatcher lost its connection; restarting")
            await self.restart()

        except asyncio.CancelledError:
            # Task cancellation is a control-flow mechanism in asyncio, not
            # an error that should trigger automatic dispatcher recreation.
            _log.debug("Timer dispatcher task cancelled")
            raise

        except Exception:
            _log.exception("Timer dispatcher stopped unexpectedly", exc_info=True)
            raise

    async def start(self) -> None:
        """Start the dispatcher task if it is not already running."""
        if self.timer_task is None or self.timer_task.done():
            self.timer_task = self.bot.loop.create_task(self._start(), name=f"{self.__class__.__name__}: start")
            _log.info("Timer dispatcher started")

    async def __call_timer(self, **data: Unpack[TimerData]) -> None:
        """Atomically consume an expired timer and dispatch its completion event.

        The timer is deleted before the application event is dispatched.
        This prevents the same persistent timer from being processed again if
        the dispatcher subsequently restarts.

        The delete result is checked because another dispatcher/process may
        have already consumed the same timer. Only the coroutine that
        successfully deletes the document is allowed to dispatch the event.
        """
        deleted: DeleteResult = await self.timers_collection.delete_one({"_id": data.get("_id")})

        if deleted.deleted_count == 0:
            _log.debug("Timer %s was already consumed; skipping dispatch", data.get("_id"))
            return

        _log.info("Dispatching completed %s timer %s", data["event_name"], data.get("_id"))
        self.bot.dispatch(f"{data['event_name']}_timer_complete".lower(), metadata=data["metadata"])

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
        post: TimerData = {
            "_id": ObjectId(),
            "expires_at": expires_at,
            "created_at": discord.utils.utcnow(),
            "event_name": event_name,
            "metadata": metadata,
        }

        insert_data = await self.timers_collection.insert_one(post)
        _log.debug("Created %s timer %s for %s", event_name, post["_id"], expires_at.isoformat())

        # Wake a dispatcher currently blocked in Event.wait(). The Event
        # remains set while timers exist; it is not consumed by wait().
        self._have_data.set()

        if self._current_timer and self._current_timer["expires_at"] > expires_at:
            self._current_timer = post
            _log.debug("New timer %s expires before current timer; restarting dispatcher", post["_id"])

            await self.restart()

        return insert_data

    async def get[T: Mapping[str, object]](self, **filters: Unpack[TimerData[T]]) -> TimerData[T] | None:
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
        filters = {
            "event_name": event_name,
            **{f"metadata.{k}": v for k, v in metadata_filter.items()},
        }
        if multiple:
            _log.debug("Deleting all %s timers matching %s", event_name, metadata_filter)
            data = await self.timers_collection.delete_many(filters)
        else:
            _log.debug("Deleting one %s timer matching %s", event_name, metadata_filter)
            data = await self.timers_collection.delete_one(filters)

        if data.deleted_count == 0:
            return data

        await self.restart()

        return data

    async def delete_by_id(self, timer_id: ObjectId, /) -> bool:
        """Delete one timer by its MongoDB id. Returns ``False`` if it no longer exists."""
        _log.debug("Deleting timer %s by id", timer_id)
        result = await self.timers_collection.delete_one({"_id": timer_id})
        if result.deleted_count == 0:
            return False

        await self.restart()
        return True

    async def update(self, timer_id: ObjectId, /, *, expires_at: datetime, metadata: Mapping[str, object]) -> bool:
        """Change a timer's expiry and metadata. Returns ``False`` if it already fired."""
        _log.debug("Updating timer %s to expire at %s with metadata %s", timer_id, expires_at.isoformat(), metadata)
        result = await self.timers_collection.update_one(
            {"_id": timer_id},
            {"$set": {"expires_at": expires_at, "metadata": dict(metadata)}},
        )
        if result.matched_count == 0:
            return False

        await self.restart()
        return True

    async def restart(self) -> None:
        """Cancel the current dispatcher and start it again.

        This forces the dispatcher to discard its cached scheduling state and
        select the earliest timer currently present in MongoDB.

        Restarting is useful after external changes to the timers collection
        that the manager itself did not observe.
        """
        self._current_timer = None

        if self.timer_task is not None:
            _log.debug("Restarting timer dispatcher")
            self.timer_task.cancel()
            self.timer_task = self.bot.loop.create_task(self._start(), name=f"{self.__class__.__name__}: start")

    async def search[T: Mapping[str, object]](self, *, event_name: VALID_EVENT_NAMES, metadata_filter: T) -> list[TimerData[T]]:
        """Return all timers matching the supplied fields."""
        filters = {
            "event_name": event_name,
            **{f"metadata.{k}": v for k, v in metadata_filter.items()},
        }
        cursor = self.timers_collection.find(filters, sort=[("expires_at", pymongo.ASCENDING)])
        return await cursor.to_list(length=None)
