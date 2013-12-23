"""A Future class similar to the one in PEP 3148."""

__all__ = ['CancelledError', 'TimeoutError',
           'InvalidStateError',
           'Future', 'wrap_future',
           ]

import concurrent.futures._base
import logging

from . import events

# TODO: Do we really want to depend on concurrent.futures internals?
Error = concurrent.futures._base.Error
CancelledError = concurrent.futures.CancelledError
TimeoutError = concurrent.futures.TimeoutError
InvalidStateError = concurrent.futures.InvalidStateError

STACK_DEBUG = logging.DEBUG - 1  # heavy-duty debugging


'''
class Future:
    """This class is *almost* compatible with concurrent.futures.Future.

    Differences:

    - result() and exception() do not take a timeout argument and
      raise an exception when the future isn't done yet.

    - Callbacks registered with add_done_callback() are always called
      via the event loop's call_soon_threadsafe().

    - This class is not compatible with the wait() and as_completed()
      methods in the concurrent.futures package.

    (In Python 3.4 or later we may be able to unify the implementations.)
    """

    # Class variables serving as defaults for instance variables.
    _state = _PENDING
    _result = None
    _exception = None
    _loop = None

    _blocking = False  # proper use of future (yield vs yield from)

    _tb_logger = None

    def __init__(self, *, loop=None):
        """Initialize the future.

        The optional event_loop argument allows to explicitly set the event
        loop object used by the future. If it's not provided, the future uses
        the default event loop.
        """
        if loop is None:
            self._loop = events.get_event_loop()
        else:
            self._loop = loop
        self._callbacks = []

    def __repr__(self):
        res = self.__class__.__name__
        if self._state == _FINISHED:
            if self._exception is not None:
                res += '<exception={!r}>'.format(self._exception)
            else:
                res += '<result={!r}>'.format(self._result)
        elif self._callbacks:
            size = len(self._callbacks)
            if size > 2:
                res += '<{}, [{}, <{} more>, {}]>'.format(
                    self._state, self._callbacks[0],
                    size-2, self._callbacks[-1])
            else:
                res += '<{}, {}>'.format(self._state, self._callbacks)
        else:
            res += '<{}>'.format(self._state)
        return res

    def cancel(self):
        """Cancel the future and schedule callbacks.

        If the future is already done or cancelled, return False.  Otherwise,
        change the future's state to cancelled, schedule the callbacks and
        return True.
        """
        if self._state != _PENDING:
            return False
        self._state = _CANCELLED
        self._schedule_callbacks()
        return True

    def _schedule_callbacks(self):
        """Internal: Ask the event loop to call all callbacks.

        The callbacks are scheduled to be called as soon as possible. Also
        clears the callback list.
        """
        callbacks = self._callbacks[:]
        if not callbacks:
            return

        self._callbacks[:] = []
        for callback in callbacks:
            self._loop.call_soon(callback, self)

    def cancelled(self):
        """Return True if the future was cancelled."""
        return self._state == _CANCELLED

    # Don't implement running(); see http://bugs.python.org/issue18699

    def done(self):
        """Return True if the future is done.

        Done means either that a result / exception are available, or that the
        future was cancelled.
        """
        return self._state != _PENDING

    def result(self):
        """Return the result this future represents.

        If the future has been cancelled, raises CancelledError.  If the
        future's result isn't yet available, raises InvalidStateError.  If
        the future is done and has an exception set, this exception is raised.
        """
        if self._state == _CANCELLED:
            raise CancelledError
        if self._state != _FINISHED:
            raise InvalidStateError('Result is not ready.')
        if self._tb_logger is not None:
            self._tb_logger.clear()
            self._tb_logger = None
        if self._exception is not None:
            raise self._exception
        return self._result

    def exception(self):
        """Return the exception that was set on this future.

        The exception (or None if no exception was set) is returned only if
        the future is done.  If the future has been cancelled, raises
        CancelledError.  If the future isn't done yet, raises
        InvalidStateError.
        """
        if self._state == _CANCELLED:
            raise CancelledError
        if self._state != _FINISHED:
            raise InvalidStateError('Exception is not set.')
        if self._tb_logger is not None:
            self._tb_logger.clear()
            self._tb_logger = None
        return self._exception

    def add_done_callback(self, fn):
        """Add a callback to be run when the future becomes done.

        The callback is called with a single argument - the future object. If
        the future is already done when this is called, the callback is
        scheduled with call_soon.
        """
        if self._state != _PENDING:
            self._loop.call_soon(fn, self)
        else:
            self._callbacks.append(fn)

    # New method not in PEP 3148.

    def remove_done_callback(self, fn):
        """Remove all instances of a callback from the "call when done" list.

        Returns the number of callbacks removed.
        """
        filtered_callbacks = [f for f in self._callbacks if f != fn]
        removed_count = len(self._callbacks) - len(filtered_callbacks)
        if removed_count:
            self._callbacks[:] = filtered_callbacks
        return removed_count

    # So-called internal methods (note: no set_running_or_notify_cancel()).

    def set_result(self, result):
        """Mark the future done and set its result.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        if self._state != _PENDING:
            raise InvalidStateError('{}: {!r}'.format(self._state, self))
        self._result = result
        self._state = _FINISHED
        self._schedule_callbacks()

    def set_exception(self, exception):
        """Mark the future done and set an exception.

        If the future is already done when this method is called, raises
        InvalidStateError.
        """
        if self._state != _PENDING:
            raise InvalidStateError('{}: {!r}'.format(self._state, self))
        self._exception = exception
        self._tb_logger = _TracebackLogger(exception)
        self._state = _FINISHED
        self._schedule_callbacks()
        # Arrange for the logger to be activated after all callbacks
        # have had a chance to call result() or exception().
        self._loop.call_soon(self._tb_logger.activate)

    # Truly internal methods.

    def _copy_state(self, other):
        """Internal helper to copy state from another Future.

        The other Future may be a concurrent.futures.Future.
        """
        assert other.done()
        if self.cancelled():
            return
        assert not self.done()
        if other.cancelled():
            self.cancel()
        else:
            exception = other.exception()
            if exception is not None:
                self.set_exception(exception)
            else:
                result = other.result()
                self.set_result(result)

    def __iter__(self):
        if not self.done():
            self._blocking = True
            yield self  # This tells Task to wait for completion.
        assert self.done(), "yield from wasn't used with future"
        return self.result()  # May raise too.


def wrap_future(fut, *, loop=None):
    """Wrap concurrent.futures.Future object."""
    if isinstance(fut, Future):
        return fut
    assert isinstance(fut, concurrent.futures.Future), \
        'concurrent.futures.Future is expected, got {!r}'.format(fut)
    if loop is None:
        loop = events.get_event_loop()
    new_future = Future(loop=loop)

    def _check_cancel_other(f):
        if f.cancelled():
            fut.cancel()

    new_future.add_done_callback(_check_cancel_other)
    fut.add_done_callback(
        lambda future: loop.call_soon_threadsafe(
            new_future._copy_state, fut))
    return new_future
'''

from concurrent.futures.sync import Future as FutureSync


class Future(FutureSync):
    _blocking = False  # proper use of future (yield vs yield from)

    def __init__(self, *, loop=None):
        super().__init__(loop or events.get_event_loop())
        self._loop = self._executor

    def _run_callback(self, clb, executor):
        #exc = executor or self._executor
        self._executor.call_soon(clb, self)

    def __iter__(self):
        if not self.done():
            self._blocking = True
            yield self  # This tells Task to wait for completion.
        assert self.done(), "yield from wasn't used with future"
        return self.result()  # May raise too.


def wrap_future(fut, *, loop=None):
    """Wrap concurrent.futures.Future object."""
    if isinstance(fut, Future):
        return fut
    assert isinstance(fut, concurrent.futures.async.Future), \
        'concurrent.futures.async.Future is expected, got {!r}'.format(fut)
    if loop is None:
        loop = events.get_event_loop()
    new_future = Future(loop=loop)

    def _check_cancel_other(f):
        if f.cancelled():
            fut.cancel()

    new_future.add_done_callback(_check_cancel_other)
    fut.add_done_callback(
        lambda future: loop.call_soon_threadsafe(
            new_future._set_from, fut))
    return new_future
