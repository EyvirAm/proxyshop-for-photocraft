"""
* Utils: Asynchronic

Run asyncio coroutines from synchronous Qt code.
"""
from __future__ import annotations
import asyncio
from asyncio import Future, InvalidStateError, get_running_loop, run

EventLoop = getattr(
    asyncio,
    "EventLoop",
    getattr(asyncio, "ProactorEventLoop", asyncio.SelectorEventLoop),
)
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from logging import getLogger
from threading import Thread
from typing import Any

_logger = getLogger(__name__)

_thread_pool = ThreadPoolExecutor(max_workers=4)


def async_to_sync[T](awaitable: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine to completion from synchronous code."""
    return _thread_pool.submit(run, awaitable, loop_factory=EventLoop).result()


def run_in_thread[T](coro: Coroutine[Any, Any, T]) -> Thread:
    """Run in thread."""
    def target():
        # Using asyncio.run without a factory starts another Qt loop, since
        # Qt sets the global loop policy to it's own implementation.
        # Starting another Qt loop fails, because the loop also tries to
        # exec another Qt application. As a workaround, we have to specifically
        # create an instance of the default non-Qt event loop.
        """Run the task in the target event loop."""
        run(coro, loop_factory=EventLoop)

    thread = Thread(target=target)
    thread.start()
    return thread


async def run_in_thread_async[T](coro: Coroutine[Any, Any, T]) -> None:
    """Run in thread async."""
    def target():
        # Using asyncio.run without a factory starts another Qt loop, since
        # Qt sets the global loop policy to it's own implementation.
        # Starting another Qt loop fails, because the loop also tries to
        # exec another Qt application. As a workaround, we have to specifically
        # create an instance of the default non-Qt event loop.
        """Run the task in the target event loop."""
        run(coro, loop_factory=EventLoop)

    get_running_loop().run_in_executor(_thread_pool, target)


def try_threadsafe_set_result[T](task: Future[T], result: T) -> None:
    """Try threadsafe set result."""
    def set_result_if_not_done():
        """Set the result if not done."""
        if not task.done():
            try:
                task.set_result(result)
            except InvalidStateError as err:
                _logger.warning("Failed to set future result", exc_info=err)

    task.get_loop().call_soon_threadsafe(set_result_if_not_done)
