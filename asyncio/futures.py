"""A Future class similar to the one in PEP 3148."""

__all__ = ['CancelledError', 'TimeoutError',
           'InvalidStateError',
           'Future', 'wrap_future',
]

import concurrent.futures.cooperative
import concurrent.futures.multithreaded
import concurrent.futures.exceptions
import logging

from . import events

# TODO: Do we really want to depend on concurrent.futures internals?
Error = concurrent.futures.exceptions.Error
CancelledError = concurrent.futures.exceptions.CancelledError
TimeoutError = concurrent.futures.exceptions.TimeoutError
InvalidStateError = concurrent.futures.exceptions.InvalidStateError

STACK_DEBUG = logging.DEBUG - 1  # heavy-duty debugging


def loop_as_executor(loop):
    return loop.call_soon


def loop_as_executor_threadsafe(loop):
    return loop.call_soon_threadsafe


class Future(concurrent.futures.cooperative.Future):
    _blocking = False  # proper use of future (yield vs yield from)

    def __init__(self, *, loop=None):
        self._loop = loop or events.get_event_loop()
        super().__init__(clb_executor=loop_as_executor(self._loop))

    def __iter__(self):
        if not self.done():
            self._blocking = True
            yield self  # This tells Task to wait for completion.
        assert self.done(), "yield from wasn't used with future"
        return self.result()  # May raise too.

    @classmethod
    def _new(cls, other=None, *, clb_executor=None):
        loop = other._loop if other else None
        return cls(loop=loop)

    @classmethod
    def convert(cls, future):
        """Enables compatibility with multithreaded futures by wrapping."""
        if isinstance(future, cls):
            return future
        if isinstance(future, concurrent.futures.multithreaded.Future):
            return wrap_future(future)
        raise TypeError("{} is not compatible with {}"
        .format(_typename(cls), _typename(type(future))))


def _typename(cls):
    return cls.__module__ + '.' + cls.__name__


def wrap_future(fut, *, loop=None):
    """Wrap concurrent.futures.Future object."""
    if isinstance(fut, Future):
        return fut
    assert isinstance(fut, concurrent.futures.multithreaded.Future), \
        'concurrent.futures.threaded.Future is expected, got {!r}'.format(fut)
    if loop is None:
        loop = events.get_event_loop()
    new_future = Future(loop=loop)

    def _check_cancel_other(f):
        if f.cancelled():
            fut.cancel()

    new_future.add_done_callback(_check_cancel_other)
    fut.add_done_callback(
        lambda future: loop.call_soon_threadsafe(
            new_future.set_from, fut))
    return new_future
